from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.memory_card import MemoryCard
from app.models.memory_conflict import MemoryConflict


NEGATION_PATTERNS: list[tuple[str, str, str]] = [
    ("喜欢", "不喜欢", "讨厌"),
    ("会", "不会", "从不"),
    ("是", "不是", "并非"),
    ("能", "不能", "无法"),
    ("爱", "不爱", "恨"),
    ("经常", "从不", "偶尔"),
    ("擅长", "不擅长", "不会"),
]

CATEGORY_OVERLAP_RISK: dict[str, list[str]] = {
    "preference": ["preference", "habit"],
    "basic_fact": ["basic_fact"],
    "relationship": ["relationship", "shared_event"],
    "habit": ["habit", "preference"],
}


def detect_conflicts_for_memory(
    db: Session,
    memory: MemoryCard,
    commit: bool = True,
) -> list[MemoryConflict]:
    from app.services.audit import write_audit_event

    risk_categories = CATEGORY_OVERLAP_RISK.get(memory.category, [memory.category])
    candidates = list(
        db.scalars(
            select(MemoryCard).where(
                MemoryCard.persona_id == memory.persona_id,
                MemoryCard.id != memory.id,
                MemoryCard.deleted_at.is_(None),
                MemoryCard.status.not_in(["rejected", "disabled"]),
                MemoryCard.category.in_(risk_categories),
            )
        ).all()
    )

    new_conflicts: list[MemoryConflict] = []
    for other in candidates:
        conflict_desc = _check_contradiction(memory, other)
        if not conflict_desc:
            continue

        existing = db.scalar(
            select(MemoryConflict).where(
                MemoryConflict.persona_id == memory.persona_id,
                MemoryConflict.resolution_status == "open",
                (
                    (MemoryConflict.memory_id_a == memory.id)
                    & (MemoryConflict.memory_id_b == other.id)
                )
                | (
                    (MemoryConflict.memory_id_a == other.id)
                    & (MemoryConflict.memory_id_b == memory.id)
                ),
            )
        )
        if existing:
            continue

        conflict = MemoryConflict(
            persona_id=memory.persona_id,
            memory_id_a=memory.id,
            memory_id_b=other.id,
            conflict_type=_classify_conflict(memory, other),
            conflict_description=conflict_desc,
            severity=_conflict_severity(memory, other),
        )
        db.add(conflict)
        new_conflicts.append(conflict)

    for conflict in new_conflicts:
        write_audit_event(
            db,
            user_id="system",
            persona_id=memory.persona_id,
            target_type="memory_conflict",
            target_id=conflict.id,
            event_type="conflict.detected",
            severity="warning",
            action=conflict.conflict_description,
            after_snapshot={
                "id": conflict.id,
                "memory_id_a": conflict.memory_id_a,
                "memory_id_b": conflict.memory_id_b,
                "conflict_type": conflict.conflict_type,
            },
            commit=False,
        )

    if commit and new_conflicts:
        db.commit()
    return new_conflicts


def resolve_conflict(
    db: Session,
    conflict_id: str,
    user_id: str,
    resolution: str,
) -> MemoryConflict:
    conflict = db.get(MemoryConflict, conflict_id)
    if not conflict:
        raise ValueError(f"Conflict {conflict_id} not found")

    conflict.resolution_status = resolution
    conflict.resolved_by = user_id
    conflict.resolved_at = _utcnow()
    db.add(conflict)
    db.commit()
    db.refresh(conflict)
    return conflict


def _check_contradiction(a: MemoryCard, b: MemoryCard) -> str | None:
    content_a = a.user_correction or a.content
    content_b = b.user_correction or b.content

    for pos, neg1, neg2 in NEGATION_PATTERNS:
        if pos in content_a and (neg1 in content_b or neg2 in content_b):
            return (
                f"Memory A '{a.title}' ({_summarize(content_a)}) contradicts "
                f"Memory B '{b.title}' ({_summarize(content_b)})"
            )
        if pos in content_b and (neg1 in content_a or neg2 in content_a):
            return (
                f"Memory A '{a.title}' ({_summarize(content_a)}) contradicts "
                f"Memory B '{b.title}' ({_summarize(content_b)})"
            )

    zh_words_a = set(re.findall(r"[一-鿿]{2,}", content_a))
    zh_words_b = set(re.findall(r"[一-鿿]{2,}", content_b))
    shared = zh_words_a & zh_words_b
    if len(shared) >= 3 and a.status == "confirmed" and b.status != "confirmed":
        return (
            f"Potential inconsistency: confirmed memory '{a.title}' and "
            f"pending memory '{b.title}' both mention {_fmt_shared(shared)}"
        )

    return None


def _classify_conflict(a: MemoryCard, b: MemoryCard) -> str:
    if a.status == "confirmed" and b.status in ("pending_review", "auto_generated"):
        return "correction_vs_confirmed"
    if a.category == b.category and a.category in ("basic_fact", "preference"):
        return "factual_contradiction"
    return "category_overlap_contradiction"


def _conflict_severity(a: MemoryCard, b: MemoryCard) -> str:
    if a.status == "confirmed" and b.status == "confirmed":
        return "high"
    if a.status == "confirmed" or b.status == "confirmed":
        return "medium"
    return "low"


def _summarize(text: str, max_len: int = 30) -> str:
    return text[:max_len] + ("..." if len(text) > max_len else "")


def _fmt_shared(words: set[str]) -> str:
    return "、".join(list(words)[:5])


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
