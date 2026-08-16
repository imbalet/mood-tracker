"""drop global field soft deletion.

Revision ID: a80c5915a5e3
Revises: bec0e9e8d3fd
Create Date: 2026-08-16 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a80c5915a5e3"
down_revision: str | None = "bec0e9e8d3fd"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_column("fields", "deleted_at")


def downgrade() -> None:
    op.add_column(
        "fields",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
