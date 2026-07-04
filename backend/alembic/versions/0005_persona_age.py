"""add persona age

Revision ID: 0005_persona_age
Revises: 0004_memory_card_embeddings
Create Date: 2026-07-04 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_persona_age"
down_revision = "0004_memory_card_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("personas", sa.Column("age", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("personas", "age")
