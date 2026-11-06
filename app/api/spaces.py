from datetime import date, time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import AuthenticatedUser, require_admin, require_enabled_user
from app.db import get_db
from app.models import AcademicSpace, Reservation
from app.schemas import (
    AvailabilityResponse,
    SpaceCreateRequest,
    SpaceResponse,
    TimeInterval,
)

router = APIRouter(prefix="/spaces", tags=["spaces"])
OPENING_TIME = time(7)
CLOSING_TIME = time(21)


@router.post("", response_model=SpaceResponse, status_code=status.HTTP_201_CREATED)
def create_space(
    payload: SpaceCreateRequest,
    _actor: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    space = AcademicSpace(
        name=payload.name,
        type=payload.type,
        capacity=payload.capacity,
        status=payload.status,
    )
    db.add(space)
    db.commit()
    db.refresh(space)
    return space


@router.get("", response_model=list[SpaceResponse])
def list_spaces(
    _actor: AuthenticatedUser = Depends(require_enabled_user),
    db: Session = Depends(get_db),
):
    return list(db.scalars(select(AcademicSpace).order_by(AcademicSpace.name, AcademicSpace.id)))


@router.get("/{space_id}/availability", response_model=AvailabilityResponse)
def get_availability(
    space_id: UUID,
    date: date = Query(),
    _actor: AuthenticatedUser = Depends(require_enabled_user),
    db: Session = Depends(get_db),
):
    space = db.get(AcademicSpace, space_id)
    if space is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Espacio no encontrado."
        )

    reservations = db.scalars(
        select(Reservation)
        .where(
            Reservation.space_id == space_id,
            Reservation.booking_date == date,
            Reservation.status == "APROBADA",
        )
        .order_by(Reservation.start_time, Reservation.end_time)
    ).all()
    occupied = [
        TimeInterval(start=reservation.start_time, end=reservation.end_time)
        for reservation in reservations
    ]

    free: list[TimeInterval] = []
    cursor = OPENING_TIME
    for interval in occupied:
        if cursor < interval.start:
            free.append(TimeInterval(start=cursor, end=interval.start))
        cursor = max(cursor, interval.end)
    if cursor < CLOSING_TIME:
        free.append(TimeInterval(start=cursor, end=CLOSING_TIME))

    return AvailabilityResponse(
        space_id=space_id,
        date=date,
        occupied=occupied,
        free=free,
    )
