from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_job import AIJob
from app.models.memory_card import MemoryCard
from app.models.persona import Persona
from app.models.persona_profile import PersonaProfile
from app.models.source_material import SourceMaterial
from app.schemas.profile import (
    PROFILE_DIMENSION_FIELDS,
    PersonaProfileRead,
    ProfileDimensionEntry,
    TrustComponent,
    TrustReport,
)


CATEGORY_TO_DIMENSION = {
    "basic_fact": "basic_facts",
    "relationship": "relationships",
    "preference": "preferences",
    "habit": "habits",
    "expression_style": "expression_style",
    "shared_event": "shared_events",
    "story_material": "shared_events",
    "value": "values_json",
    "emotional_pattern": "emotional_patterns",
}
REVIEWED_STATUSES = ("confirmed", "corrected")
INACTIVE_STATUSES = ("rejected", "disabled")
TRUST_WEIGHTS = {
    "material_coverage": 0.25,
    "memory_review_rate": 0.25,
    "source_traceability": 0.20,
    "expression_habit_completeness": 0.15,
    "multimodal_completeness": 0.15,
}
MANUAL_OVERRIDE_KEY = "_manual_overrides"
MANUAL_OVERRIDE_FIELDS = (*PROFILE_DIMENSION_FIELDS, "profile_summary")


def get_or_create_profile(db: Session, persona: Persona) -> PersonaProfile:
    profile = db.scalar(
        select(PersonaProfile).where(PersonaProfile.persona_id == persona.id)
    )
    if profile is not None:
        return profile

    profile = PersonaProfile(
        persona_id=persona.id,
        **{field: [] for field in PROFILE_DIMENSION_FIELDS},
        profile_summary=None,
        source_memory_ids={},
    )
    db.add(profile)
    db.flush()
    return profile


def build_profile_from_memories(
    db: Session,
    persona: Persona,
    preserve_manual_overrides: bool = False,
) -> PersonaProfile:
    db.flush()
    profile = get_or_create_profile(db, persona)
    manual_fields = (
        _manual_override_fields(profile) if preserve_manual_overrides else set()
    )
    manual_values = {
        field: getattr(profile, field)
        for field in manual_fields
        if field in MANUAL_OVERRIDE_FIELDS
    }
    memories = db.scalars(
        select(MemoryCard).where(
            MemoryCard.persona_id == persona.id,
            MemoryCard.deleted_at.is_(None),
            MemoryCard.status.in_(REVIEWED_STATUSES),
        )
    ).all()

    dimensions = {field: [] for field in PROFILE_DIMENSION_FIELDS}
    source_memory_ids: dict[str, list[str]] = {}
    entries: list[dict] = []
    for memory in sorted(memories, key=_memory_priority):
        dimension = CATEGORY_TO_DIMENSION.get(memory.category)
        if dimension is None:
            continue
        entry = ProfileDimensionEntry(
            memory_id=memory.id,
            title=memory.title,
            content=memory.content,
            category=memory.category,
            confidence_level=memory.confidence_level,
            status=memory.status,
        ).model_dump()
        dimensions[dimension].append(entry)
        source_memory_ids.setdefault(dimension, []).append(memory.id)
        entries.append(entry)

    for field in manual_fields:
        if field in PROFILE_DIMENSION_FIELDS:
            dimensions[field] = manual_values[field]
            source_memory_ids.pop(field, None)

    for field, value in dimensions.items():
        setattr(profile, field, value)
    profile.source_memory_ids = _with_manual_override_metadata(
        source_memory_ids,
        manual_fields,
    )
    profile.profile_summary = manual_values.get(
        "profile_summary",
        _build_profile_summary(persona, entries),
    )
    db.add(profile)
    db.flush()
    return profile


def calculate_trust_report(db: Session, persona: Persona) -> TrustReport:
    db.flush()
    materials = db.scalars(
        select(SourceMaterial).where(
            SourceMaterial.persona_id == persona.id,
            SourceMaterial.deleted_at.is_(None),
        )
    ).all()
    active_memories = db.scalars(
        select(MemoryCard).where(
            MemoryCard.persona_id == persona.id,
            MemoryCard.deleted_at.is_(None),
            MemoryCard.status.not_in(INACTIVE_STATUSES),
        )
    ).all()
    reviewed_memories = [
        memory for memory in active_memories if memory.status in REVIEWED_STATUSES
    ]

    components = [
        _component(
            "material_coverage",
            _material_coverage_score(materials),
            f"{len(materials)} active materials across "
            f"{len(_material_types(materials))} PRD material type(s)",
        ),
        _component(
            "memory_review_rate",
            _rate_score(len(reviewed_memories), len(active_memories)),
            f"{len(reviewed_memories)} confirmed/corrected active memories out of "
            f"{len(active_memories)}",
        ),
        _component(
            "source_traceability",
            _source_traceability_score(active_memories),
            "active memories with both source_quote and source_location",
        ),
        _component(
            "expression_habit_completeness",
            _expression_habit_score(persona, reviewed_memories),
            "persona speaking/calling style plus confirmed expression memories",
        ),
        _component(
            "multimodal_completeness",
            _multimodal_score(materials),
            "text, image, audio, video coverage; voice/avatar are not available yet",
        ),
    ]
    trust_score = max(
        0,
        min(100, round(sum(component.weighted_score for component in components))),
    )
    return TrustReport(
        trust_score=trust_score,
        trust_level=_trust_level(trust_score),
        components=components,
        suggestions=_suggestions(materials, reviewed_memories, active_memories),
    )


def refresh_profile_and_trust(db: Session, persona: Persona) -> TrustReport:
    from app.services.audit import write_audit_event

    before_trust = persona.trust_score
    build_profile_from_memories(db, persona, preserve_manual_overrides=True)
    report = calculate_trust_report(db, persona)
    persona.trust_score = report.trust_score
    db.add(persona)
    db.flush()

    if abs(persona.trust_score - before_trust) >= 10:
        write_audit_event(
            db,
            user_id="system",
            persona_id=persona.id,
            target_type="persona",
            target_id=persona.id,
            event_type="persona.trust_changed",
            severity="warning",
            action=f"Trust score changed from {before_trust} to {persona.trust_score} ({report.trust_level})",
            changed_fields=["trust_score"],
            commit=False,
        )

    write_audit_event(
        db,
        user_id="system",
        persona_id=persona.id,
        target_type="persona_profile",
        target_id=None,
        event_type="profile.regenerated",
        severity="info",
        action=f"Profile regenerated from {len(report.components)} trust components",
        commit=False,
    )

    return report


def mark_manual_overrides(profile: PersonaProfile, fields: set[str]) -> None:
    manual_fields = _manual_override_fields(profile)
    manual_fields.update(field for field in fields if field in MANUAL_OVERRIDE_FIELDS)
    source_memory_ids = _source_memory_ids(profile)
    for field in manual_fields:
        source_memory_ids.pop(field, None)
    profile.source_memory_ids = _with_manual_override_metadata(
        source_memory_ids,
        manual_fields,
    )


def record_profile_job(
    db: Session,
    persona: Persona,
    job_type: str,
    report: TrustReport,
) -> AIJob:
    now = _utcnow()
    job = AIJob(
        user_id=persona.user_id,
        persona_id=persona.id,
        job_type=job_type,
        provider_type="local",
        provider_name="deterministic_profile_service",
        status="succeeded",
        input_json={"persona_id": persona.id},
        output_json=report.model_dump(),
        started_at=now,
        finished_at=now,
    )
    db.add(job)
    db.flush()
    return job


def profile_response(
    profile: PersonaProfile,
    report: TrustReport,
) -> PersonaProfileRead:
    return PersonaProfileRead(
        id=profile.id,
        persona_id=profile.persona_id,
        basic_facts=profile.basic_facts or [],
        relationships=profile.relationships or [],
        preferences=profile.preferences or [],
        habits=profile.habits or [],
        expression_style=profile.expression_style or [],
        shared_events=profile.shared_events or [],
        values_json=profile.values_json or [],
        emotional_patterns=profile.emotional_patterns or [],
        profile_summary=profile.profile_summary,
        source_memory_ids=_source_memory_ids(profile),
        trust_score=report.trust_score,
        trust_level=report.trust_level,
        components=report.components,
        suggestions=report.suggestions,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _component(name: str, score: int, evidence: str) -> TrustComponent:
    weight = TRUST_WEIGHTS[name]
    bounded_score = max(0, min(100, score))
    return TrustComponent(
        name=name,
        score=bounded_score,
        weight=weight,
        weighted_score=round(bounded_score * weight, 2),
        evidence=evidence,
    )


def _material_coverage_score(materials: list[SourceMaterial]) -> int:
    count_score = min(len(materials), 4) / 4 * 50
    type_score = min(len(_material_types(materials)), 4) / 4 * 50
    return round(count_score + type_score)


def _source_traceability_score(memories: list[MemoryCard]) -> int:
    traceable = [
        memory for memory in memories if memory.source_quote and memory.source_location
    ]
    return _rate_score(len(traceable), len(memories))


def _expression_habit_score(
    persona: Persona,
    reviewed_memories: list[MemoryCard],
) -> int:
    score = 0
    if persona.speaking_style:
        score += 30
    if persona.user_nickname_by_persona:
        score += 20
    if persona.language:
        score += 20
    if any(memory.category == "expression_style" for memory in reviewed_memories):
        score += 30
    return score


def _multimodal_score(materials: list[SourceMaterial]) -> int:
    return round(len(_material_types(materials)) / 4 * 80)


def _rate_score(numerator: int, denominator: int) -> int:
    if denominator == 0:
        return 0
    return round(numerator / denominator * 100)


def _suggestions(
    materials: list[SourceMaterial],
    reviewed_memories: list[MemoryCard],
    active_memories: list[MemoryCard],
) -> list[str]:
    present_types = _material_types(materials)
    suggestions: list[str] = []
    missing_types = [
        label
        for material_type, label in [
            ("text", "聊天记录或文字故事"),
            ("image", "共同经历照片"),
            ("audio", "TA 的清晰语音"),
            ("video", "家庭视频或访谈视频"),
        ]
        if material_type not in present_types
    ]
    if missing_types:
        suggestions.append("继续上传：" + "、".join(missing_types))
    if active_memories and not reviewed_memories:
        suggestions.append("确认或修正待审核记忆卡片")
    if not any(memory.category == "expression_style" for memory in reviewed_memories):
        suggestions.append("确认包含口头禅、称呼或说话节奏的表达习惯记忆")
    suggestions.append("后续补充音色和头像/半身数字人资料可继续提升可信度")
    return suggestions


def _material_types(materials: list[SourceMaterial]) -> set[str]:
    return {_normalize_material_type(material.file_type) for material in materials}


def _normalize_material_type(file_type: str) -> str:
    if file_type == "manual":
        return "text"
    return file_type


def _trust_level(score: int) -> str:
    if score <= 30:
        return "initial"
    if score <= 60:
        return "usable"
    if score <= 80:
        return "trusted"
    return "high_trust"


def _source_memory_ids(profile: PersonaProfile) -> dict[str, list[str]]:
    if isinstance(profile.source_memory_ids, dict):
        return {
            str(key): [str(memory_id) for memory_id in value]
            for key, value in profile.source_memory_ids.items()
            if key in PROFILE_DIMENSION_FIELDS and isinstance(value, list)
        }
    return {}


def _manual_override_fields(profile: PersonaProfile) -> set[str]:
    if not isinstance(profile.source_memory_ids, dict):
        return set()
    metadata = profile.source_memory_ids.get(MANUAL_OVERRIDE_KEY)
    if not isinstance(metadata, dict):
        return set()
    fields = metadata.get("fields")
    if not isinstance(fields, list):
        return set()
    return {field for field in fields if field in MANUAL_OVERRIDE_FIELDS}


def _with_manual_override_metadata(
    source_memory_ids: dict[str, list[str]],
    manual_fields: set[str],
) -> dict[str, object]:
    metadata: dict[str, object] = {
        field: list(memory_ids)
        for field, memory_ids in source_memory_ids.items()
        if field in PROFILE_DIMENSION_FIELDS
    }
    if manual_fields:
        metadata[MANUAL_OVERRIDE_KEY] = {"fields": sorted(manual_fields)}
    return metadata


def _build_profile_summary(persona: Persona, entries: list[dict]) -> str:
    if not entries:
        return f"{persona.name}的档案还需要确认或修正记忆补充。"
    contents = "；".join(entry["content"] for entry in entries[:3])
    return f"{persona.name}的档案摘要：{contents}。"


def _memory_priority(memory: MemoryCard) -> tuple[int, int, str]:
    status_priority = 0 if memory.status == "corrected" else 1
    return (status_priority, -memory.confidence_score, memory.id)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
