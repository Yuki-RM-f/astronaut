from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ProviderStatus(BaseModel):
    id: str
    label: str
    configured: bool
    secret_status: str
    capabilities: list[str] = Field(default_factory=list)
    settings: dict[str, str] = Field(default_factory=dict)


class ProviderSettingsResponse(BaseModel):
    default_llm_provider: str
    runtime_env_path: str
    runtime_env_exists: bool
    providers: list[ProviderStatus] = Field(default_factory=list)


class ProviderSettingsUpdate(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)

    @field_validator("values")
    @classmethod
    def reject_blank_keys(cls, values: dict[str, str]):
        cleaned: dict[str, str] = {}
        for key, value in values.items():
            normalized_key = key.strip().upper()
            if not normalized_key:
                raise ValueError("provider setting keys cannot be blank")
            cleaned[normalized_key] = str(value).strip()
        return cleaned
