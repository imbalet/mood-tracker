"""add questionnaire field soft deletion.

Revision ID: bec0e9e8d3fd
Revises: 31002b676585
Create Date: 2026-08-14 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bec0e9e8d3fd"
down_revision: str | None = "31002b676585"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "questionnaire_fields",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("questionnaire_fields", "deleted_at")
