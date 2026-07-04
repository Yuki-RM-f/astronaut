from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.audit import (
    AuditDashboardResponse,
    AuditLogListResponse,
    AuditLogRead,
    AuditReportResponse,
    AuditSummaryResponse,
    ConflictListResponse,
    ConflictRead,
    DriftListResponse,
    DriftRead,
    MemoryHistoryResponse,
    ResolveConflictRequest,
    RollbackRequest,
    RollbackResponse,
    SnapshotCompareResponse,
    SnapshotCreate,
    SnapshotListResponse,
    SnapshotRead,
)
from app.services.audit import (
    compare_snapshots,
    create_snapshot,
    generate_audit_report,
    get_audit_dashboard,
    get_audit_summary,
    get_memory_change_history,
    get_snapshots,
    query_audit_logs,
    rollback_to_snapshot,
)
from app.services.conflict_detector import resolve_conflict
from app.services.materials import get_persona_or_404


router = APIRouter(tags=["audit"])


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s)


# ── Audit Logs ─────────────────────────────────────────────────────────

@router.get(
    "/personas/{persona_id}/audit/logs",
    response_model=AuditLogListResponse,
)
def list_audit_logs(
    persona_id: str,
    event_type: str | None = None,
    severity: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    correlation_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_persona_or_404(persona_id, current_user, db)
    items, total = query_audit_logs(
        db,
        persona_id=persona_id,
        event_type=event_type,
        severity=severity,
        target_type=target_type,
        target_id=target_id,
        date_from=_parse_iso(date_from),
        date_to=_parse_iso(date_to),
        correlation_id=correlation_id,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(
        items=[AuditLogRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/personas/{persona_id}/audit/summary",
    response_model=AuditSummaryResponse,
)
def audit_summary(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_persona_or_404(persona_id, current_user, db)
    return AuditSummaryResponse(**get_audit_summary(db, persona_id))


@router.get(
    "/personas/{persona_id}/audit/report",
    response_model=AuditReportResponse,
)
def audit_report(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_persona_or_404(persona_id, current_user, db)
    return AuditReportResponse(**generate_audit_report(db, persona_id))


@router.get(
    "/memories/{memory_id}/history",
    response_model=MemoryHistoryResponse,
)
def memory_change_history(
    memory_id: str,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = get_memory_change_history(db, memory_id, limit=limit)
    return MemoryHistoryResponse(
        items=[AuditLogRead.model_validate(item) for item in items]
    )


# ── Snapshots ──────────────────────────────────────────────────────────

@router.post(
    "/personas/{persona_id}/audit/snapshots",
    response_model=SnapshotRead,
    status_code=status.HTTP_201_CREATED,
)
def create_manual_snapshot(
    persona_id: str,
    payload: SnapshotCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_persona_or_404(persona_id, current_user, db)
    snapshot = create_snapshot(
        db,
        persona_id=persona_id,
        snapshot_type=payload.snapshot_type,
        label=payload.label,
    )
    return SnapshotRead.model_validate(snapshot)


@router.get(
    "/personas/{persona_id}/audit/snapshots",
    response_model=SnapshotListResponse,
)
def list_snapshots(
    persona_id: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_persona_or_404(persona_id, current_user, db)
    snapshots = get_snapshots(db, persona_id, limit=limit)
    return SnapshotListResponse(
        items=[SnapshotRead.model_validate(s) for s in snapshots]
    )


@router.get(
    "/personas/{persona_id}/audit/snapshots/compare",
    response_model=SnapshotCompareResponse,
)
def compare_two_snapshots(
    persona_id: str,
    snapshot_id_a: str,
    snapshot_id_b: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_persona_or_404(persona_id, current_user, db)
    result = compare_snapshots(db, snapshot_id_a, snapshot_id_b)
    return SnapshotCompareResponse(**result)


# ── Rollback ───────────────────────────────────────────────────────────

@router.post(
    "/personas/{persona_id}/audit/rollback",
    response_model=RollbackResponse,
)
def rollback_to_previous_snapshot(
    persona_id: str,
    payload: RollbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_persona_or_404(persona_id, current_user, db)
    if not payload.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rollback requires confirmed=True",
        )
    log = rollback_to_snapshot(
        db,
        user_id=current_user.id,
        snapshot_id=payload.snapshot_id,
        confirmed=True,
    )
    safety_id = (
        log.metadata_json.get("safety_snapshot_id") if log.metadata_json else None
    )
    return RollbackResponse(
        safety_snapshot_id=safety_id or "",
        rollback_event_id=log.id,
    )


# ── Conflicts ──────────────────────────────────────────────────────────

@router.get(
    "/personas/{persona_id}/audit/conflicts",
    response_model=ConflictListResponse,
)
def list_conflicts(
    persona_id: str,
    resolution_status: str | None = "open",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.memory_conflict import MemoryConflict

    get_persona_or_404(persona_id, current_user, db)
    stmt = select(MemoryConflict).where(MemoryConflict.persona_id == persona_id)
    if resolution_status:
        stmt = stmt.where(MemoryConflict.resolution_status == resolution_status)
    conflicts = list(db.scalars(stmt.order_by(MemoryConflict.created_at.desc())).all())
    return ConflictListResponse(
        items=[ConflictRead.model_validate(c) for c in conflicts]
    )


@router.post(
    "/personas/{persona_id}/audit/conflicts/{conflict_id}/resolve",
    response_model=ConflictRead,
)
def resolve_memory_conflict(
    persona_id: str,
    conflict_id: str,
    payload: ResolveConflictRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_persona_or_404(persona_id, current_user, db)
    conflict = resolve_conflict(
        db, conflict_id, current_user.id, payload.resolution
    )
    return ConflictRead.model_validate(conflict)


# ── Drifts ─────────────────────────────────────────────────────────────

@router.get(
    "/personas/{persona_id}/audit/drifts",
    response_model=DriftListResponse,
)
def list_drifts(
    persona_id: str,
    unacknowledged_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.persona_drift import PersonaDrift

    get_persona_or_404(persona_id, current_user, db)
    stmt = select(PersonaDrift).where(PersonaDrift.persona_id == persona_id)
    if unacknowledged_only:
        stmt = stmt.where(
            PersonaDrift.triggered_alert.is_(True),
            PersonaDrift.acknowledged_at.is_(None),
        )
    drifts = list(db.scalars(stmt.order_by(PersonaDrift.created_at.desc())).all())
    return DriftListResponse(items=[DriftRead.model_validate(d) for d in drifts])


@router.post(
    "/personas/{persona_id}/audit/drifts/{drift_id}/acknowledge",
    response_model=DriftRead,
)
def acknowledge_persona_drift(
    persona_id: str,
    drift_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.persona_drift import PersonaDrift

    get_persona_or_404(persona_id, current_user, db)
    drift = db.get(PersonaDrift, drift_id)
    if not drift or drift.persona_id != persona_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    drift.acknowledged_at = datetime.now(timezone.utc)
    db.add(drift)
    db.commit()
    db.refresh(drift)
    return DriftRead.model_validate(drift)


# ── Dashboard ──────────────────────────────────────────────────────────

@router.get(
    "/personas/{persona_id}/audit/dashboard",
    response_model=AuditDashboardResponse,
)
def audit_dashboard(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_persona_or_404(persona_id, current_user, db)
    return AuditDashboardResponse(**get_audit_dashboard(db, persona_id))
