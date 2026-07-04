from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.memory import MemoryRead


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    persona_id: str | None
    target_type: str | None
    target_id: str | None
    action: str | None
    event_type: str
    severity: str
    changed_fields: list[str] | None
    before_json: dict[str, Any] | list[Any] | None
    after_json: dict[str, Any] | list[Any] | None
    correlation_id: str | None
    parent_event_id: str | None
    metadata_json: dict[str, Any] | list[Any] | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]
    total: int
    limit: int
    offset: int


class AuditSummaryResponse(BaseModel):
    persona_id: str
    total_events: int
    by_event_type: dict[str, int]
    by_severity: dict[str, int]
    recent_events: list[AuditLogRead]
    open_conflicts: int
    health_score: int = Field(ge=0, le=100)


class AuditDashboardResponse(BaseModel):
    persona_id: str
    health_score: int = Field(ge=0, le=100)
    pending_review_count: int
    open_conflict_count: int
    source_coverage: dict[str, int]
    recent_events: list[AuditLogRead]


class MemoryConflictRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    persona_id: str
    memory_id_a: str
    memory_id_b: str
    memory_title_a: str | None = None
    memory_title_b: str | None = None
    conflict_type: str
    conflict_description: str
    resolution_status: str
    resolved_by: str | None
    resolved_at: datetime | None
    severity: str
    created_at: datetime
    updated_at: datetime


class MemoryConflictListResponse(BaseModel):
    items: list[MemoryConflictRead]
    total: int


class AuditReportResponse(BaseModel):
    persona_id: str
    generated_at: datetime
    summary: AuditSummaryResponse
    events_by_day: dict[str, int]
    conflicts: list[MemoryConflictRead]
    recommendations: list[str]


class ResolveConflictRequest(BaseModel):
    resolution_status: Literal["resolved_by_user", "dismissed"]


class MemoryHistoryResponse(BaseModel):
    memory_id: str
    events: list[AuditLogRead]
    conflicts: list[MemoryConflictRead]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("query", mode="before")
    @classmethod
    def trim_query(cls, value: str) -> str:
        query = str(value or "").strip()
        if not query:
            raise ValueError("query cannot be blank")
        return query


class SearchResultItem(BaseModel):
    memory: MemoryRead
    relevance_score: float
    matched_terms: list[str]
    source_excerpt: str | None


class SearchResponse(BaseModel):
    query: str
    items: list[SearchResultItem]
    total: int
