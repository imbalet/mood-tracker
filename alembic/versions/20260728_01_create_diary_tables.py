"""create diary tables.

Revision ID: 20260728_01
Revises:
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260728_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), unique=True, nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column(
            "reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("reminder_time", sa.Time(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_table(
        "fields",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("is_core", sa.Boolean(), nullable=False),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("display_config", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'hidden')", name="fields_status_check"
        ),
        sa.CheckConstraint("sort_order >= 0", name="fields_sort_order_check"),
    )
    op.create_table(
        "field_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "field_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fields.id"),
            nullable=False,
        ),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "type IN ('scale', 'ordinal', 'text')", name="field_versions_type_check"
        ),
    )
    op.create_foreign_key(
        "fields_current_version_fkey",
        "fields",
        "field_versions",
        ["current_version_id"],
        ["id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_table(
        "days",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("status IN ('draft', 'complete')", name="days_status_check"),
        sa.UniqueConstraint("user_id", "date", name="days_user_date_key"),
    )
    op.create_table(
        "day_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "day_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("days.id"),
            nullable=False,
        ),
        sa.Column(
            "field_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fields.id"),
            nullable=False,
        ),
        sa.Column(
            "field_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("field_versions.id"),
            nullable=False,
        ),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("normalized_value", sa.Numeric(5, 4)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "normalized_value IS NULL OR normalized_value BETWEEN 0 AND 1",
            name="day_values_normalized_check",
        ),
        sa.UniqueConstraint("day_id", "field_id", name="day_values_day_field_key"),
    )
    op.create_table(
        "day_field_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "day_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("days.id"),
            nullable=False,
        ),
        sa.Column(
            "field_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fields.id"),
            nullable=False,
        ),
        sa.Column(
            "field_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("field_versions.id"),
            nullable=False,
        ),
        sa.Column("skipped", sa.Boolean(), nullable=False),
        sa.UniqueConstraint(
            "day_id", "field_id", name="day_field_progress_day_field_key"
        ),
    )
    op.create_table(
        "reference_states",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            primary_key=True,
        ),
        sa.Column(
            "best_day_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("days.id")
        ),
        sa.Column(
            "worst_day_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("days.id")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_table(
        "day_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "day_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("days.id"),
            nullable=False,
        ),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column(
            "previous_reference_day_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("days.id"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "type IN ('best', 'worst')", name="day_references_type_check"
        ),
    )


def downgrade() -> None:
    for table in (
        "day_references",
        "reference_states",
        "day_field_progress",
        "day_values",
        "days",
        "field_versions",
        "fields",
        "users",
    ):
        op.drop_table(table)
