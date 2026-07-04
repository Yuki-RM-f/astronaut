from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import uuid_str


class MemoryCard(Base):
    __tablename__ = "memory_cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id"), index=True
    )
    title: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50))
    confidence_level: Mapped[str] = mapped_column(String(20))
    confidence_score: Mapped[int] = mapped_column(Integer, default=50)
    source_material_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("source_materials.id")
    )
    parsed_chunk_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("parsed_chunks.id")
    )
    source_type: Mapped[str | None] = mapped_column(String(50))
    source_quote: Mapped[str | None] = mapped_column(Text)
    source_location: Mapped[str | None] = mapped_column(Text)
    evidence_json: Mapped[dict | list | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="pending_review")
    is_important: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    user_correction: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(50), default="system")
    embedding: Mapped[list | None] = mapped_column(JSON)
    embedding_model: Mapped[str | None] = mapped_column(String(120))
    embedding_provider: Mapped[str | None] = mapped_column(String(50))
    embedding_text_hash: Mapped[str | None] = mapped_column(String(64))
    embedding_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
