from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.dependencies import AuthenticatedUser, require_admin
from app.db import get_db
from app.models import AccountHistory, Reservation, ReservationHistory, User, utc_now
from app.schemas import (
    AccountHistoryResponse,
    RoleRequest,
    StatusRequest,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["users"])
VALID_STATUS_TRANSITIONS = {
    ("VERIFICADO", "HABILITADO"),
    ("HABILITADO", "DESHABILITADO"),
    ("DESHABILITADO", "HABILITADO"),
}
ACTIVE_ADMIN_STATUSES = {"VERIFICADO", "HABILITADO"}
ACADEMIC_TIMEZONE = ZoneInfo("America/Bogota")


@router.get("", response_model=list[UserResponse])
def list_users(
    _actor: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return list(db.scalars(select(User).order_by(User.created_at, User.id)))


@router.patch("/{user_id}/status", response_model=UserResponse)
def change_user_status(
    user_id: UUID,
    payload: StatusRequest,
    actor: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado."
        )
    transition = (user.status, payload.status)
    if transition not in VALID_STATUS_TRANSITIONS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transición de estado no permitida.",
        )

    now = utc_now()
    previous_status = user.status
    user.status = payload.status
    db.add(
        AccountHistory(
            target_user_id=user.id,
            actor_user_id=actor.user.id,
            change_type="STATE",
            old_value=previous_status,
            new_value=payload.status,
            created_at=now,
        )
    )
    if payload.status == "DESHABILITADO":
        local_now = now.astimezone(ACADEMIC_TIMEZONE)
        reservations = db.scalars(
            select(Reservation)
            .where(
                Reservation.requester_user_id == user.id,
                Reservation.status.in_(("PENDIENTE", "APROBADA")),
            )
            .with_for_update()
        ).all()
        for reservation in reservations:
            reservation_start = datetime.combine(
                reservation.booking_date,
                reservation.start_time,
                tzinfo=ACADEMIC_TIMEZONE,
            )
            if reservation.status == "PENDIENTE" or reservation_start > local_now:
                previous_status = reservation.status
                reservation.status = "CANCELADA"
                db.add(
                    ReservationHistory(
                        reservation_id=reservation.id,
                        actor_user_id=actor.user.id,
                        old_status=previous_status,
                        new_status="CANCELADA",
                        reason="usuario deshabilitado",
                        created_at=now,
                    )
                )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/role", response_model=UserResponse)
def change_user_role(
    user_id: UUID,
    payload: RoleRequest,
    actor: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(731942017)"))

    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado."
        )
    if user_id == actor.user.id and payload.role == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No puedes promoverte a ti mismo.",
        )
    if payload.role == "ADMIN" and user.status not in ACTIVE_ADMIN_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede asignar un rol de administrador a un usuario verificado.",
        )

    previous_role = user.role
    if previous_role == payload.role:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario ya tiene ese rol.",
        )
    if previous_role == "ADMIN" and payload.role == "USER":
        active_admins = db.scalars(
            select(User)
            .where(
                User.role == "ADMIN",
                User.status.in_(ACTIVE_ADMIN_STATUSES),
            )
            .with_for_update()
        ).all()
        if user.status in ACTIVE_ADMIN_STATUSES and len(active_admins) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede revocar el rol del último administrador activo.",
            )

    now = utc_now()
    user.role = payload.role
    db.add(
        AccountHistory(
            target_user_id=user.id,
            actor_user_id=actor.user.id,
            change_type="ROLE",
            old_value=previous_role,
            new_value=payload.role,
            created_at=now,
        )
    )
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}/history", response_model=list[AccountHistoryResponse])
def get_account_history(
    user_id: UUID,
    _actor: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.get(User, user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado."
        )
    return list(
        db.scalars(
            select(AccountHistory)
            .where(AccountHistory.target_user_id == user_id)
            .order_by(AccountHistory.created_at, AccountHistory.id)
        )
    )
