from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


ProfileValue = dict[str, Any] | list[Any]
PROFILE_DIMENSION_FIELDS = (
    "basic_facts",
    "relationships",
    "preferences",
    "habits",
    "expression_style",
    "shared_events",
    "values_json",
    "emotional_patterns",
)


class ProfileDimensionEntry(BaseModel):
    memory_id: str
    title: str
    content: str
    category: str
    confidence_level: str
    status: str


class TrustComponent(BaseModel):
    name: str
    score: int = Field(ge=0, le=100)
    weight: float
    weighted_score: float
    evidence: str


class TrustReport(BaseModel):
    trust_score: int = Field(ge=0, le=100)
    trust_level: str
    components: list[TrustComponent]
    suggestions: list[str]


class PersonaProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    persona_id: str
    basic_facts: ProfileValue
    relationships: ProfileValue
    preferences: ProfileValue
    habits: ProfileValue
    expression_style: ProfileValue
    shared_events: ProfileValue
    values_json: ProfileValue
    emotional_patterns: ProfileValue
    profile_summary: str | None
    source_memory_ids: dict[str, list[str]]
    persona_engine_json: dict[str, Any] | list[Any] | None = None
    persona_engine_generated_at: datetime | None = None
    trust_score: int
    trust_level: str
    components: list[TrustComponent]
    suggestions: list[str]
    created_at: datetime
    updated_at: datetime


class PersonaProfileUpdate(BaseModel):
    basic_facts: ProfileValue | None = None
    relationships: ProfileValue | None = None
    preferences: ProfileValue | None = None
    habits: ProfileValue | None = None
    expression_style: ProfileValue | None = None
    shared_events: ProfileValue | None = None
    values_json: ProfileValue | None = None
    emotional_patterns: ProfileValue | None = None
    profile_summary: str | None = None

    @field_validator(*PROFILE_DIMENSION_FIELDS, mode="before")
    @classmethod
    def validate_profile_value(cls, value):
        if value is None:
            raise ValueError("provided field cannot be null")
        if not isinstance(value, (dict, list)):
            raise ValueError("profile dimension must be a JSON object or array")
        return value

    @field_validator("profile_summary", mode="before")
    @classmethod
    def reject_null_summary(cls, value):
        if value is None:
            raise ValueError("provided field cannot be null")
        return value
