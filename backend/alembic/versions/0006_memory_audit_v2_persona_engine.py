"""memory audit v2 and persona engine profile output

Revision ID: 0006_audit_persona_engine
Revises: 0005_persona_age
Create Date: 2026-07-04 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_audit_persona_engine"
down_revision = "0005_persona_age"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_logs",
        sa.Column("event_type", sa.String(length=50), nullable=False, server_default="memory.updated"),
    )
    op.add_column(
        "audit_logs",
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="info"),
    )
    op.add_column("audit_logs", sa.Column("changed_fields", sa.JSON(), nullable=True))
    op.add_column("audit_logs", sa.Column("correlation_id", sa.String(length=36), nullable=True))
    op.add_column("audit_logs", sa.Column("parent_event_id", sa.String(length=36), nullable=True))
    op.add_column("audit_logs", sa.Column("metadata_json", sa.JSON(), nullable=True))
    op.alter_column(
        "audit_logs",
        "action",
        existing_type=sa.String(length=50),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.create_index(
        op.f("ix_audit_logs_correlation_id"),
        "audit_logs",
        ["correlation_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_audit_logs_parent_event_id_audit_logs",
        "audit_logs",
        "audit_logs",
        ["parent_event_id"],
        ["id"],
    )

    op.create_table("memory_conflicts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("persona_id", sa.String(length=36), nullable=False),
        sa.Column("memory_id_a", sa.String(length=36), nullable=False),
        sa.Column("memory_id_b", sa.String(length=36), nullable=False),
        sa.Column("conflict_type", sa.String(length=30), nullable=False),
        sa.Column("conflict_description", sa.Text(), nullable=False),
        sa.Column("resolution_status", sa.String(length=30), nullable=False, server_default="open"),
        sa.Column("resolved_by", sa.String(length=36), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["memory_id_a"], ["memory_cards.id"]),
        sa.ForeignKeyConstraint(["memory_id_b"], ["memory_cards.id"]),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_memory_conflicts_persona_id"),
        "memory_conflicts",
        ["persona_id"],
        unique=False,
    )

    op.add_column("persona_profiles", sa.Column("persona_engine_json", sa.JSON(), nullable=True))
    op.add_column(
        "persona_profiles",
        sa.Column("persona_engine_generated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("persona_profiles", "persona_engine_generated_at")
    op.drop_column("persona_profiles", "persona_engine_json")

    op.drop_index(op.f("ix_memory_conflicts_persona_id"), table_name="memory_conflicts")
    op.drop_table("memory_conflicts")

    op.drop_constraint(
        "fk_audit_logs_parent_event_id_audit_logs",
        "audit_logs",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_audit_logs_correlation_id"), table_name="audit_logs")
    op.alter_column(
        "audit_logs",
        "action",
        existing_type=sa.Text(),
        type_=sa.String(length=50),
        existing_nullable=True,
    )
    op.drop_column("audit_logs", "metadata_json")
    op.drop_column("audit_logs", "parent_event_id")
    op.drop_column("audit_logs", "correlation_id")
    op.drop_column("audit_logs", "changed_fields")
    op.drop_column("audit_logs", "severity")
    op.drop_column("audit_logs", "event_type")
