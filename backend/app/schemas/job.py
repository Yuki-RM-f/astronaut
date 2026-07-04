from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


AIJobStatus = Literal["pending", "running", "succeeded", "failed", "canceled", "retrying"]


class AIJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    persona_id: str | None
    source_material_id: str | None
    job_type: str
    provider_type: str
    provider_name: str | None
    status: AIJobStatus
    input_json: dict | list | None
    output_json: dict | list | None
    error_message: str | None
    retry_count: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AIJobListResponse(BaseModel):
    items: list[AIJobRead]
