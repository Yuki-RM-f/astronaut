from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
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
    MemoryHistoryResponse,
    ResolveConflictRequest,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.services.audit import (
    generate_audit_report,
    get_audit_dashboard,
    get_audit_summary,
    get_memory_change_history,
    query_audit_logs,
)
from app.services.conflict_detector import resolve_conflict
from app.services.materials import get_persona_or_404
from app.services.semantic_search import semantic_search

router = APIRouter(tags=["audit"])


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s)


# ── Audit Logs ────────────────────────────────────────────────────────────

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


# ── Conflicts ─────────────────────────────────────────────────────────────

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


# ── Dashboard ─────────────────────────────────────────────────────────────

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


# ── Semantic Search ───────────────────────────────────────────────────────

@router.post(
    "/personas/{persona_id}/audit/search",
    response_model=SearchResponse,
)
def search_memories(
    persona_id: str,
    payload: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.memory_card import MemoryCard
    from app.services.audit import write_audit_event

    get_persona_or_404(persona_id, current_user, db)

    memories = list(
        db.scalars(
            __import__("sqlalchemy").select(MemoryCard).where(
                MemoryCard.persona_id == persona_id,
                MemoryCard.deleted_at.is_(None),
                MemoryCard.status.not_in(["rejected", "disabled"]),
            )
        ).all()
    )

    mem_dicts = [
        {
            "id": m.id,
            "title": m.title or "",
            "content": m.user_correction or m.content or "",
            "source_quote": m.source_quote,
            "source_location": m.source_location,
            "confidence_score": m.confidence_score,
            "confidence_level": m.confidence_level,
            "category": m.category or "",
            "status": m.status or "",
        }
        for m in memories
    ]

    results = semantic_search(payload.query, mem_dicts, top_k=payload.top_k)

    write_audit_event(
        db,
        user_id=current_user.id,
        persona_id=persona_id,
        target_type="memory_search",
        target_id=None,
        event_type="memory.searched",
        severity="debug",
        action=f"Search: '{payload.query}' → {len(results)} results",
        metadata_json={
            "query": payload.query,
            "result_count": len(results),
            "top_k": payload.top_k,
        },
    )

    return SearchResponse(
        query=payload.query,
        results=[SearchResultItem(**r) for r in results],
        total_found=len(results),
    )
