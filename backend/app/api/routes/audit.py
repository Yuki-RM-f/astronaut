from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.memory_card import MemoryCard
from app.models.memory_conflict import MemoryConflict
from app.models.persona import Persona
from app.models.user import User
from app.schemas.audit import (
    AuditDashboardResponse,
    AuditLogListResponse,
    AuditReportResponse,
    AuditSummaryResponse,
    MemoryConflictListResponse,
    MemoryConflictRead,
    MemoryHistoryResponse,
    ResolveConflictRequest,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.schemas.memory import MemoryRead
from app.services.audit import (
    audit_dashboard,
    audit_report,
    audit_summary,
    enrich_conflicts,
    list_audit_logs,
    memory_history,
    write_audit_event,
)
from app.services.conflict_detector import resolve_conflict
from app.services.materials import get_persona_or_404
from app.services.semantic_search import semantic_search


router = APIRouter(tags=["audit"])


@router.get(
    "/personas/{persona_id}/audit/logs",
    response_model=AuditLogListResponse,
)
def get_audit_logs(
    persona_id: str,
    event_type: str | None = None,
    severity: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    correlation_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    logs, total = list_audit_logs(
        db,
        persona=persona,
        event_type=event_type,
        severity=severity,
        target_type=target_type,
        target_id=target_id,
        correlation_id=correlation_id,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(items=logs, total=total, limit=limit, offset=offset)


@router.get(
    "/personas/{persona_id}/audit/summary",
    response_model=AuditSummaryResponse,
)
def get_audit_summary(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    return audit_summary(db, persona)


@router.get(
    "/personas/{persona_id}/audit/dashboard",
    response_model=AuditDashboardResponse,
)
def get_audit_dashboard(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    return audit_dashboard(db, persona)


@router.get(
    "/personas/{persona_id}/audit/report",
    response_model=AuditReportResponse,
)
def get_audit_report(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    return audit_report(db, persona)


@router.get(
    "/personas/{persona_id}/audit/conflicts",
    response_model=MemoryConflictListResponse,
)
def get_conflicts(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    conflicts = db.scalars(
        select(MemoryConflict)
        .where(MemoryConflict.persona_id == persona.id)
        .order_by(MemoryConflict.created_at.desc(), MemoryConflict.id.desc())
    ).all()
    items = enrich_conflicts(db, list(conflicts))
    return MemoryConflictListResponse(items=items, total=len(items))


@router.post(
    "/personas/{persona_id}/audit/conflicts/{conflict_id}/resolve",
    response_model=MemoryConflictRead,
)
def post_resolve_conflict(
    persona_id: str,
    conflict_id: str,
    payload: ResolveConflictRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    conflict = resolve_conflict(
        db,
        persona=persona,
        conflict_id=conflict_id,
        user_id=current_user.id,
        resolution_status=payload.resolution_status,
    )
    if conflict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()
    db.refresh(conflict)
    return enrich_conflicts(db, [conflict])[0]


@router.post(
    "/personas/{persona_id}/audit/search",
    response_model=SearchResponse,
)
def post_audit_search(
    persona_id: str,
    payload: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    results = semantic_search(db, persona=persona, query=payload.query, top_k=payload.top_k)
    write_audit_event(
        db,
        user_id=current_user.id,
        persona_id=persona.id,
        target_type="memory",
        target_id=None,
        event_type="memory.searched",
        action=f"审计语义搜索：{payload.query}",
        severity="debug",
        metadata_json={
            "query": payload.query,
            "top_k": payload.top_k,
            "result_memory_ids": [item.memory.id for item in results],
        },
    )
    db.commit()
    return SearchResponse(
        query=payload.query,
        total=len(results),
        items=[
            SearchResultItem(
                memory=MemoryRead.model_validate(item.memory),
                relevance_score=item.relevance_score,
                matched_terms=item.matched_terms,
                source_excerpt=item.source_excerpt,
            )
            for item in results
        ],
    )


@router.get("/memories/{memory_id}/history", response_model=MemoryHistoryResponse)
def get_memory_history(
    memory_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memory = _get_memory_for_user_or_404(db, current_user, memory_id)
    return memory_history(db, memory=memory)


def _get_memory_for_user_or_404(db: Session, user: User, memory_id: str) -> MemoryCard:
    memory = db.scalar(
        select(MemoryCard)
        .join(Persona, MemoryCard.persona_id == Persona.id)
        .where(
            MemoryCard.id == memory_id,
            MemoryCard.deleted_at.is_(None),
            Persona.user_id == user.id,
            Persona.deleted_at.is_(None),
        )
    )
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return memory
