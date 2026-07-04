from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ── AuditLog ───────────────────────────────────────────────────────────────

class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    persona_id: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    event_type: str
    severity: str
    action: str | None = None
    changed_fields: list[str] | None = None
    before_json: dict | list | None = None
    after_json: dict | list | None = None
    correlation_id: str | None = None
    parent_event_id: str | None = None
    metadata_json: dict | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]
    total: int
    limit: int
    offset: int


# ── Summary ────────────────────────────────────────────────────────────────

class AuditSummaryResponse(BaseModel):
    total_events: int
    by_severity: dict[str, int]
    by_event_type: dict[str, int]
    open_conflicts: int


# ── Conflict ───────────────────────────────────────────────────────────────

class ConflictRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    persona_id: str
    memory_id_a: str
    memory_id_b: str
    conflict_type: str
    conflict_description: str
    resolution_status: str
    severity: str
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class ConflictListResponse(BaseModel):
    items: list[ConflictRead]


class ResolveConflictRequest(BaseModel):
    resolution: str  # "resolved_by_user" | "dismissed"


# ── Dashboard ──────────────────────────────────────────────────────────────

class AuditDashboardResponse(BaseModel):
    memory_health_score: float
    review_queue_size: int
    open_conflict_count: int
    recent_events: list[dict]
    source_coverage: dict


# ── Report ─────────────────────────────────────────────────────────────────

class AuditReportResponse(BaseModel):
    report_generated_at: str
    persona_name: str
    summary: dict
    timeline: list[dict]
    conflicts: list[dict]
    source_coverage: dict


# ── Memory History ─────────────────────────────────────────────────────────

class MemoryHistoryResponse(BaseModel):
    items: list[AuditLogRead]


# ── Semantic Search ────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResultItem(BaseModel):
    id: str
    title: str
    content: str
    source_quote: str | None = None
    source_location: str | None = None
    confidence_score: float | None = None
    confidence_level: str | None = None
    category: str
    status: str
    relevance_score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total_found: int
