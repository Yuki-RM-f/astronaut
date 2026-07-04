from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import uuid_str


class VoiceModel(Base):
    __tablename__ = "voice_models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id"), index=True
    )
    provider_type: Mapped[str | None] = mapped_column(String(50))
    provider_name: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str | None] = mapped_column(String(50))
    reference_audio_asset_id: Mapped[str | None] = mapped_column(String(36))
    model_artifact_url: Mapped[str | None] = mapped_column(Text)
    sample_text: Mapped[str | None] = mapped_column(Text)
    sample_audio_url: Mapped[str | None] = mapped_column(Text)
    quality_score: Mapped[int | None] = mapped_column(Integer)
    user_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)


class AvatarModel(Base):
    __tablename__ = "avatar_models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    persona_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personas.id"), index=True
    )
    provider_type: Mapped[str | None] = mapped_column(String(50))
    provider_name: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str | None] = mapped_column(String(50))
    source_image_material_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("source_materials.id")
    )
    style: Mapped[str | None] = mapped_column(String(50))
    model_url: Mapped[str | None] = mapped_column(Text)
    preview_image_url: Mapped[str | None] = mapped_column(Text)
    format: Mapped[str | None] = mapped_column(String(20))
    expression_config_json: Mapped[dict | list | None] = mapped_column(JSON)
    animation_config_json: Mapped[dict | list | None] = mapped_column(JSON)
    lip_sync_config_json: Mapped[dict | list | None] = mapped_column(JSON)
    user_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
