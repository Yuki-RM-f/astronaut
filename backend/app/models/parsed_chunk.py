from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import uuid_str


class ParsedChunk(Base):
    __tablename__ = "parsed_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id"), index=True
    )
    source_material_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("source_materials.id"), index=True
    )
    chunk_type: Mapped[str | None] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    source_location: Mapped[str | None] = mapped_column(Text)
    start_time_seconds: Mapped[float | None] = mapped_column(Float)
    end_time_seconds: Mapped[float | None] = mapped_column(Float)
    metadata_json: Mapped[dict | list | None] = mapped_column("metadata", JSON)
    embedding: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
