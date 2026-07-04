from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_snapshot import AuditSnapshot
from app.models.persona_drift import PersonaDrift
from app.schemas.profile import PROFILE_DIMENSION_FIELDS


DRIFT_THRESHOLDS = {
    "trust_score": 15,
    "memory_count": 0.30,
    "profile_dimension": 0.40,
}


def detect_drift_between_snapshots(
    db: Session,
    snapshot_before: AuditSnapshot,
    snapshot_after: AuditSnapshot,
    commit: bool = True,
) -> list[PersonaDrift]:
    from app.services.audit import write_audit_event

    drifts: list[PersonaDrift] = []
    persona_id: str = snapshot_before.persona_id

    trust_delta = abs(snapshot_after.trust_score - snapshot_before.trust_score)
    if trust_delta >= DRIFT_THRESHOLDS["trust_score"]:
        drift = PersonaDrift(
            persona_id=persona_id,
            snapshot_id_before=snapshot_before.id,
            snapshot_id_after=snapshot_after.id,
            dimension="trust_score",
            drift_score=min(1.0, trust_delta / 100.0),
            before_summary=f"Trust score: {snapshot_before.trust_score}",
            after_summary=f"Trust score: {snapshot_after.trust_score}",
            triggered_alert=True,
        )
        db.add(drift)
        drifts.append(drift)

    if snapshot_before.memory_count > 0:
        count_ratio = abs(
            snapshot_after.memory_count - snapshot_before.memory_count
        ) / snapshot_before.memory_count
        if count_ratio >= DRIFT_THRESHOLDS["memory_count"]:
            drift = PersonaDrift(
                persona_id=persona_id,
                snapshot_id_before=snapshot_before.id,
                snapshot_id_after=snapshot_after.id,
                dimension="memory_count",
                drift_score=min(1.0, count_ratio),
                before_summary=f"Memory count: {snapshot_before.memory_count}",
                after_summary=f"Memory count: {snapshot_after.memory_count}",
                triggered_alert=True,
            )
            db.add(drift)
            drifts.append(drift)

    before_profile = snapshot_before.profile_snapshot or {}
    after_profile = snapshot_after.profile_snapshot or {}
    for dim in PROFILE_DIMENSION_FIELDS:
        before_entries = _to_list(before_profile.get(dim, []))
        after_entries = _to_list(after_profile.get(dim, []))
        if not before_entries and not after_entries:
            continue

        before_ids = {
            e.get("memory_id") for e in before_entries if isinstance(e, dict)
        }
        after_ids = {
            e.get("memory_id") for e in after_entries if isinstance(e, dict)
        }
        if not before_ids and not after_ids:
            continue
        intersection = len(before_ids & after_ids)
        union = len(before_ids | after_ids)
        if union == 0:
            continue
        jaccard_dist = 1.0 - (intersection / union)
        if jaccard_dist >= DRIFT_THRESHOLDS["profile_dimension"]:
            drift = PersonaDrift(
                persona_id=persona_id,
                snapshot_id_before=snapshot_before.id,
                snapshot_id_after=snapshot_after.id,
                dimension=dim,
                drift_score=round(jaccard_dist, 4),
                before_summary=f"{dim}: {len(before_ids)} entries",
                after_summary=f"{dim}: {len(after_ids)} entries",
                triggered_alert=True,
            )
            db.add(drift)
            drifts.append(drift)

    for d in drifts:
        write_audit_event(
            db,
            user_id="system",
            persona_id=persona_id,
            target_type="persona_drift",
            target_id=d.id,
            event_type="drift.detected",
            severity="warning",
            action=f"Significant drift in {d.dimension}: {d.before_summary} -> {d.after_summary}",
            commit=False,
        )

    if commit and drifts:
        db.commit()
    return drifts


def check_drift_after_profile_change(
    db: Session,
    persona_id: str,
    commit: bool = True,
) -> list[PersonaDrift]:
    from app.services.audit import create_snapshot

    prev = db.scalar(
        select(AuditSnapshot)
        .where(AuditSnapshot.persona_id == persona_id)
        .order_by(AuditSnapshot.created_at.desc())
        .limit(1)
    )

    new_snapshot = create_snapshot(
        db,
        persona_id=persona_id,
        snapshot_type="auto_periodic",
        label="Auto snapshot after change",
        commit=False,
    )

    if prev:
        return detect_drift_between_snapshots(db, prev, new_snapshot, commit=commit)

    if commit:
        db.commit()
    return []


def _to_list(value: object) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
