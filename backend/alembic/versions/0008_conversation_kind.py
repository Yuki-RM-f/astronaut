"""Add conversation kind for guided chat isolation."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0008_conversation_kind"
down_revision = "0007_memory_card_importance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="chat"),
    )
    op.create_index(op.f("ix_conversations_kind"), "conversations", ["kind"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_conversations_kind"), table_name="conversations")
    op.drop_column("conversations", "kind")
