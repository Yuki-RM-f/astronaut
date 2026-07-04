"""add soft-delete tombstones to related records

Revision ID: 0003_soft_delete_related_records
Revises: 0002_memory_stories
Create Date: 2026-07-04
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_soft_delete_related_records"
down_revision = "0002_memory_stories"
branch_labels = None
depends_on = None


TABLES = [
    "parsed_chunks",
    "persona_profiles",
    "messages",
    "message_citations",
    "voice_models",
    "avatar_models",
    "ai_jobs",
]


def upgrade() -> None:
    for table_name in TABLES:
        op.add_column(table_name, sa.Column("deleted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    for table_name in reversed(TABLES):
        op.drop_column(table_name, "deleted_at")
