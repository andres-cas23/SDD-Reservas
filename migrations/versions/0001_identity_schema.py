"""Create the identity schema.

Revision ID: 0001_identity_schema
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_identity_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="PENDIENTE_VERIFICACION",
            nullable=False,
        ),
        sa.Column("role", sa.String(length=16), server_default="USER", nullable=False),
        sa.Column("last_verification_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('PENDIENTE_VERIFICACION', 'VERIFICADO', 'HABILITADO', 'DESHABILITADO')",
            name="ck_users_status",
        ),
        sa.CheckConstraint("role IN ('USER', 'ADMIN')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_users_email_ci", "users", [sa.text("lower(trim(email))")], unique=True
    )

    op.create_table(
        "verification_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('EMAIL_VERIFICATION', 'ADMIN_ACTIVATION')",
            name="ck_verification_tokens_kind",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_verification_tokens_user_kind", "verification_tokens", ["user_id", "kind"]
    )

    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("jti"),
    )

    op.create_table(
        "account_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("target_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("change_type", sa.String(length=16), nullable=False),
        sa.Column("old_value", sa.String(length=64), nullable=True),
        sa.Column("new_value", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "change_type IN ('STATE', 'ROLE')", name="ck_account_history_change_type"
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_account_history_target_created",
        "account_history",
        ["target_user_id", "created_at"],
    )

    op.execute(
        """
        CREATE FUNCTION prevent_account_history_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'account_history is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER account_history_append_only
        BEFORE UPDATE OR DELETE ON account_history
        FOR EACH ROW EXECUTE FUNCTION prevent_account_history_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS account_history_append_only ON account_history")
    op.execute("DROP FUNCTION IF EXISTS prevent_account_history_mutation()")
    op.drop_index("ix_account_history_target_created", table_name="account_history")
    op.drop_table("account_history")
    op.drop_table("revoked_tokens")
    op.drop_index("ix_verification_tokens_user_kind", table_name="verification_tokens")
    op.drop_table("verification_tokens")
    op.drop_index("uq_users_email_ci", table_name="users")
    op.drop_table("users")
