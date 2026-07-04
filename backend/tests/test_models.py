from sqlalchemy import inspect

from app.core.config import get_settings
from app.db.base import Base


def test_prd_tables_are_registered():
    expected_tables = {
        "users",
        "personas",
        "source_materials",
        "parsed_chunks",
        "memory_cards",
        "persona_profiles",
        "ai_jobs",
        "conversations",
        "messages",
        "message_citations",
        "voice_models",
        "avatar_models",
        "audit_logs",
    }

    assert expected_tables.issubset(set(Base.metadata.tables))


def test_schema_can_be_created_in_sqlite_test_database(db_session):
    inspector = inspect(db_session.get_bind())
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    persona_columns = {column["name"] for column in inspector.get_columns("personas")}
    memory_columns = {column["name"] for column in inspector.get_columns("memory_cards")}

    assert {"id", "email", "password_hash", "plan_type"}.issubset(user_columns)
    assert {
        "id",
        "user_id",
        "name",
        "persona_type",
        "relationship_to_user",
        "user_nickname_by_persona",
        "age",
    }.issubset(persona_columns)
    assert {"title", "content", "confidence_level", "status"}.issubset(
        memory_columns
    )


def test_settings_repr_does_not_expose_jwt_secret():
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.database_url == "sqlite+pysqlite://"
    assert "test-secret" not in repr(settings)
