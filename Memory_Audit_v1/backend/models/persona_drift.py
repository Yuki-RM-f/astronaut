from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import uuid_str


class PersonaDrift(Base):
    __tablename__ = "persona_drifts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id"), index=True
    )
    snapshot_id_before: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("audit_snapshots.id")
    )
    snapshot_id_after: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("audit_snapshots.id")
    )
    dimension: Mapped[str] = mapped_column(String(50))
    drift_score: Mapped[float] = mapped_column(Float, default=0.0)
    before_summary: Mapped[str | None] = mapped_column(Text)
    after_summary: Mapped[str | None] = mapped_column(Text)
    triggered_alert: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
