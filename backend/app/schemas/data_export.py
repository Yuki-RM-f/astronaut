from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.chat import ConversationRead, MessageRead
from app.schemas.memory import MemoryRead
from app.schemas.profile import PersonaProfileRead


class PersonaExportSnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    persona_type: str
    status: str | None
    relationship_to_user: str
    user_nickname_by_persona: str
    age: int | None
    gender: str | None
    language: str
    birth_date: date | None
    death_date: date | None
    short_bio: str | None
    speaking_style: str | None
    emotional_style: str | None
    forbidden_expressions: str | None
    avatar_image_url: str | None
    trust_score: int
    created_at: datetime
    updated_at: datetime


class PersonaProfileExportResponse(BaseModel):
    export_type: Literal["profile"]
    filename: str
    exported_at: datetime
    watermark: str
    persona: PersonaExportSnapshot
    profile: PersonaProfileRead


class PersonaMemoriesExportResponse(BaseModel):
    export_type: Literal["memories"]
    filename: str
    exported_at: datetime
    watermark: str
    persona: PersonaExportSnapshot
    items: list[MemoryRead]


class ConversationExportResponse(BaseModel):
    export_type: Literal["conversation"]
    filename: str
    exported_at: datetime
    watermark: str
    conversation: ConversationRead
    messages: list[MessageRead]
