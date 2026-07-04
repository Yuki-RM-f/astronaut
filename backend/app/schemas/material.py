from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.job import AIJobRead


AllowedImportance = Literal["normal", "important", "very_important"]
MaterialFileType = Literal["text", "image", "audio", "video", "manual"]
MaterialParseStatus = Literal[
    "pending", "running", "succeeded", "failed", "canceled", "retrying"
]


class ManualMaterialCreate(BaseModel):
    manual_text: str = Field(min_length=1)
    importance: AllowedImportance = "normal"
    user_description: str | None = None
    material_time: datetime | None = None
    people_tags: dict | list | None = None
    location_hint: str | None = None

    @field_validator("manual_text")
    @classmethod
    def reject_blank_manual_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("manual_text cannot be blank")
        return value


class MaterialRead(BaseModel):
    id: str
    persona_id: str
    file_name: str | None
    file_type: MaterialFileType
    mime_type: str | None
    file_size: int | None
    storage_url: str | None
    manual_text: str | None
    user_description: str | None
    material_time: datetime | None
    people_tags: dict | list | None
    location_hint: str | None
    importance: AllowedImportance
    parse_status: MaterialParseStatus
    created_at: datetime
    updated_at: datetime
    jobs: list[AIJobRead] = Field(default_factory=list)


class MaterialListResponse(BaseModel):
    items: list[MaterialRead]
