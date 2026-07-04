from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.memory_card import MemoryCard
from app.models.memory_conflict import MemoryConflict
from app.models.persona import Persona
from app.models.source_material import SourceMaterial


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def snapshot_entity(entity: object | None) -> dict[str, Any] | None:
    if entity is None:
        return None
    mapper = inspect(entity).mapper
    data: dict[str, Any] = {}
    for column in mapper.column_attrs:
        data[column.key] = _jsonable(getattr(entity, column.key))
    return data


def diff_fields(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> list[str]:
    if before is None and after is None:
        return []
    if before is None:
        return sorted((after or {}).keys())
    if after is None:
        return sorted(before.keys())
    fields = set(before) | set(after)
    return sorted(field for field in fields if before.get(field) != after.get(field))


def write_audit_event(
    db: Session,
    *,
    user_id: str,
    persona_id: str | None,
    target_type: str,
    target_id: str | None = None,
    event_type: str,
    action: str,
    severity: str = "info",
    before_snapshot: dict[str, Any] | None = None,
    after_snapshot: dict[str, Any] | None = None,
    changed_fields: list[str] | None = None,
    correlation_id: str | None = None,
    parent_event_id: str | None = None,
    metadata_json: dict[str, Any] | list[Any] | None = None,
) -> AuditLog:
    event = AuditLog(
        user_id=user_id,
        persona_id=persona_id,
        target_type=target_type,
        target_id=target_id,
        action=action,
        event_type=event_type,
        severity=severity,
        changed_fields=changed_fields
        if changed_fields is not None
        else diff_fields(before_snapshot, after_snapshot),
        before_json=before_snapshot,
        after_json=after_snapshot,
        correlation_id=correlation_id,
        parent_event_id=parent_event_id,
        metadata_json=metadata_json,
    )
    db.add(event)
    db.flush()
    return event


def list_audit_logs(
    db: Session,
    *,
    persona: Persona,
    event_type: str | None = None,
    severity: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    correlation_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    statement = _audit_statement(
        persona,
        event_type=event_type,
        severity=severity,
        target_type=target_type,
        target_id=target_id,
        correlation_id=correlation_id,
    )
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    logs = db.scalars(
        statement.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return list(logs), total


def audit_summary(db: Session, persona: Persona, *, recent_limit: int = 10) -> dict[str, Any]:
    logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.persona_id == persona.id, AuditLog.user_id == persona.user_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    ).all()
    conflicts = db.scalars(
        select(MemoryConflict).where(MemoryConflict.persona_id == persona.id)
    ).all()
    open_conflicts = [
        conflict for conflict in conflicts if conflict.resolution_status == "open"
    ]
    by_event = Counter(log.event_type for log in logs)
    by_severity = Counter(log.severity for log in logs)
    return {
        "persona_id": persona.id,
        "total_events": len(logs),
        "by_event_type": dict(by_event),
        "by_severity": dict(by_severity),
        "recent_events": list(logs[:recent_limit]),
        "open_conflicts": len(open_conflicts),
        "health_score": _health_score(db, persona, len(open_conflicts)),
    }


def audit_dashboard(db: Session, persona: Persona) -> dict[str, Any]:
    summary = audit_summary(db, persona, recent_limit=8)
    active_memories = db.scalars(
        select(MemoryCard).where(
            MemoryCard.persona_id == persona.id,
            MemoryCard.deleted_at.is_(None),
        )
    ).all()
    pending_review = [memory for memory in active_memories if memory.status == "pending_review"]
    source_coverage = Counter(memory.source_type or "unknown" for memory in active_memories)
    return {
        "persona_id": persona.id,
        "health_score": summary["health_score"],
        "pending_review_count": len(pending_review),
        "open_conflict_count": summary["open_conflicts"],
        "source_coverage": dict(source_coverage),
        "recent_events": summary["recent_events"],
    }


def audit_report(db: Session, persona: Persona) -> dict[str, Any]:
    summary = audit_summary(db, persona, recent_limit=20)
    logs = db.scalars(
        select(AuditLog).where(AuditLog.persona_id == persona.id, AuditLog.user_id == persona.user_id)
    ).all()
    conflicts = db.scalars(
        select(MemoryConflict)
        .where(MemoryConflict.persona_id == persona.id)
        .order_by(MemoryConflict.created_at.desc(), MemoryConflict.id.desc())
    ).all()
    events_by_day = Counter(log.created_at.date().isoformat() for log in logs)
    recommendations: list[str] = []
    if summary["open_conflicts"]:
        recommendations.append("优先处理开放冲突，避免档案中同时存在互相矛盾的记忆。")
    if summary["by_event_type"].get("memory.searched", 0) == 0:
        recommendations.append("可使用语义搜索检查重点记忆是否能被准确召回。")
    if not recommendations:
        recommendations.append("当前审计状态稳定，继续按分类审核记忆即可。")
    return {
        "persona_id": persona.id,
        "generated_at": _utcnow(),
        "summary": summary,
        "events_by_day": dict(events_by_day),
        "conflicts": enrich_conflicts(db, conflicts),
        "recommendations": recommendations,
    }


def memory_history(db: Session, *, memory: MemoryCard) -> dict[str, Any]:
    logs = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.persona_id == memory.persona_id,
            AuditLog.target_type == "memory",
            AuditLog.target_id == memory.id,
        )
        .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
    ).all()
    conflicts = db.scalars(
        select(MemoryConflict)
        .where(
            MemoryConflict.persona_id == memory.persona_id,
            or_(
                MemoryConflict.memory_id_a == memory.id,
                MemoryConflict.memory_id_b == memory.id,
            ),
        )
        .order_by(MemoryConflict.created_at.desc(), MemoryConflict.id.desc())
    ).all()
    return {
        "memory_id": memory.id,
        "events": list(logs),
        "conflicts": enrich_conflicts(db, conflicts),
    }


def enrich_conflicts(
    db: Session,
    conflicts: list[MemoryConflict],
) -> list[dict[str, Any]]:
    memory_ids = {
        memory_id
        for conflict in conflicts
        for memory_id in (conflict.memory_id_a, conflict.memory_id_b)
    }
    memories = {}
    if memory_ids:
        rows = db.scalars(select(MemoryCard).where(MemoryCard.id.in_(memory_ids))).all()
        memories = {memory.id: memory for memory in rows}
    items: list[dict[str, Any]] = []
    for conflict in conflicts:
        base = snapshot_entity(conflict) or {}
        base["memory_title_a"] = getattr(memories.get(conflict.memory_id_a), "title", None)
        base["memory_title_b"] = getattr(memories.get(conflict.memory_id_b), "title", None)
        items.append(base)
    return items


def _audit_statement(
    persona: Persona,
    *,
    event_type: str | None = None,
    severity: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    correlation_id: str | None = None,
):
    statement = select(AuditLog).where(
        AuditLog.persona_id == persona.id,
        AuditLog.user_id == persona.user_id,
    )
    if event_type:
        statement = statement.where(AuditLog.event_type == event_type)
    if severity:
        statement = statement.where(AuditLog.severity == severity)
    if target_type:
        statement = statement.where(AuditLog.target_type == target_type)
    if target_id:
        statement = statement.where(AuditLog.target_id == target_id)
    if correlation_id:
        statement = statement.where(AuditLog.correlation_id == correlation_id)
    return statement


def _health_score(db: Session, persona: Persona, open_conflicts: int) -> int:
    memories = db.scalars(
        select(MemoryCard).where(
            MemoryCard.persona_id == persona.id,
            MemoryCard.deleted_at.is_(None),
        )
    ).all()
    if not memories:
        return 80
    reviewed = [memory for memory in memories if memory.status in {"confirmed", "corrected"}]
    pending = [memory for memory in memories if memory.status == "pending_review"]
    traceable = [memory for memory in memories if memory.source_quote and memory.source_location]
    source_types = {memory.source_type for memory in memories if memory.source_type}
    score = 40
    score += round(len(reviewed) / len(memories) * 25)
    score += round(len(traceable) / len(memories) * 15)
    score += min(len(source_types), 4) * 5
    score -= open_conflicts * 15
    score -= min(len(pending), 5) * 3
    return max(0, min(100, score))


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value
