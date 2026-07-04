from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ── AuditLog ───────────────────────────────────────────────────────────

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


# ── Summary ────────────────────────────────────────────────────────────

class AuditSummaryResponse(BaseModel):
    total_events: int
    by_severity: dict[str, int]
    by_event_type: dict[str, int]
    open_conflicts: int
    unacknowledged_drifts: int
    last_snapshot_at: str | None = None
    last_snapshot_id: str | None = None


# ── Snapshot ───────────────────────────────────────────────────────────

class SnapshotCreate(BaseModel):
    snapshot_type: str = "manual"
    label: str | None = None


class SnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    persona_id: str
    snapshot_type: str
    label: str | None = None
    memory_count: int
    trust_score: int
    created_at: datetime


class SnapshotListResponse(BaseModel):
    items: list[SnapshotRead]


class SnapshotCompareResponse(BaseModel):
    snapshot_a: dict
    snapshot_b: dict
    trust_score_delta: int
    memory_count_delta: int
    persona_changes: list[str]
    profile_changes: list[str]


# ── Rollback ───────────────────────────────────────────────────────────

class RollbackRequest(BaseModel):
    snapshot_id: str
    confirmed: bool = False


class RollbackResponse(BaseModel):
    success: bool = True
    safety_snapshot_id: str
    rollback_event_id: str


# ── Conflict ───────────────────────────────────────────────────────────

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


# ── Drift ──────────────────────────────────────────────────────────────

class DriftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    persona_id: str
    dimension: str
    drift_score: float
    before_summary: str | None = None
    after_summary: str | None = None
    triggered_alert: bool = False
    acknowledged_at: datetime | None = None
    created_at: datetime


class DriftListResponse(BaseModel):
    items: list[DriftRead]


# ── Dashboard ──────────────────────────────────────────────────────────

class AuditDashboardResponse(BaseModel):
    memory_health_score: float
    review_queue_size: int
    open_conflict_count: int
    unacknowledged_drift_count: int
    recent_events: list[dict]
    trust_score_trend: list[dict]
    source_coverage: dict


# ── Report ─────────────────────────────────────────────────────────────

class AuditReportResponse(BaseModel):
    report_generated_at: str
    persona_name: str
    summary: dict
    timeline: list[dict]
    conflicts: list[dict]
    drifts: list[dict]
    trust_trend: list[dict]
    current_trust: dict | None = None
    source_coverage: dict


# ── Memory History ─────────────────────────────────────────────────────

class MemoryHistoryResponse(BaseModel):
    items: list[AuditLogRead]
