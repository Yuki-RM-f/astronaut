from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import inspect, select, func
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.memory_card import MemoryCard
from app.models.memory_conflict import MemoryConflict
from app.models.persona import Persona
from app.models.persona_profile import PersonaProfile


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (set, frozenset)):
        return list(value)
    return value


# ── write ──────────────────────────────────────────────────────────────────

def write_audit_event(
    db: Session,
    *,
    user_id: str,
    persona_id: str,
    target_type: str,
    target_id: str | None = None,
    event_type: str = "memory.updated",
    severity: str = "info",
    action: str = "",
    before_snapshot: dict | None = None,
    after_snapshot: dict | None = None,
    changed_fields: list[str] | None = None,
    correlation_id: str | None = None,
    parent_event_id: str | None = None,
    metadata_json: dict | None = None,
    commit: bool = True,
) -> AuditLog:
    log = AuditLog(
        user_id=user_id,
        persona_id=persona_id,
        target_type=target_type,
        target_id=target_id,
        event_type=event_type,
        severity=severity,
        action=action,
        before_json=before_snapshot,
        after_json=after_snapshot,
        changed_fields=changed_fields or [],
        correlation_id=correlation_id,
        parent_event_id=parent_event_id,
        metadata_json=metadata_json,
    )
    db.add(log)
    if commit:
        db.commit()
        db.refresh(log)
    else:
        db.flush()
    return log


def snapshot_entity(model_instance: Any) -> dict[str, Any]:
    insp = inspect(model_instance)
    return {
        col.key: _json_safe(getattr(model_instance, col.key))
        for col in insp.mapper.column_attrs
    }


def diff_before_after(before: dict, after: dict) -> list[str]:
    changed = []
    all_keys = set(before.keys()) | set(after.keys())
    for key in sorted(all_keys):
        if before.get(key) != after.get(key):
            changed.append(key)
    return changed


# ── query ──────────────────────────────────────────────────────────────────

def query_audit_logs(
    db: Session,
    *,
    persona_id: str,
    event_type: str | None = None,
    severity: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    user_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    correlation_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    stmt = select(AuditLog).where(AuditLog.persona_id == persona_id)
    count_stmt = select(func.count(AuditLog.id)).where(AuditLog.persona_id == persona_id)

    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
        count_stmt = count_stmt.where(AuditLog.event_type == event_type)
    if severity:
        stmt = stmt.where(AuditLog.severity == severity)
        count_stmt = count_stmt.where(AuditLog.severity == severity)
    if target_type:
        stmt = stmt.where(AuditLog.target_type == target_type)
        count_stmt = count_stmt.where(AuditLog.target_type == target_type)
    if target_id:
        stmt = stmt.where(AuditLog.target_id == target_id)
        count_stmt = count_stmt.where(AuditLog.target_id == target_id)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
        count_stmt = count_stmt.where(AuditLog.user_id == user_id)
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= date_from)
        count_stmt = count_stmt.where(AuditLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.created_at <= date_to)
        count_stmt = count_stmt.where(AuditLog.created_at <= date_to)
    if correlation_id:
        stmt = stmt.where(AuditLog.correlation_id == correlation_id)
        count_stmt = count_stmt.where(AuditLog.correlation_id == correlation_id)

    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return list(items), total


def get_memory_change_history(
    db: Session, memory_id: str, limit: int = 100
) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.target_type == "memory_card", AuditLog.target_id == memory_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
        ).all()
    )


def get_audit_summary(db: Session, persona_id: str) -> dict:
    total_events = (
        db.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.persona_id == persona_id)
        )
        or 0
    )

    by_severity: dict[str, int] = {}
    for sev in ("critical", "warning", "info", "debug"):
        by_severity[sev] = (
            db.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.persona_id == persona_id, AuditLog.severity == sev
                )
            )
            or 0
        )

    rows = db.execute(
        select(AuditLog.event_type, func.count(AuditLog.id))
        .where(AuditLog.persona_id == persona_id)
        .group_by(AuditLog.event_type)
    ).all()
    by_event_type = {event_type: count for event_type, count in rows}

    open_conflicts = (
        db.scalar(
            select(func.count(MemoryConflict.id)).where(
                MemoryConflict.persona_id == persona_id,
                MemoryConflict.resolution_status == "open",
            )
        )
        or 0
    )

    return {
        "total_events": total_events,
        "by_severity": by_severity,
        "by_event_type": by_event_type,
        "open_conflicts": open_conflicts,
    }


def generate_audit_report(db: Session, persona_id: str) -> dict:
    persona = db.get(Persona, persona_id)
    timeline, _ = query_audit_logs(db, persona_id=persona_id, limit=200)

    conflicts = list(
        db.scalars(
            select(MemoryConflict)
            .where(MemoryConflict.persona_id == persona_id)
            .order_by(MemoryConflict.created_at.desc())
        ).all()
    )

    memory_count = (
        db.scalar(
            select(func.count(MemoryCard.id)).where(
                MemoryCard.persona_id == persona_id,
                MemoryCard.deleted_at.is_(None),
            )
        )
        or 0
    )

    unique_sources = (
        db.scalar(
            select(func.count(func.distinct(MemoryCard.source_material_id))).where(
                MemoryCard.persona_id == persona_id,
                MemoryCard.deleted_at.is_(None),
                MemoryCard.source_material_id.is_not(None),
            )
        )
        or 0
    )

    def _log_to_dict(log: AuditLog) -> dict:
        return {
            "id": log.id,
            "event_type": log.event_type,
            "severity": log.severity,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }

    def _conflict_to_dict(c: MemoryConflict) -> dict:
        return {
            "id": c.id,
            "conflict_type": c.conflict_type,
            "conflict_description": c.conflict_description,
            "resolution_status": c.resolution_status,
            "severity": c.severity,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }

    return {
        "report_generated_at": _utcnow().isoformat(),
        "persona_name": persona.name if persona else "",
        "summary": get_audit_summary(db, persona_id),
        "timeline": [_log_to_dict(log) for log in timeline],
        "conflicts": [_conflict_to_dict(c) for c in conflicts],
        "source_coverage": {
            "total_memories": memory_count,
            "unique_sources_used": unique_sources,
        },
    }


# ── dashboard ──────────────────────────────────────────────────────────────

def get_audit_dashboard(db: Session, persona_id: str) -> dict:
    active_memories = list(
        db.scalars(
            select(MemoryCard).where(
                MemoryCard.persona_id == persona_id,
                MemoryCard.deleted_at.is_(None),
            )
        ).all()
    )

    total_active = len(active_memories)
    pending_count = sum(
        1 for m in active_memories if m.status in ("pending_review", "auto_generated")
    )
    review_rate = (
        (total_active - pending_count) / total_active * 40 if total_active > 0 else 0
    )

    confidence_avg = (
        sum(m.confidence_score or 0 for m in active_memories) / total_active
        if total_active > 0
        else 0
    )
    confidence_score_part = (confidence_avg / 100) * 30

    traceable = sum(
        1 for m in active_memories if m.source_quote and m.source_location
    )
    traceability_ratio = traceable / total_active * 30 if total_active > 0 else 0

    health_score = round(review_rate + confidence_score_part + traceability_ratio)
    health_score = max(0, min(100, health_score))

    summary = get_audit_summary(db, persona_id)

    recent = list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.persona_id == persona_id,
                AuditLog.severity.in_(["info", "warning", "critical"]),
            )
            .order_by(AuditLog.created_at.desc())
            .limit(10)
        ).all()
    )

    def _event_summary(log: AuditLog) -> dict:
        return {
            "id": log.id,
            "event_type": log.event_type,
            "severity": log.severity,
            "action": log.action,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }

    source_types: dict[str, int] = {}
    categories: dict[str, int] = {}
    statuses: dict[str, int] = {}
    confidence_levels: dict[str, int] = {}
    for m in active_memories:
        st = m.source_type or "unknown"
        source_types[st] = source_types.get(st, 0) + 1
        categories[m.category] = categories.get(m.category, 0) + 1
        statuses[m.status] = statuses.get(m.status, 0) + 1
        cl = m.confidence_level or "unknown"
        confidence_levels[cl] = confidence_levels.get(cl, 0) + 1

    unique_sources = len({m.source_material_id for m in active_memories if m.source_material_id})

    return {
        "memory_health_score": health_score,
        "review_queue_size": pending_count,
        "open_conflict_count": summary["open_conflicts"],
        "recent_events": [_event_summary(e) for e in recent],
        "source_coverage": {
            "total_memories": total_active,
            "unique_sources_used": unique_sources,
            "memories_by_source_type": source_types,
            "memories_by_category": categories,
            "memories_by_status": statuses,
            "memories_by_confidence": confidence_levels,
        },
    }
