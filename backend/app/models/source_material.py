from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import uuid_str


class SourceMaterial(Base):
    __tablename__ = "source_materials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id"), index=True
    )
    file_name: Mapped[str | None] = mapped_column(Text)
    file_type: Mapped[str] = mapped_column(String(50))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    storage_url: Mapped[str | None] = mapped_column(Text)
    manual_text: Mapped[str | None] = mapped_column(Text)
    user_description: Mapped[str | None] = mapped_column(Text)
    material_time: Mapped[datetime | None] = mapped_column(DateTime)
    people_tags: Mapped[dict | list | None] = mapped_column(JSON)
    location_hint: Mapped[str | None] = mapped_column(Text)
    importance: Mapped[str] = mapped_column(String(50), default="normal")
    parse_status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
