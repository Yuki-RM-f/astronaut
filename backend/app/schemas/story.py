from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _reject_blank(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} cannot be blank")
    return stripped


class StoryMemorySource(BaseModel):
    memory_card_id: str
    title: str
    quote: str
    source_location: str | None


class MemoryStoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    persona_id: str
    theme: str
    title: str
    content: str
    audio_url: str | None
    source_memory_ids: list[str]
    source_memories: list[StoryMemorySource]
    is_favorite: bool
    metadata_json: dict | list | None
    created_at: datetime
    updated_at: datetime


class MemoryStoryListResponse(BaseModel):
    items: list[MemoryStoryRead]


class MemoryStoryExportResponse(BaseModel):
    story_id: str
    persona_id: str
    theme: str
    title: str
    export_text: str
    text_filename: str
    audio_url: str | None
    audio_filename: str | None
    audio_export_notice: str
    source_memory_ids: list[str]
    source_memories: list[StoryMemorySource]


class MemoryStoryCreate(BaseModel):
    theme: str = Field(min_length=1)

    @field_validator("theme")
    @classmethod
    def reject_blank_theme(cls, value: str):
        return _reject_blank(value, "theme")


class MemoryStoryFavoriteUpdate(BaseModel):
    is_favorite: bool
