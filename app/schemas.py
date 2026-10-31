from datetime import datetime
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
