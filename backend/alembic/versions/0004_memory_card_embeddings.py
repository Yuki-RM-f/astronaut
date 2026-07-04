"""add memory card embedding metadata

Revision ID: 0004_memory_card_embeddings
Revises: 0003_soft_delete_related_records
Create Date: 2026-07-04 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_memory_card_embeddings"
down_revision = "0003_soft_delete_related_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("memory_cards", sa.Column("embedding", sa.JSON(), nullable=True))
    op.add_column("memory_cards", sa.Column("embedding_model", sa.String(length=120), nullable=True))
    op.add_column("memory_cards", sa.Column("embedding_provider", sa.String(length=50), nullable=True))
    op.add_column("memory_cards", sa.Column("embedding_text_hash", sa.String(length=64), nullable=True))
    op.add_column("memory_cards", sa.Column("embedding_updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("memory_cards", "embedding_updated_at")
    op.drop_column("memory_cards", "embedding_text_hash")
    op.drop_column("memory_cards", "embedding_provider")
    op.drop_column("memory_cards", "embedding_model")
    op.drop_column("memory_cards", "embedding")
