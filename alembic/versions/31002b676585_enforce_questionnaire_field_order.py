"""enforce questionnaire field order.

Revision ID: 31002b676585
Revises: a1cd3b5a0969
Create Date: 2026-08-10 16:38:32.150283
"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "31002b676585"
down_revision: str | None = "a1cd3b5a0969"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "questionnaire_fields_questionnaire_order_key",
        "questionnaire_fields",
        ["questionnaire_id", "sort_order"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "questionnaire_fields_questionnaire_order_key",
        "questionnaire_fields",
        type_="unique",
    )
