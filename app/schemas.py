from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=12)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre es obligatorio.")
        return value


class EmailRequest(BaseModel):
    email: EmailStr


class TokenRequest(BaseModel):
    token: str = Field(min_length=1)


class ActivateAdminRequest(TokenRequest):
    password: str = Field(min_length=12)


class LoginRequest(EmailRequest):
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    status: str
    role: str
    created_at: datetime


class StatusRequest(BaseModel):
    status: Literal[
        "PENDIENTE_VERIFICACION", "VERIFICADO", "HABILITADO", "DESHABILITADO"
    ]


class RoleRequest(BaseModel):
    role: Literal["USER", "ADMIN"]


class AccountHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_user_id: UUID
    actor_user_id: UUID | None
    change_type: str
    old_value: str | None
    new_value: str
    created_at: datetime


class SpaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: Literal["LABORATORIO", "AUDITORIO", "SALA_COMPUTO"]
    capacity: int = Field(gt=0)
    status: Literal["ACTIVO", "INACTIVO"] = "ACTIVO"

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre es obligatorio.")
        return value


class SpaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: str
    capacity: int
    status: str
    created_at: datetime


class TimeInterval(BaseModel):
    start: time
    end: time


class AvailabilityResponse(BaseModel):
    space_id: UUID
    date: date
    occupied: list[TimeInterval]
    free: list[TimeInterval]


class ReservationCreateRequest(BaseModel):
    space_id: UUID
    date: date
    start_time: time
    end_time: time


class ReservationDecisionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El motivo es obligatorio.")
        return value


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    space_id: UUID
    requester_user_id: UUID
    booking_date: date
    start_time: time
    end_time: time
    status: str
    created_at: datetime


class ReservationListItemResponse(BaseModel):
    status: str
    space: str
    date: date
    start_time: time
    end_time: time


class ReservationHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reservation_id: UUID
    actor_user_id: UUID
    old_status: str | None
    new_status: str
    reason: str | None
    created_at: datetime
