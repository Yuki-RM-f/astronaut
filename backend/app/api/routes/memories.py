from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.memory_card import MemoryCard
from app.models.persona import Persona
from app.models.source_material import SourceMaterial
from app.models.user import User
from app.schemas.memory import (
    AllowedConfidenceLevel,
    AllowedMemoryCategory,
    AllowedMemoryStatus,
    MemoryCreate,
    MemoryListResponse,
    MemoryRead,
    MemoryUpdate,
)
from app.services.materials import get_persona_or_404
from app.services.memory_markdown import refresh_long_term_memory_md
from app.services.profile import refresh_profile_and_trust
from app.services.audit import snapshot_entity, write_audit_event
from app.services.conflict_detector import detect_conflicts_for_memory


router = APIRouter(tags=["memories"])


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _memory_response(memory: MemoryCard) -> MemoryRead:
    return MemoryRead.model_validate(memory)


def _get_memory_or_404(memory_id: str, user: User, db: Session) -> MemoryCard:
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


def _get_source_material_or_404(
    material_id: str,
    persona_id: str,
    user: User,
    db: Session,
) -> SourceMaterial:
    material = db.scalar(
        select(SourceMaterial).where(
            SourceMaterial.id == material_id,
            SourceMaterial.user_id == user.id,
            SourceMaterial.persona_id == persona_id,
            SourceMaterial.deleted_at.is_(None),
        )
    )
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return material


def _refresh_profile_for_memory(memory: MemoryCard, db: Session) -> None:
    persona = db.get(Persona, memory.persona_id)
    if persona is not None:
        refresh_profile_and_trust(db, persona)
        refresh_long_term_memory_md(db, persona)


@router.get("/personas/{persona_id}/memories", response_model=MemoryListResponse)
def list_memories(
    persona_id: str,
    status: AllowedMemoryStatus | None = None,
    category: AllowedMemoryCategory | None = None,
    confidence_level: AllowedConfidenceLevel | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    statement = select(MemoryCard).where(
        MemoryCard.persona_id == persona.id,
        MemoryCard.deleted_at.is_(None),
    )
    if status is not None:
        statement = statement.where(MemoryCard.status == status)
    if category is not None:
        statement = statement.where(MemoryCard.category == category)
    if confidence_level is not None:
        statement = statement.where(MemoryCard.confidence_level == confidence_level)

    memories = db.scalars(
        statement.order_by(MemoryCard.created_at.desc(), MemoryCard.id.desc())
    ).all()
    return MemoryListResponse(items=[_memory_response(memory) for memory in memories])


@router.post(
    "/personas/{persona_id}/memories",
    response_model=MemoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_memory(
    persona_id: str,
    payload: MemoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    material = _get_source_material_or_404(
        payload.source_material_id,
        persona.id,
        current_user,
        db,
    )
    memory = MemoryCard(
        persona_id=persona.id,
        title=payload.title,
        content=payload.content,
        category=payload.category,
        confidence_level=payload.confidence_level,
        confidence_score=payload.confidence_score,
        source_material_id=material.id,
        source_type=material.file_type,
        source_quote=payload.source_quote,
        source_location=payload.source_location,
        evidence_json=payload.evidence_json,
        status=payload.status,
        is_important=payload.is_important,
        created_by="user",
    )
    db.add(memory)
    db.flush()
    write_audit_event(
        db,
        user_id=current_user.id,
        persona_id=persona.id,
        target_type="memory",
        target_id=memory.id,
        event_type="memory.created",
        action="创建记忆卡片",
        after_snapshot=snapshot_entity(memory),
    )
    if memory.status in {"confirmed", "corrected"}:
        refresh_long_term_memory_md(db, persona)
        detect_conflicts_for_memory(db, memory)
    db.commit()
    db.refresh(memory)
    return _memory_response(memory)


@router.get("/memories/{memory_id}", response_model=MemoryRead)
def get_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _memory_response(_get_memory_or_404(memory_id, current_user, db))


@router.patch("/memories/{memory_id}", response_model=MemoryRead)
def update_memory(
    memory_id: str,
    payload: MemoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memory = _get_memory_or_404(memory_id, current_user, db)
    before = snapshot_entity(memory)
    updates = payload.model_dump(exclude_unset=True)
    content_or_title_changed = "title" in updates or "content" in updates
    for field, value in updates.items():
        setattr(memory, field, value)
    if content_or_title_changed:
        memory.status = "corrected"
        memory.user_correction = memory.content
    db.add(memory)
    _refresh_profile_for_memory(memory, db)
    db.flush()
    write_audit_event(
        db,
        user_id=current_user.id,
        persona_id=memory.persona_id,
        target_type="memory",
        target_id=memory.id,
        event_type="memory.updated",
        action="更新记忆卡片",
        before_snapshot=before,
        after_snapshot=snapshot_entity(memory),
    )
    detect_conflicts_for_memory(db, memory)
    db.commit()
    db.refresh(memory)
    return _memory_response(memory)


def _set_memory_status(
    memory_id: str,
    new_status: str,
    user: User,
    db: Session,
) -> MemoryRead:
    memory = _get_memory_or_404(memory_id, user, db)
    before = snapshot_entity(memory)
    memory.status = new_status
    db.add(memory)
    _refresh_profile_for_memory(memory, db)
    db.flush()
    write_audit_event(
        db,
        user_id=user.id,
        persona_id=memory.persona_id,
        target_type="memory",
        target_id=memory.id,
        event_type=f"memory.{_status_event_name(new_status)}",
        action=f"记忆状态改为 {new_status}",
        before_snapshot=before,
        after_snapshot=snapshot_entity(memory),
    )
    detect_conflicts_for_memory(db, memory)
    db.commit()
    db.refresh(memory)
    return _memory_response(memory)


@router.post("/memories/{memory_id}/confirm", response_model=MemoryRead)
def confirm_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _set_memory_status(memory_id, "confirmed", current_user, db)


@router.post("/memories/{memory_id}/reject", response_model=MemoryRead)
def reject_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _set_memory_status(memory_id, "rejected", current_user, db)


@router.post("/memories/{memory_id}/disable", response_model=MemoryRead)
def disable_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _set_memory_status(memory_id, "disabled", current_user, db)


@router.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memory = _get_memory_or_404(memory_id, current_user, db)
    before = snapshot_entity(memory)
    memory.deleted_at = _utcnow()
    db.add(memory)
    _refresh_profile_for_memory(memory, db)
    db.flush()
    write_audit_event(
        db,
        user_id=current_user.id,
        persona_id=memory.persona_id,
        target_type="memory",
        target_id=memory.id,
        event_type="memory.deleted",
        action="删除记忆卡片",
        before_snapshot=before,
        after_snapshot=snapshot_entity(memory),
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _status_event_name(new_status: str) -> str:
    return {
        "confirmed": "confirmed",
        "rejected": "rejected",
        "disabled": "disabled",
    }.get(new_status, "updated")
