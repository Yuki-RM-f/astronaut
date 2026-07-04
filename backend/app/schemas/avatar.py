from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.job import AIJobRead


AvatarStatus = Literal[
    "no_avatar",
    "default_avatar",
    "generating",
    "generated_ready",
    "generation_failed",
]
AvatarStyle = Literal["semi_realistic", "cartoon", "memorial"]


def _reject_blank(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be blank")
    return value.strip()


class AvatarModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    persona_id: str
    provider_type: str | None
    provider_name: str | None
    status: str | None
    source_image_material_id: str | None
    style: str | None
    model_url: str | None
    preview_image_url: str | None
    format: str | None
    expression_config_json: dict | list | None
    animation_config_json: dict | list | None
    lip_sync_config_json: dict | list | None
    user_selected: bool
    created_at: datetime
    updated_at: datetime


class AvatarConfigResponse(BaseModel):
    persona_id: str
    avatar_status: AvatarStatus
    selected_avatar_model: AvatarModelRead | None
    avatar_models: list[AvatarModelRead] = Field(default_factory=list)
    style_options: list[AvatarStyle]
    failure_notice: str


class DefaultAvatarSelection(BaseModel):
    style: AvatarStyle = "memorial"


class AvatarGenerateCreate(BaseModel):
    source_image_material_id: str = Field(min_length=1)
    style: AvatarStyle = "semi_realistic"
    simulate_failure: bool = False

    @field_validator("source_image_material_id")
    @classmethod
    def reject_blank_source_image_material_id(cls, value: str):
        return _reject_blank(value, "source_image_material_id")


class AvatarGenerateResponse(BaseModel):
    avatar_status: AvatarStatus
    avatar_model: AvatarModelRead
    selected_avatar_model: AvatarModelRead
    failure_notice: str
    provider: dict[str, str]
    job: AIJobRead
