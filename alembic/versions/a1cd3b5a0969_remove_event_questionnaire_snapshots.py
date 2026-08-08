"""remove event questionnaire snapshots.

Revision ID: a1cd3b5a0969
Revises: 97e36b17a25e
Create Date: 2026-08-08 15:51:51.725811
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1cd3b5a0969"
down_revision: str | None = "97e36b17a25e"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_table("event_questionnaire_fields")


def downgrade() -> None:
    op.create_table(
        "event_questionnaire_fields",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("field_id", sa.UUID(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.CheckConstraint(
            "sort_order >= 0", name="event_questionnaire_fields_order_check"
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id", "field_id", name="event_questionnaire_fields_key"
        ),
    )
