from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import uuid_str


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    persona_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("personas.id"), index=True
    )
    target_type: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[str | None] = mapped_column(String(36))
    event_type: Mapped[str] = mapped_column(String(50), default="memory.updated")
    severity: Mapped[str] = mapped_column(String(20), default="info")
    action: Mapped[str | None] = mapped_column(Text)
    changed_fields: Mapped[list | None] = mapped_column(JSON)
    before_json: Mapped[dict | list | None] = mapped_column(JSON)
    after_json: Mapped[dict | list | None] = mapped_column(JSON)
    correlation_id: Mapped[str | None] = mapped_column(String(36), index=True)
    parent_event_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("audit_logs.id"))
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
