from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import uuid_str


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    persona_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str | None] = mapped_column(String(50))
    relationship_to_user: Mapped[str] = mapped_column(String(100))
    user_nickname_by_persona: Mapped[str] = mapped_column(String(100))
    gender: Mapped[str | None] = mapped_column(String(50))
    language: Mapped[str] = mapped_column(String(50), default="zh-CN")
    birth_date: Mapped[date | None] = mapped_column(Date)
    death_date: Mapped[date | None] = mapped_column(Date)
    short_bio: Mapped[str | None] = mapped_column(Text)
    speaking_style: Mapped[str | None] = mapped_column(Text)
    emotional_style: Mapped[str | None] = mapped_column(Text)
    forbidden_expressions: Mapped[str | None] = mapped_column(Text)
    avatar_image_url: Mapped[str | None] = mapped_column(Text)
    trust_score: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
