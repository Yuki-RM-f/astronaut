from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


AllowedMemoryCategory = Literal[
    "basic_fact",
    "relationship",
    "preference",
    "habit",
    "expression_style",
    "shared_event",
    "value",
    "emotional_pattern",
    "story_material",
    "unknown",
]
AllowedConfidenceLevel = Literal["high", "medium", "low"]
AllowedMemoryStatus = Literal[
    "pending_review",
    "confirmed",
    "corrected",
    "rejected",
    "disabled",
    "auto_generated",
]
AllowedMemorySourceType = Literal["text", "image", "audio", "video", "manual"]


def _reject_blank(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be blank")
    return value


class MemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    persona_id: str
    title: str
    content: str
    category: AllowedMemoryCategory
    confidence_level: AllowedConfidenceLevel
    confidence_score: int
    source_material_id: str | None
    parsed_chunk_id: str | None
    source_type: AllowedMemorySourceType | None
    source_quote: str | None
    source_location: str | None
    evidence_json: dict | list | None
    status: AllowedMemoryStatus
    user_correction: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime


class MemoryListResponse(BaseModel):
    items: list[MemoryRead]


class MemoryCreate(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    category: AllowedMemoryCategory
    confidence_level: AllowedConfidenceLevel = "medium"
    confidence_score: int = Field(default=50, ge=0, le=100)
    source_material_id: str
    source_type: AllowedMemorySourceType | None = None
    source_quote: str = Field(min_length=1)
    source_location: str = Field(min_length=1)
    evidence_json: dict | list | None = None
    status: AllowedMemoryStatus = "pending_review"

    @field_validator("title", "content", "source_quote", "source_location")
    @classmethod
    def reject_blank_strings(cls, value: str, info):
        return _reject_blank(value, info.field_name)


class MemoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    content: str | None = Field(default=None, min_length=1)
    category: AllowedMemoryCategory | None = None
    confidence_level: AllowedConfidenceLevel | None = None
    confidence_score: int | None = Field(default=None, ge=0, le=100)
    status: AllowedMemoryStatus | None = None

    @field_validator(
        "title",
        "content",
        "category",
        "confidence_level",
        "confidence_score",
        "status",
        mode="before",
    )
    @classmethod
    def reject_null_updates(cls, value):
        if value is None:
            raise ValueError("provided field cannot be null")
        return value

    @field_validator("title", "content")
    @classmethod
    def reject_blank_strings(cls, value: str, info):
        return _reject_blank(value, info.field_name)
