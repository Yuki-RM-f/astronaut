"""add memory stories

Revision ID: 0002_memory_stories
Revises: 0001_initial_schema
Create Date: 2026-07-04
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_memory_stories"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_stories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("persona_id", sa.String(length=36), nullable=False),
        sa.Column("theme", sa.String(length=50), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("audio_url", sa.Text(), nullable=True),
        sa.Column("source_memory_ids", sa.JSON(), nullable=True),
        sa.Column("source_memories", sa.JSON(), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_stories_persona_id", "memory_stories", ["persona_id"])


def downgrade() -> None:
    op.drop_index("ix_memory_stories_persona_id", table_name="memory_stories")
    op.drop_table("memory_stories")
