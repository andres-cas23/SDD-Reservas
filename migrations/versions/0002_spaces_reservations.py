"""Create academic spaces and reservation schema.

Revision ID: 0002_spaces_reservations
Revises: 0001_identity_schema
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_spaces_reservations"
down_revision = "0001_identity_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "academic_spaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="ACTIVO", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "type IN ('LABORATORIO', 'AUDITORIO', 'SALA_COMPUTO')",
            name="ck_academic_spaces_type",
        ),
        sa.CheckConstraint("capacity > 0", name="ck_academic_spaces_capacity"),
        sa.CheckConstraint(
            "status IN ('ACTIVO', 'INACTIVO')", name="ck_academic_spaces_status"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_academic_spaces_status_name", "academic_spaces", ["status", "name"]
    )

    op.create_table(
        "reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("requester_user_id", sa.Uuid(), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default="PENDIENTE", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('PENDIENTE', 'APROBADA', 'RECHAZADA', 'CANCELADA')",
            name="ck_reservations_status",
        ),
        sa.CheckConstraint("start_time < end_time", name="ck_reservations_time_order"),
        sa.ForeignKeyConstraint(
            ["space_id"], ["academic_spaces.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["requester_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_reservations_space_date_status",
        "reservations",
        ["space_id", "booking_date", "status"],
    )
    op.create_index(
        "ix_reservations_requester",
        "reservations",
        ["requester_user_id", "booking_date"],
    )

    op.create_table(
        "reservation_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reservation_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("old_status", sa.String(length=16), nullable=True),
        sa.Column("new_status", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "old_status IS NULL OR old_status IN ('PENDIENTE', 'APROBADA', 'RECHAZADA', 'CANCELADA')",
            name="ck_reservation_history_old_status",
        ),
        sa.CheckConstraint(
            "new_status IN ('PENDIENTE', 'APROBADA', 'RECHAZADA', 'CANCELADA')",
            name="ck_reservation_history_new_status",
        ),
        sa.ForeignKeyConstraint(
            ["reservation_id"], ["reservations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_reservation_history_reservation_created",
        "reservation_history",
        ["reservation_id", "created_at"],
    )

    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE reservations
        ADD CONSTRAINT ex_reservations_approved_no_overlap
        EXCLUDE USING gist (
            space_id WITH =,
            tsrange(booking_date + start_time, booking_date + end_time, '[)') WITH &&
        )
        WHERE (status = 'APROBADA')
        """
    )
    op.execute(
        """
        CREATE FUNCTION prevent_reservation_history_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'reservation_history is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER reservation_history_append_only
        BEFORE UPDATE OR DELETE ON reservation_history
        FOR EACH ROW EXECUTE FUNCTION prevent_reservation_history_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS reservation_history_append_only ON reservation_history"
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_reservation_history_mutation()")
    op.drop_index(
        "ix_reservation_history_reservation_created", table_name="reservation_history"
    )
    op.drop_table("reservation_history")
    op.drop_index("ix_reservations_requester", table_name="reservations")
    op.drop_index("ix_reservations_space_date_status", table_name="reservations")
    op.drop_table("reservations")
    op.drop_index("ix_academic_spaces_status_name", table_name="academic_spaces")
    op.drop_table("academic_spaces")
