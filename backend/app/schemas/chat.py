from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.memory import MemoryRead


ConversationKind = Literal["chat", "regrets", "wishes"]
ConversationContextKind = Literal["general", "wishes"]


def _reject_blank(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be blank")
    return value.strip()


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    kind: ConversationKind = "chat"
    context_kind: ConversationContextKind | None = None

    @field_validator("title")
    @classmethod
    def reject_blank_title(cls, value: str | None):
        if value is None:
            return value
        return _reject_blank(value, "title")


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    persona_id: str
    title: str | None
    kind: ConversationKind
    context_kind: ConversationContextKind
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationRead]


class MessageCitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    message_id: str
    memory_card_id: str | None
    source_material_id: str | None
    parsed_chunk_id: str | None
    quote: str | None
    source_location: str | None
    created_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    audio_url: str | None
    metadata_json: dict | list | None
    created_at: datetime
    citations: list[MessageCitationRead] = Field(default_factory=list)


class MessageListResponse(BaseModel):
    items: list[MessageRead]


class MessageCitationListResponse(BaseModel):
    items: list[MessageCitationRead]


class MessageSend(BaseModel):
    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value: str):
        return _reject_blank(value, "content")


class VoiceMessageSend(BaseModel):
    source_material_id: str = Field(min_length=1)

    @field_validator("source_material_id")
    @classmethod
    def reject_blank_source_material_id(cls, value: str):
        return _reject_blank(value, "source_material_id")


class MemoryCorrectionCreate(BaseModel):
    memory_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    title: str | None = Field(default=None, min_length=1)

    @field_validator("memory_id", "content", "title")
    @classmethod
    def reject_blank_strings(cls, value: str | None, info):
        if value is None:
            return value
        return _reject_blank(value, info.field_name)


class MemoryCorrectionResponse(BaseModel):
    memory: MemoryRead
    message: str
