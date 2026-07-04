"""add memory card importance flag

Revision ID: 0007_memory_card_importance
Revises: 0006_memory_audit_v2_persona_engine
Create Date: 2026-07-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_memory_card_importance"
down_revision = "0006_audit_persona_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "memory_cards",
        sa.Column(
            "is_important",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("memory_cards", "is_important")
