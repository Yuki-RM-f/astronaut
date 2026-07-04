from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import uuid_str


class AuditSnapshot(Base):
    __tablename__ = "audit_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id"), index=True
    )
    snapshot_type: Mapped[str] = mapped_column(String(20), default="manual")
    label: Mapped[str | None] = mapped_column(Text)

    persona_snapshot: Mapped[dict] = mapped_column(JSON)
    profile_snapshot: Mapped[dict] = mapped_column(JSON)
    memory_snapshots: Mapped[list] = mapped_column(JSON)
    trust_report: Mapped[dict] = mapped_column(JSON)

    memory_count: Mapped[int] = mapped_column(Integer, default=0)
    trust_score: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
