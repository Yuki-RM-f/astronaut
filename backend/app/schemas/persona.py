from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


AllowedPersonaType = Literal[
    "deceased_relative",
    "living_relative",
    "public_figure",
    "fictional_character",
]
AllowedGender = Literal["female", "male", "unknown"]
AllowedPersonaStatus = Literal["deceased", "living", "public", "fictional"]
AllowedPersonaLanguage = Literal["zh-CN"]
DEFAULT_PERSONA_LANGUAGE = "zh-CN"
CREATE_REQUIRED_STRING_FIELDS = (
    "name",
    "relationship_to_user",
    "user_nickname_by_persona",
    "short_bio",
    "speaking_style",
    "emotional_style",
    "forbidden_expressions",
)
PATCH_REQUIRED_FIELDS = (
    "name",
    "persona_type",
    "relationship_to_user",
    "user_nickname_by_persona",
    "age",
    "gender",
    "language",
    "status",
    "short_bio",
    "speaking_style",
    "emotional_style",
    "forbidden_expressions",
)


class PersonaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    persona_type: AllowedPersonaType
    status: AllowedPersonaStatus
    relationship_to_user: str = Field(min_length=1, max_length=100)
    user_nickname_by_persona: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=1, le=150)
    gender: AllowedGender
    language: AllowedPersonaLanguage = DEFAULT_PERSONA_LANGUAGE
    birth_date: date | None = None
    death_date: date | None = None
    short_bio: str = Field(min_length=1)
    speaking_style: str = Field(min_length=1)
    emotional_style: str = Field(min_length=1)
    forbidden_expressions: str = Field(min_length=1)
    avatar_image_url: str | None = None

    @field_validator(*CREATE_REQUIRED_STRING_FIELDS)
    @classmethod
    def reject_blank_required_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("required field cannot be blank")
        return value


class PersonaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    persona_type: AllowedPersonaType | None = None
    status: AllowedPersonaStatus | None = None
    relationship_to_user: str | None = Field(default=None, min_length=1, max_length=100)
    user_nickname_by_persona: str | None = Field(
        default=None, min_length=1, max_length=100
    )
    age: int | None = Field(default=None, ge=1, le=150)
    gender: AllowedGender | None = None
    language: AllowedPersonaLanguage | None = None
    birth_date: date | None = None
    death_date: date | None = None
    short_bio: str | None = None
    speaking_style: str | None = None
    emotional_style: str | None = None
    forbidden_expressions: str | None = None
    avatar_image_url: str | None = None

    @field_validator(*PATCH_REQUIRED_FIELDS, mode="before")
    @classmethod
    def reject_empty_required_fields(cls, value):
        if value is None:
            raise ValueError("required field cannot be null")
        if isinstance(value, str) and not value.strip():
            raise ValueError("required field cannot be blank")
        return value


class PersonaStats(BaseModel):
    materials_count: int
    memories_count: int
    conversations_count: int


class PersonaRead(BaseModel):
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
    stats: PersonaStats
    prompt_context: dict[str, str]


class PersonaListResponse(BaseModel):
    items: list[PersonaRead]
