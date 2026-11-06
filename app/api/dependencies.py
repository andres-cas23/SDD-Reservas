from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RevokedToken, User

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    user: User
    token_id: str
    token_expires_at: datetime


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de autenticación no válido.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_authenticated_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()

    try:
        claims = jwt.decode(
            credentials.credentials,
            request.app.state.settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            options={"require": ["sub", "jti", "iat", "exp"]},
        )
        user_id = UUID(claims["sub"])
        token_id = claims["jti"]
        token_expires_at = datetime.fromtimestamp(claims["exp"], timezone.utc)
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise unauthorized() from None

    if db.get(RevokedToken, token_id) is not None:
        raise unauthorized()
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized()
    return AuthenticatedUser(user, token_id, token_expires_at)


def require_admin(
    authenticated: AuthenticatedUser = Depends(get_authenticated_user),
) -> AuthenticatedUser:
    if authenticated.user.role != "ADMIN" or authenticated.user.status == "DESHABILITADO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere una cuenta de administrador activa.",
        )
    return authenticated


def require_enabled_user(
    authenticated: AuthenticatedUser = Depends(get_authenticated_user),
) -> AuthenticatedUser:
    if authenticated.user.status != "HABILITADO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere una cuenta habilitada.",
        )
    return authenticated
