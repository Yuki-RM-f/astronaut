from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import uuid_str


class PersonaProfile(Base):
    __tablename__ = "persona_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id"), unique=True, index=True
    )
    basic_facts: Mapped[dict | list | None] = mapped_column(JSON)
    relationships: Mapped[dict | list | None] = mapped_column(JSON)
    preferences: Mapped[dict | list | None] = mapped_column(JSON)
    habits: Mapped[dict | list | None] = mapped_column(JSON)
    expression_style: Mapped[dict | list | None] = mapped_column(JSON)
    shared_events: Mapped[dict | list | None] = mapped_column(JSON)
    values_json: Mapped[dict | list | None] = mapped_column(JSON)
    emotional_patterns: Mapped[dict | list | None] = mapped_column(JSON)
    profile_summary: Mapped[str | None] = mapped_column(Text)
    source_memory_ids: Mapped[dict | list | None] = mapped_column(JSON)
    persona_engine_json: Mapped[dict | list | None] = mapped_column(JSON)
    persona_engine_generated_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
