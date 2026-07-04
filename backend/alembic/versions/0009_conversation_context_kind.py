"""add conversation context kind

Revision ID: 0009_conversation_context_kind
Revises: 0008_conversation_kind
Create Date: 2026-07-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_conversation_context_kind"
down_revision = "0008_conversation_kind"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("context_kind", sa.String(length=20), nullable=False, server_default="general"),
    )
    op.create_index(
        op.f("ix_conversations_context_kind"),
        "conversations",
        ["context_kind"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_conversations_context_kind"), table_name="conversations")
    op.drop_column("conversations", "context_kind")
