from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.memory_card import MemoryCard
from app.models.memory_conflict import MemoryConflict
from app.models.persona import Persona
from app.services.audit import snapshot_entity, write_audit_event


REVIEWED_STATUSES = {"confirmed", "corrected"}
NEGATIVE_MARKERS = ("不喜欢", "不爱", "讨厌", "不会", "从不", "没有", "不能")
POSITIVE_MARKERS = ("喜欢", "爱", "常常", "经常", "会", "总是")


def detect_conflicts_for_memory(db: Session, memory: MemoryCard) -> list[MemoryConflict]:
    if memory.status not in REVIEWED_STATUSES or memory.deleted_at is not None:
        return []
    persona = db.get(Persona, memory.persona_id)
    if persona is None:
        return []

    candidates = db.scalars(
        select(MemoryCard).where(
            MemoryCard.persona_id == memory.persona_id,
            MemoryCard.id != memory.id,
            MemoryCard.deleted_at.is_(None),
            MemoryCard.status.in_(REVIEWED_STATUSES),
        )
    ).all()

    created: list[MemoryConflict] = []
    for candidate in candidates:
        if not _looks_conflicting(memory, candidate):
            continue
        if _existing_conflict(db, memory.id, candidate.id) is not None:
            continue
        conflict = MemoryConflict(
            persona_id=memory.persona_id,
            memory_id_a=candidate.id,
            memory_id_b=memory.id,
            conflict_type="contradiction",
            conflict_description=(
                f"“{candidate.title}” 与 “{memory.title}” 可能存在正反表述冲突。"
            ),
            severity="medium",
        )
        db.add(conflict)
        db.flush()
        write_audit_event(
            db,
            user_id=persona.user_id,
            persona_id=persona.id,
            target_type="memory_conflict",
            target_id=conflict.id,
            event_type="memory.conflict_detected",
            severity="warning",
            action="检测到两条记忆之间存在潜在冲突",
            after_snapshot=snapshot_entity(conflict),
            metadata_json={
                "memory_id_a": candidate.id,
                "memory_id_b": memory.id,
            },
        )
        created.append(conflict)
    return created


def resolve_conflict(
    db: Session,
    *,
    persona: Persona,
    conflict_id: str,
    user_id: str,
    resolution_status: str,
) -> MemoryConflict | None:
    conflict = db.scalar(
        select(MemoryConflict).where(
            MemoryConflict.id == conflict_id,
            MemoryConflict.persona_id == persona.id,
        )
    )
    if conflict is None:
        return None
    before = snapshot_entity(conflict)
    conflict.resolution_status = resolution_status
    conflict.resolved_by = user_id
    conflict.resolved_at = datetime.now(UTC).replace(tzinfo=None)
    db.add(conflict)
    db.flush()
    write_audit_event(
        db,
        user_id=user_id,
        persona_id=persona.id,
        target_type="memory_conflict",
        target_id=conflict.id,
        event_type="memory.conflict_resolved",
        severity="info",
        action=f"处理记忆冲突为 {resolution_status}",
        before_snapshot=before,
        after_snapshot=snapshot_entity(conflict),
    )
    return conflict


def _existing_conflict(db: Session, memory_id_a: str, memory_id_b: str) -> MemoryConflict | None:
    return db.scalar(
        select(MemoryConflict).where(
            or_(
                (
                    (MemoryConflict.memory_id_a == memory_id_a)
                    & (MemoryConflict.memory_id_b == memory_id_b)
                ),
                (
                    (MemoryConflict.memory_id_a == memory_id_b)
                    & (MemoryConflict.memory_id_b == memory_id_a)
                ),
            )
        )
    )


def _looks_conflicting(first: MemoryCard, second: MemoryCard) -> bool:
    if first.category != second.category:
        return False
    first_text = _normalize(first.content)
    second_text = _normalize(second.content)
    if not first_text or not second_text:
        return False
    first_negative = _has_marker(first_text, NEGATIVE_MARKERS)
    second_negative = _has_marker(second_text, NEGATIVE_MARKERS)
    if first_negative == second_negative:
        return False
    first_positive = _has_marker(first_text, POSITIVE_MARKERS)
    second_positive = _has_marker(second_text, POSITIVE_MARKERS)
    if not (first_positive or second_positive):
        return False
    first_terms = _terms(first_text)
    second_terms = _terms(second_text)
    return bool(first_terms & second_terms)


def _has_marker(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _terms(text: str) -> set[str]:
    cleaned = text
    for marker in (*NEGATIVE_MARKERS, *POSITIVE_MARKERS):
        cleaned = cleaned.replace(marker, "")
    words = set(re.findall(r"[\u4e00-\u9fff]{2,}", cleaned))
    food_tail = {word[-2:] for word in words if len(word) > 2}
    return words | food_tail


def _normalize(text: str | None) -> str:
    return re.sub(r"\s+", "", text or "")
