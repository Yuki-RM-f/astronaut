from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.job import AIJobRead


VoiceStatus = Literal[
    "no_voice",
    "default_tts",
    "sample_ready",
    "cloning",
    "cloned_ready",
    "clone_failed",
]
DefaultTTSGender = Literal["male", "female", "neutral"]
DefaultTTSAgeStyle = Literal["young", "middle_aged", "elderly"]
DefaultTTSStyle = Literal["gentle", "calm", "lively", "kind", "low"]
DefaultTTSSpeed = Literal["slow", "normal", "fast"]
DefaultTTSEmotion = Literal["calm", "comfort", "encourage", "nostalgia"]


class VoiceModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    persona_id: str
    provider_type: str | None
    provider_name: str | None
    status: str | None
    reference_audio_asset_id: str | None
    model_artifact_url: str | None
    sample_text: str | None
    sample_audio_url: str | None
    quality_score: int | None
    user_selected: bool
    created_at: datetime
    updated_at: datetime


class VoiceConfigResponse(BaseModel):
    persona_id: str
    voice_status: VoiceStatus
    selected_voice_model: VoiceModelRead | None
    voice_models: list[VoiceModelRead] = Field(default_factory=list)
    default_tts_notice: str
    default_tts_options: dict[str, list[str]]


class DefaultTTSSelection(BaseModel):
    gender: DefaultTTSGender = "female"
    age_style: DefaultTTSAgeStyle = "elderly"
    style: DefaultTTSStyle = "gentle"
    speed: DefaultTTSSpeed = "normal"
    emotion: DefaultTTSEmotion = "comfort"


class SpeechSynthesisCreate(BaseModel):
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str):
        stripped = value.strip()
        if not stripped:
            raise ValueError("text cannot be blank")
        return stripped


class SpeechSynthesisResponse(BaseModel):
    audio_url: str
    voice_status: VoiceStatus
    selected_voice_model: VoiceModelRead
    default_tts_notice: str
    provider: dict[str, Any]
    job: AIJobRead


class VoiceSampleCreate(BaseModel):
    source_material_id: str = Field(min_length=1)

    @field_validator("source_material_id")
    @classmethod
    def reject_blank_source_material_id(cls, value: str):
        stripped = value.strip()
        if not stripped:
            raise ValueError("source_material_id cannot be blank")
        return stripped


class VoiceSampleResponse(BaseModel):
    voice_status: VoiceStatus
    voice_model: VoiceModelRead
    provider: dict[str, Any]
    job: AIJobRead


class VoiceCloneCreate(BaseModel):
    voice_model_id: str | None = Field(default=None, min_length=1)
    simulate_failure: bool = False

    @field_validator("voice_model_id")
    @classmethod
    def reject_blank_voice_model_id(cls, value: str | None):
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("voice_model_id cannot be blank")
        return stripped


class VoiceCloneResponse(BaseModel):
    voice_status: VoiceStatus
    voice_model: VoiceModelRead
    selected_voice_model: VoiceModelRead
    default_tts_notice: str
    provider: dict[str, Any]
    job: AIJobRead
