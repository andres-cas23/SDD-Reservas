import secrets
import smtplib
from datetime import timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AccountHistory, RevokedToken, User, VerificationToken, utc_now
from app.schemas import (
    ActivateAdminRequest,
    EmailRequest,
    LoginRequest,
    RegisterRequest,
    TokenRequest,
    UserResponse,
)
from app.security import (
    create_access_token,
    dummy_password_hash,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.seed_admin import activate_seeded_admin
from app.api.dependencies import AuthenticatedUser, get_authenticated_user

router = APIRouter(prefix="/auth", tags=["auth"])
VERIFICATION_TTL = timedelta(hours=24)
RESEND_COOLDOWN = timedelta(minutes=2)


def _new_verification_token(db: Session, user: User, now) -> tuple[VerificationToken, str]:
    token_value = secrets.token_urlsafe(32)
    token = VerificationToken(
        user_id=user.id,
        token_hash=hash_opaque_token(token_value),
        kind="EMAIL_VERIFICATION",
        created_at=now,
        expires_at=now + VERIFICATION_TTL,
    )
    db.add(token)
    user.last_verification_sent_at = now
    return token, token_value


def _verification_link(base_url: str, token_value: str) -> str:
    return f"{base_url.rstrip('/')}/auth/verify#{urlencode({'token': token_value})}"


def _token_is_expired(token: VerificationToken, now) -> bool:
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= now


def _send_verification(request: Request, email: str, token_value: str) -> None:
    try:
        request.app.state.send_verification(
            email,
            _verification_link(request.app.state.settings.app_base_url, token_value),
        )
    except (OSError, RuntimeError, smtplib.SMTPException):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo enviar el correo de verificación.",
        ) from None


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest, request: Request, db: Session = Depends(get_db)
):
    email = str(payload.email).strip().casefold()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo.",
        )

    now = utc_now()
    user = User(
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password),
        status="PENDIENTE_VERIFICACION",
        role="USER",
        created_at=now,
    )
    db.add(user)
    try:
        db.flush()
        _, token_value = _new_verification_token(db, user, now)
        db.add(
            AccountHistory(
                target_user_id=user.id,
                actor_user_id=None,
                change_type="STATE",
                old_value=None,
                new_value="PENDIENTE_VERIFICACION",
                created_at=now,
            )
        )
        db.add(
            AccountHistory(
                target_user_id=user.id,
                actor_user_id=None,
                change_type="ROLE",
                old_value=None,
                new_value="USER",
                created_at=now,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo.",
        ) from None

    try:
        _send_verification(request, user.email, token_value)
    finally:
        del token_value
    return user


@router.post("/verify")
def verify_email(payload: TokenRequest, db: Session = Depends(get_db)):
    now = utc_now()
    verification = db.scalar(
        select(VerificationToken)
        .where(
            VerificationToken.token_hash == hash_opaque_token(payload.token),
            VerificationToken.kind == "EMAIL_VERIFICATION",
            VerificationToken.consumed_at.is_(None),
        )
        .with_for_update()
    )
    if verification is None or _token_is_expired(verification, now):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de verificación no es válido o expiró.",
        )

    user = db.get(User, verification.user_id)
    if user is None or user.status != "PENDIENTE_VERIFICACION":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de verificación no es válido o expiró.",
        )

    verification.consumed_at = now
    user.status = "VERIFICADO"
    db.add(
        AccountHistory(
            target_user_id=user.id,
            actor_user_id=user.id,
            change_type="STATE",
            old_value="PENDIENTE_VERIFICACION",
            new_value="VERIFICADO",
            created_at=now,
        )
    )
    db.commit()
    return {"message": "Cuenta verificada."}


@router.get("/verify")
def verification_instructions():
    return {
        "message": "Envía el token del fragmento del enlace en el cuerpo de POST /auth/verify."
    }


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
def resend_verification(
    payload: EmailRequest, request: Request, db: Session = Depends(get_db)
):
    email = str(payload.email).strip().casefold()
    user = db.scalar(select(User).where(User.email == email).with_for_update())
    now = utc_now()
    last_sent = user.last_verification_sent_at if user is not None else None
    if last_sent is not None and last_sent.tzinfo is None:
        last_sent = last_sent.replace(tzinfo=timezone.utc)
    if (
        user is None
        or user.status != "PENDIENTE_VERIFICACION"
        or (last_sent is not None and now - last_sent < RESEND_COOLDOWN)
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="No se puede reenviar la verificación en este momento.",
        )

    for previous in db.scalars(
        select(VerificationToken).where(
            VerificationToken.user_id == user.id,
            VerificationToken.kind == "EMAIL_VERIFICATION",
            VerificationToken.consumed_at.is_(None),
        )
    ):
        previous.consumed_at = now
    _, token_value = _new_verification_token(db, user, now)
    db.commit()
    try:
        _send_verification(request, user.email, token_value)
    finally:
        del token_value
    return {"message": "Si la cuenta puede verificarse, se envió un nuevo enlace."}


@router.post("/activate-admin")
def activate_admin(
    payload: ActivateAdminRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        activate_seeded_admin(
            db, payload.token, payload.password, request.app.state.settings
        )
    except ValueError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from None
    except OSError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo completar la activación del administrador.",
        ) from None
    return {"message": "Administrador activado."}


@router.get("/activate-admin")
def admin_activation_instructions():
    return {
        "message": (
            "Envía el token del fragmento y una contraseña de al menos 12 caracteres "
            "en el cuerpo de POST /auth/activate-admin."
        )
    }


@router.post("/login")
def login(
    payload: LoginRequest, request: Request, db: Session = Depends(get_db)
):
    email = str(payload.email).strip().casefold()
    user = db.scalar(select(User).where(User.email == email))
    password_hash = (
        user.password_hash
        if user is not None and user.password_hash is not None
        else dummy_password_hash()
    )
    password_matches = verify_password(payload.password, password_hash)
    if user is None or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status == "PENDIENTE_VERIFICACION":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cuenta no verificada",
        )
    if user.status == "DESHABILITADO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cuenta deshabilitada",
        )

    encoded, _, _ = create_access_token(str(user.id), request.app.state.settings)
    return {
        "access_token": encoded,
        "token_type": "bearer",
        "expires_in": 60 * 60,
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    authenticated: AuthenticatedUser = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    db.add(
        RevokedToken(
            jti=authenticated.token_id,
            expires_at=authenticated.token_expires_at,
            revoked_at=utc_now(),
        )
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
