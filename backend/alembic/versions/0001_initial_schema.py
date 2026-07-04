"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-04
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("plan_type", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "personas",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("persona_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("relationship_to_user", sa.String(length=100), nullable=False),
        sa.Column("user_nickname_by_persona", sa.String(length=100), nullable=False),
        sa.Column("gender", sa.String(length=50), nullable=True),
        sa.Column("language", sa.String(length=50), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("death_date", sa.Date(), nullable=True),
        sa.Column("short_bio", sa.Text(), nullable=True),
        sa.Column("speaking_style", sa.Text(), nullable=True),
        sa.Column("emotional_style", sa.Text(), nullable=True),
        sa.Column("forbidden_expressions", sa.Text(), nullable=True),
        sa.Column("avatar_image_url", sa.Text(), nullable=True),
        sa.Column("trust_score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_personas_user_id", "personas", ["user_id"])

    op.create_table(
        "source_materials",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("persona_id", sa.String(length=36), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=True),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("storage_url", sa.Text(), nullable=True),
        sa.Column("manual_text", sa.Text(), nullable=True),
        sa.Column("user_description", sa.Text(), nullable=True),
        sa.Column("material_time", sa.DateTime(), nullable=True),
        sa.Column("people_tags", sa.JSON(), nullable=True),
        sa.Column("location_hint", sa.Text(), nullable=True),
        sa.Column("importance", sa.String(length=50), nullable=False),
        sa.Column("parse_status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_materials_persona_id", "source_materials", ["persona_id"])
    op.create_index("ix_source_materials_user_id", "source_materials", ["user_id"])

    op.create_table(
        "parsed_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("persona_id", sa.String(length=36), nullable=False),
        sa.Column("source_material_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_type", sa.String(length=50), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_location", sa.Text(), nullable=True),
        sa.Column("start_time_seconds", sa.Float(), nullable=True),
        sa.Column("end_time_seconds", sa.Float(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.ForeignKeyConstraint(["source_material_id"], ["source_materials.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parsed_chunks_persona_id", "parsed_chunks", ["persona_id"])
    op.create_index(
        "ix_parsed_chunks_source_material_id",
        "parsed_chunks",
        ["source_material_id"],
    )

    op.create_table(
        "memory_cards",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("persona_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("confidence_level", sa.String(length=20), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("source_material_id", sa.String(length=36), nullable=True),
        sa.Column("parsed_chunk_id", sa.String(length=36), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("source_quote", sa.Text(), nullable=True),
        sa.Column("source_location", sa.Text(), nullable=True),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("user_correction", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parsed_chunk_id"], ["parsed_chunks.id"]),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.ForeignKeyConstraint(["source_material_id"], ["source_materials.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_cards_persona_id", "memory_cards", ["persona_id"])

    op.create_table(
        "persona_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("persona_id", sa.String(length=36), nullable=False),
        sa.Column("basic_facts", sa.JSON(), nullable=True),
        sa.Column("relationships", sa.JSON(), nullable=True),
        sa.Column("preferences", sa.JSON(), nullable=True),
        sa.Column("habits", sa.JSON(), nullable=True),
        sa.Column("expression_style", sa.JSON(), nullable=True),
        sa.Column("shared_events", sa.JSON(), nullable=True),
        sa.Column("values_json", sa.JSON(), nullable=True),
        sa.Column("emotional_patterns", sa.JSON(), nullable=True),
        sa.Column("profile_summary", sa.Text(), nullable=True),
        sa.Column("source_memory_ids", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_persona_profiles_persona_id",
        "persona_profiles",
        ["persona_id"],
        unique=True,
    )

    op.create_table(
        "ai_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("persona_id", sa.String(length=36), nullable=True),
        sa.Column("source_material_id", sa.String(length=36), nullable=True),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("provider_type", sa.String(length=50), nullable=False),
        sa.Column("provider_name", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.ForeignKeyConstraint(["source_material_id"], ["source_materials.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_jobs_persona_id", "ai_jobs", ["persona_id"])
    op.create_index("ix_ai_jobs_user_id", "ai_jobs", ["user_id"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("persona_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_persona_id", "conversations", ["persona_id"])
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("audio_url", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    op.create_table(
        "message_citations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=False),
        sa.Column("memory_card_id", sa.String(length=36), nullable=True),
        sa.Column("source_material_id", sa.String(length=36), nullable=True),
        sa.Column("parsed_chunk_id", sa.String(length=36), nullable=True),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("source_location", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["memory_card_id"], ["memory_cards.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.ForeignKeyConstraint(["parsed_chunk_id"], ["parsed_chunks.id"]),
        sa.ForeignKeyConstraint(["source_material_id"], ["source_materials.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_message_citations_message_id", "message_citations", ["message_id"])

    op.create_table(
        "voice_models",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("persona_id", sa.String(length=36), nullable=False),
        sa.Column("provider_type", sa.String(length=50), nullable=True),
        sa.Column("provider_name", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("reference_audio_asset_id", sa.String(length=36), nullable=True),
        sa.Column("model_artifact_url", sa.Text(), nullable=True),
        sa.Column("sample_text", sa.Text(), nullable=True),
        sa.Column("sample_audio_url", sa.Text(), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("user_selected", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_voice_models_persona_id", "voice_models", ["persona_id"])

    op.create_table(
        "avatar_models",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("persona_id", sa.String(length=36), nullable=False),
        sa.Column("provider_type", sa.String(length=50), nullable=True),
        sa.Column("provider_name", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("source_image_material_id", sa.String(length=36), nullable=True),
        sa.Column("style", sa.String(length=50), nullable=True),
        sa.Column("model_url", sa.Text(), nullable=True),
        sa.Column("preview_image_url", sa.Text(), nullable=True),
        sa.Column("format", sa.String(length=20), nullable=True),
        sa.Column("expression_config_json", sa.JSON(), nullable=True),
        sa.Column("animation_config_json", sa.JSON(), nullable=True),
        sa.Column("lip_sync_config_json", sa.JSON(), nullable=True),
        sa.Column("user_selected", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.ForeignKeyConstraint(["source_image_material_id"], ["source_materials.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_avatar_models_persona_id", "avatar_models", ["persona_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("persona_id", sa.String(length=36), nullable=True),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_persona_id", "audit_logs", ["persona_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("avatar_models")
    op.drop_table("voice_models")
    op.drop_table("message_citations")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("ai_jobs")
    op.drop_table("persona_profiles")
    op.drop_table("memory_cards")
    op.drop_table("parsed_chunks")
    op.drop_table("source_materials")
    op.drop_table("personas")
    op.drop_table("users")
