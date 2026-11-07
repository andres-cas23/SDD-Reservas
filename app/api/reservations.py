from datetime import time
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from uuid import UUID

from app.api.dependencies import (
    AuthenticatedUser,
    get_authenticated_user,
    require_admin,
    require_enabled_user,
)
from app.db import get_db
from app.models import AcademicSpace, Reservation, ReservationHistory, utc_now
from app.schemas import (
    ReservationCreateRequest,
    ReservationDecisionRequest,
    ReservationHistoryResponse,
    ReservationListItemResponse,
    ReservationResponse,
)

router = APIRouter(prefix="/reservations", tags=["reservations"])
ACADEMIC_TIMEZONE = ZoneInfo("America/Bogota")
OPENING_TIME = time(7)
CLOSING_TIME = time(21)


def _append_history(
    db: Session,
    reservation: Reservation,
    actor_user_id: UUID,
    old_status: str | None,
    new_status: str,
    reason: str | None = None,
) -> None:
    db.add(
        ReservationHistory(
            reservation_id=reservation.id,
            actor_user_id=actor_user_id,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            created_at=utc_now(),
        )
    )


def _overlap_conditions(
    space_id: UUID,
    booking_date,
    start_time: time,
    end_time: time,
):
    return (
        Reservation.space_id == space_id,
        Reservation.booking_date == booking_date,
        Reservation.start_time < end_time,
        Reservation.end_time > start_time,
    )


def _get_space_for_update(db: Session, space_id: UUID) -> AcademicSpace | None:
    return db.scalar(
        select(AcademicSpace).where(AcademicSpace.id == space_id).with_for_update()
    )


def _reservation_or_404(db: Session, reservation_id: UUID) -> Reservation:
    reservation = db.scalar(
        select(Reservation).where(Reservation.id == reservation_id).with_for_update()
    )
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada."
        )
    return reservation


@router.get("", response_model=list[ReservationListItemResponse])
def list_reservations(
    actor: AuthenticatedUser = Depends(require_enabled_user),
    db: Session = Depends(get_db),
):
    query = (
        select(Reservation, AcademicSpace.name)
        .join(AcademicSpace, Reservation.space_id == AcademicSpace.id)
    )
    if actor.user.role != "ADMIN":
        query = query.where(Reservation.requester_user_id == actor.user.id)

    return [
        ReservationListItemResponse(
            id=reservation.id,
            status=reservation.status,
            space=space_name,
            date=reservation.booking_date,
            start_time=reservation.start_time,
            end_time=reservation.end_time,
        )
        for reservation, space_name in db.execute(
            query.order_by(
                Reservation.booking_date,
                Reservation.start_time,
                Reservation.id,
            )
        )
    ]


@router.post("", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def create_reservation(
    payload: ReservationCreateRequest,
    actor: AuthenticatedUser = Depends(require_enabled_user),
    db: Session = Depends(get_db),
):
    if (
        payload.start_time < OPENING_TIME
        or payload.end_time > CLOSING_TIME
        or payload.start_time >= payload.end_time
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El horario debe estar entre 07:00 y 21:00 y la hora de inicio debe preceder a la hora de fin.",
        )

    space = _get_space_for_update(db, payload.space_id)
    if space is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Espacio no encontrado."
        )
    if space.status != "ACTIVO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El espacio no está activo.",
        )

    conflict = db.scalar(
        select(Reservation)
        .where(
            *_overlap_conditions(
                payload.space_id,
                payload.date,
                payload.start_time,
                payload.end_time,
            ),
            Reservation.status == "APROBADA",
        )
        .order_by(Reservation.start_time, Reservation.id)
    )
    if conflict is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "El horario se cruza con una reserva aprobada.",
                "reservation_id": str(conflict.id),
            },
        )

    reservation = Reservation(
        space_id=payload.space_id,
        requester_user_id=actor.user.id,
        booking_date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status="PENDIENTE",
    )
    db.add(reservation)
    db.flush()
    _append_history(db, reservation, actor.user.id, None, "PENDIENTE")
    db.commit()
    db.refresh(reservation)
    return reservation


@router.post("/{reservation_id}/approve", response_model=ReservationResponse)
def approve_reservation(
    reservation_id: UUID,
    actor: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada."
        )
    _get_space_for_update(db, reservation.space_id)
    reservation = _reservation_or_404(db, reservation_id)
    if reservation.status != "PENDIENTE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden aprobar solicitudes pendientes.",
        )

    approved_conflict = db.scalar(
        select(Reservation)
        .where(
            *_overlap_conditions(
                reservation.space_id,
                reservation.booking_date,
                reservation.start_time,
                reservation.end_time,
            ),
            Reservation.status == "APROBADA",
            Reservation.id != reservation.id,
        )
        .order_by(Reservation.start_time, Reservation.id)
    )
    if approved_conflict is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "El horario se cruza con una reserva aprobada.",
                "reservation_id": str(approved_conflict.id),
            },
        )

    pending = db.scalars(
        select(Reservation)
        .where(
            *_overlap_conditions(
                reservation.space_id,
                reservation.booking_date,
                reservation.start_time,
                reservation.end_time,
            ),
            Reservation.status == "PENDIENTE",
            Reservation.id != reservation.id,
        )
        .with_for_update()
    ).all()
    reservation.status = "APROBADA"
    _append_history(db, reservation, actor.user.id, "PENDIENTE", "APROBADA")
    for conflict in pending:
        conflict.status = "RECHAZADA"
        _append_history(
            db,
            conflict,
            actor.user.id,
            "PENDIENTE",
            "RECHAZADA",
            "conflicto con reserva aprobada",
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        conflict = db.scalar(
            select(Reservation)
            .where(
                *_overlap_conditions(
                    reservation.space_id,
                    reservation.booking_date,
                    reservation.start_time,
                    reservation.end_time,
                ),
                Reservation.status == "APROBADA",
                Reservation.id != reservation.id,
            )
            .order_by(Reservation.start_time, Reservation.id)
        )
        if conflict is None:
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "El horario se cruza con una reserva aprobada.",
                "reservation_id": str(conflict.id),
            },
        ) from None
    db.refresh(reservation)
    return reservation


@router.post("/{reservation_id}/reject", response_model=ReservationResponse)
def reject_reservation(
    reservation_id: UUID,
    payload: ReservationDecisionRequest,
    actor: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    reservation = _reservation_or_404(db, reservation_id)
    if reservation.status != "PENDIENTE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden rechazar solicitudes pendientes.",
        )
    reservation.status = "RECHAZADA"
    _append_history(
        db,
        reservation,
        actor.user.id,
        "PENDIENTE",
        "RECHAZADA",
        payload.reason,
    )
    db.commit()
    db.refresh(reservation)
    return reservation


@router.post("/{reservation_id}/cancel", response_model=ReservationResponse)
def cancel_reservation(
    reservation_id: UUID,
    payload: ReservationDecisionRequest,
    actor: AuthenticatedUser = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada."
        )
    _get_space_for_update(db, reservation.space_id)
    reservation = _reservation_or_404(db, reservation_id)
    if reservation.requester_user_id != actor.user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el solicitante puede cancelar esta reserva.",
        )
    if reservation.status not in {"PENDIENTE", "APROBADA"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La reserva ya se encuentra en un estado final.",
        )
    previous_status = reservation.status
    reservation.status = "CANCELADA"
    _append_history(
        db,
        reservation,
        actor.user.id,
        previous_status,
        "CANCELADA",
        payload.reason,
    )
    db.commit()
    db.refresh(reservation)
    return reservation


@router.get("/{reservation_id}/history", response_model=list[ReservationHistoryResponse])
def get_reservation_history(
    reservation_id: UUID,
    actor: AuthenticatedUser = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada."
        )
    if (
        actor.user.role != "ADMIN"
        and reservation.requester_user_id != actor.user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para consultar este historial.",
        )
    return list(
        db.scalars(
            select(ReservationHistory)
            .where(ReservationHistory.reservation_id == reservation_id)
            .order_by(ReservationHistory.created_at, ReservationHistory.id)
        )
    )
