"""add durable notification settings and delivery claims."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# TODO: посмотреть слоп

revision: str = "c4f3e8b2a1d7"
down_revision: str | Sequence[str] | None = "a80c5915a5e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_settings",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "reminder_time", sa.Time(), nullable=False, server_default="20:00:00"
        ),
        sa.Column(
            "repeat_interval", sa.Interval(), nullable=False, server_default="1 day"
        ),
        sa.Column(
            "max_reminders_per_day",
            sa.SmallInteger(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "notification_deliveries",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("reminder_number", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "local_date", "reminder_number"),
        sa.CheckConstraint(
            "status IN ('claimed', 'sent')", name="notification_delivery_status_check"
        ),
    )
    op.execute(
        sa.text(
            """INSERT INTO notification_settings
            (user_id, is_enabled, reminder_time, repeat_interval, max_reminders_per_day)
            SELECT id, reminder_enabled, COALESCE(reminder_time, '20:00:00'),
                   INTERVAL '1 day', 1 FROM users"""
        )
    )
    op.drop_column("users", "reminder_time")
    op.drop_column("users", "reminder_enabled")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column("users", sa.Column("reminder_time", sa.Time(), nullable=True))
    op.execute(
        sa.text(
            """UPDATE users AS u
            SET reminder_enabled = n.is_enabled, reminder_time = n.reminder_time
            FROM notification_settings AS n WHERE n.user_id = u.id"""
        )
    )
    op.drop_table("notification_deliveries")
    op.drop_table("notification_settings")
    op.alter_column("users", "reminder_enabled", server_default=None)
