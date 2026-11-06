from datetime import date, datetime, time as wall_time, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Time,
    Uuid,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, Session as OrmSession, mapped_column

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDIENTE_VERIFICACION', 'VERIFICADO', 'HABILITADO', 'DESHABILITADO')",
            name="ck_users_status",
        ),
        CheckConstraint("role IN ('USER', 'ADMIN')", name="ck_users_role"),
        Index("uq_users_email_ci", text("lower(trim(email))"), unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDIENTE_VERIFICACION",
        server_default="PENDIENTE_VERIFICACION",
    )
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, default="USER", server_default="USER"
    )
    last_verification_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class VerificationToken(Base):
    __tablename__ = "verification_tokens"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('EMAIL_VERIFICATION', 'ADMIN_ACTIVATION')",
            name="ck_verification_tokens_kind",
        ),
        Index("ix_verification_tokens_user_kind", "user_id", "kind"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class AccountHistory(Base):
    __tablename__ = "account_history"
    __table_args__ = (
        CheckConstraint(
            "change_type IN ('STATE', 'ROLE')", name="ck_account_history_change_type"
        ),
        Index("ix_account_history_target_created", "target_user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    target_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    change_type: Mapped[str] = mapped_column(String(16), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(64))
    new_value: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class AcademicSpace(Base):
    __tablename__ = "academic_spaces"
    __table_args__ = (
        CheckConstraint(
            "type IN ('LABORATORIO', 'AUDITORIO', 'SALA_COMPUTO')",
            name="ck_academic_spaces_type",
        ),
        CheckConstraint(
            "capacity > 0",
            name="ck_academic_spaces_capacity",
        ),
        CheckConstraint(
            "status IN ('ACTIVO', 'INACTIVO')",
            name="ck_academic_spaces_status",
        ),
        Index("ix_academic_spaces_status_name", "status", "name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    capacity: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ACTIVO", server_default="ACTIVO"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDIENTE', 'APROBADA', 'RECHAZADA', 'CANCELADA')",
            name="ck_reservations_status",
        ),
        CheckConstraint("start_time < end_time", name="ck_reservations_time_order"),
        Index("ix_reservations_space_date_status", "space_id", "booking_date", "status"),
        Index("ix_reservations_requester", "requester_user_id", "booking_date"),
        ExcludeConstraint(
            ("space_id", "="),
            (
                text("tsrange(booking_date + start_time, booking_date + end_time, '[)')"),
                "&&",
            ),
            where=text("status = 'APROBADA'"),
            using="gist",
            name="ex_reservations_approved_no_overlap",
        ).ddl_if(dialect="postgresql"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    space_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("academic_spaces.id", ondelete="RESTRICT"), nullable=False
    )
    requester_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    booking_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[wall_time] = mapped_column(Time, nullable=False)
    end_time: Mapped[wall_time] = mapped_column(Time, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PENDIENTE", server_default="PENDIENTE"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class ReservationHistory(Base):
    __tablename__ = "reservation_history"
    __table_args__ = (
        CheckConstraint(
            "old_status IS NULL OR old_status IN ('PENDIENTE', 'APROBADA', 'RECHAZADA', 'CANCELADA')",
            name="ck_reservation_history_old_status",
        ),
        CheckConstraint(
            "new_status IN ('PENDIENTE', 'APROBADA', 'RECHAZADA', 'CANCELADA')",
            name="ck_reservation_history_new_status",
        ),
        Index("ix_reservation_history_reservation_created", "reservation_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    reservation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("reservations.id", ondelete="RESTRICT"), nullable=False
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    old_status: Mapped[str | None] = mapped_column(String(16))
    new_status: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


@event.listens_for(OrmSession, "before_flush")
def prevent_history_mutation(session, _flush_context, _instances) -> None:
    history_types = (AccountHistory, ReservationHistory)
    if any(isinstance(record, history_types) for record in session.deleted):
        raise ValueError("El historial es append-only.")
    if any(
        isinstance(record, history_types) and session.is_modified(record)
        for record in session.dirty
    ):
        raise ValueError("El historial es append-only.")
