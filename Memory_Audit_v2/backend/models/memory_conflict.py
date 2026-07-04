from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import uuid_str


class MemoryConflict(Base):
    __tablename__ = "memory_conflicts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id"), index=True
    )
    memory_id_a: Mapped[str] = mapped_column(String(36), ForeignKey("memory_cards.id"))
    memory_id_b: Mapped[str] = mapped_column(String(36), ForeignKey("memory_cards.id"))
    conflict_type: Mapped[str] = mapped_column(String(30))
    conflict_description: Mapped[str] = mapped_column(Text)
    resolution_status: Mapped[str] = mapped_column(String(20), default="open")
    resolved_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
