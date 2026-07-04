from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ai_job import AIJob
from app.models.memory_card import MemoryCard
from app.models.parsed_chunk import ParsedChunk
from app.models.persona import Persona
from app.models.persona_profile import PersonaProfile
from app.models.source_material import SourceMaterial
from app.providers.gateway import ProviderGateway
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
MANUAL_OVERRIDE_FIELDS = PROFILE_DIMENSION_FIELDS
MEMORY_DOCUMENT_COMPONENT_NAME = "memory_document_generation"
MEMORY_DOCUMENT_TRUST_LEVELS = {"initial", "usable", "trusted", "high_trust"}
STRUCTURED_MEMORY_SECTIONS = (
    "资料来源",
    "基础信息",
    "人物关系",
    "兴趣偏好",
    "生活习惯",
    "表达习惯",
    "共同经历",
    "待用户确认",
)
MEMORY_DOCUMENT_MODULES = (
    "basic_fact",
    "relationship",
    "preference",
    "habit",
    "expression_style",
    "shared_event",
)
MEMORY_DOCUMENT_MODULE_SET = set(MEMORY_DOCUMENT_MODULES)
MEMORY_DOCUMENT_SECTION_BY_MODULE = {
    "basic_fact": "基础信息",
    "relationship": "人物关系",
    "preference": "兴趣偏好",
    "habit": "生活习惯",
    "expression_style": "表达习惯",
    "shared_event": "共同经历",
}


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
    try:
        with db.begin_nested():
            db.add(profile)
            db.flush()
        return profile
    except IntegrityError:
        profile = db.scalar(
            select(PersonaProfile).where(PersonaProfile.persona_id == persona.id)
        )
        if profile is not None:
            return profile
        raise


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
    db.add(profile)
    db.flush()
    return profile


def calculate_trust_report(db: Session, persona: Persona) -> TrustReport:
    db.flush()
    trust_score = _bounded_score(persona.trust_score, 0)
    jobs = db.scalars(
        select(AIJob)
        .where(
            AIJob.persona_id == persona.id,
            AIJob.status == "succeeded",
            AIJob.deleted_at.is_(None),
        )
        .order_by(AIJob.created_at.desc(), AIJob.id.desc())
    ).all()
    for job in jobs:
        if isinstance(job.output_json, dict) and _is_memory_document_output(job.output_json):
            return _memory_document_report_from_output(
                {
                    **job.output_json,
                    "trust_score": trust_score,
                    "trust_level": _trust_level(trust_score),
                }
            )

    return _memory_document_report_from_output(
        {
            "trust_score": trust_score,
            "trust_level": _trust_level(trust_score),
            "trust_rationale": "尚未生成结构化记忆文档，当前仅返回人物已存可信度。",
            "suggestions": ["继续上传资料，生成结构化记忆文档"],
        }
    )


def refresh_profile_and_trust(db: Session, persona: Persona) -> TrustReport:
    build_profile_from_memories(db, persona, preserve_manual_overrides=True)
    report = calculate_trust_report(db, persona)
    return report


def generate_memory_document_trust(
    db: Session,
    persona: Persona,
    *,
    runner=None,
) -> tuple[TrustReport, dict[str, Any], dict[str, Any], str, str]:
    profile = get_or_create_profile(db, persona)
    payload = build_memory_document_payload(db, persona, profile)
    run = runner or _run_provider
    provider_type = "local"
    provider_name = "deterministic_memory_document_renderer"
    try:
        result = run("memory_document_generation", payload)
        output = _normalize_memory_document_output(
            result.get("output"),
            persona.trust_score,
            payload=payload,
        )
        output.setdefault("memory_document_generation_status", "succeeded")
        provider_type = str(result.get("provider_type") or "local")
        provider_name = str(result.get("provider_name") or "mock")
    except Exception as exc:
        output = _normalize_memory_document_output(
            {},
            persona.trust_score,
            payload=payload,
            provider_error=str(exc),
        )
    report = _memory_document_report_from_output(output)
    profile.profile_summary = output["profile_summary"]
    persona.trust_score = report.trust_score
    db.add_all([persona, profile])
    db.flush()
    return (
        report,
        payload,
        output,
        provider_type,
        provider_name,
    )


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
    *,
    provider_type: str = "local",
    provider_name: str | None = "deterministic_profile_service",
    input_json: dict[str, Any] | None = None,
    output_json_extra: dict[str, Any] | None = None,
    status: str = "succeeded",
    error_message: str | None = None,
) -> AIJob:
    now = _utcnow()
    output_json: dict[str, Any] = report.model_dump()
    if output_json_extra:
        output_json.update(output_json_extra)
    job = AIJob(
        user_id=persona.user_id,
        persona_id=persona.id,
        job_type=job_type,
        provider_type=provider_type,
        provider_name=provider_name,
        status=status,
        input_json=input_json or {"persona_id": persona.id},
        output_json=output_json,
        error_message=error_message,
        started_at=now,
        finished_at=now,
    )
    db.add(job)
    db.flush()
    return job


def profile_response(
    profile: PersonaProfile,
    report: TrustReport,
    persona: Persona,
) -> PersonaProfileRead:
    return PersonaProfileRead(
        id=profile.id,
        persona_id=profile.persona_id,
        basic_facts=_basic_facts_with_persona_age(profile, persona),
        relationships=profile.relationships or [],
        preferences=profile.preferences or [],
        habits=profile.habits or [],
        expression_style=profile.expression_style or [],
        shared_events=profile.shared_events or [],
        values_json=profile.values_json or [],
        emotional_patterns=profile.emotional_patterns or [],
        profile_summary=profile.profile_summary,
        source_memory_ids=_source_memory_ids(profile),
        persona_engine_json=profile.persona_engine_json,
        persona_engine_generated_at=profile.persona_engine_generated_at,
        trust_score=report.trust_score,
        trust_level=report.trust_level,
        components=report.components,
        suggestions=report.suggestions,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _basic_facts_with_persona_age(
    profile: PersonaProfile,
    persona: Persona,
) -> list[object] | dict:
    basic_facts = profile.basic_facts or []
    if "basic_facts" in _manual_override_fields(profile) or not isinstance(
        basic_facts, list
    ):
        return basic_facts
    if persona.age is None:
        return basic_facts

    age_entry = {
        "field": "age",
        "value": persona.age,
        "content": f"年龄/享年：{persona.age}",
        "source": "persona_card",
    }
    return [age_entry, *[fact for fact in basic_facts if not _is_persona_age_fact(fact)]]


def regenerate_with_persona_engine(
    db: Session,
    persona: Persona,
) -> tuple[PersonaProfile, TrustReport, dict[str, Any]]:
    profile = build_profile_from_memories(db, persona)
    report = calculate_trust_report(db, persona)
    payload = build_persona_engine_payload(db, persona, profile)
    try:
        result = _run_provider("persona_profile_analysis", payload)
        output = result.get("output")
        if not isinstance(output, dict):
            raise ValueError("Persona Engine output is not a JSON object")
        _apply_persona_engine_output(profile, output)
        job_extra = {
            "persona_engine_status": "succeeded",
            "persona_engine_json": output,
        }
        provider_type = str(result.get("provider_type") or "local")
        provider_name = str(result.get("provider_name") or "mock")
    except Exception as exc:  # pragma: no cover - exact provider failures vary.
        fallback = {
            "persona_engine_status": "fallback",
            "persona_engine_error": str(exc),
        }
        profile.persona_engine_json = {
            "persona_version": "deterministic_fallback",
            "fallback_reason": str(exc),
        }
        profile.persona_engine_generated_at = _utcnow()
        job_extra = fallback
        provider_type = "local"
        provider_name = "deterministic_profile_service"
    db.add_all([persona, profile])
    db.flush()
    record_profile_job(
        db,
        persona,
        "update_profile",
        report,
        provider_type=provider_type,
        provider_name=provider_name,
        input_json=payload,
        output_json_extra=job_extra,
    )
    return profile, report, job_extra


def build_memory_document_payload(
    db: Session,
    persona: Persona,
    profile: PersonaProfile,
) -> dict[str, Any]:
    materials = db.scalars(
        select(SourceMaterial)
        .where(
            SourceMaterial.persona_id == persona.id,
            SourceMaterial.deleted_at.is_(None),
            SourceMaterial.parse_status == "succeeded",
        )
        .order_by(SourceMaterial.created_at.desc(), SourceMaterial.id.desc())
    ).all()
    chunks = db.scalars(
        select(ParsedChunk)
        .where(ParsedChunk.persona_id == persona.id, ParsedChunk.deleted_at.is_(None))
        .order_by(ParsedChunk.created_at.desc(), ParsedChunk.id.desc())
        .limit(120)
    ).all()
    memories = db.scalars(
        select(MemoryCard)
        .where(
            MemoryCard.persona_id == persona.id,
            MemoryCard.deleted_at.is_(None),
            MemoryCard.status.not_in(INACTIVE_STATUSES),
        )
        .order_by(
            MemoryCard.is_important.desc(),
            MemoryCard.updated_at.desc(),
            MemoryCard.id.desc(),
        )
        .limit(160)
    ).all()
    return {
        "persona_card": {
            "id": persona.id,
            "name": persona.name,
            "persona_type": persona.persona_type,
            "status": persona.status,
            "relationship_to_user": persona.relationship_to_user,
            "user_nickname_by_persona": persona.user_nickname_by_persona,
            "age": persona.age,
            "gender": persona.gender,
            "language": persona.language,
            "short_bio": persona.short_bio,
            "speaking_style": persona.speaking_style,
            "emotional_style": persona.emotional_style,
            "forbidden_expressions": persona.forbidden_expressions,
        },
        "parsed_chunks": [
            {
                "id": chunk.id,
                "source_material_id": chunk.source_material_id,
                "chunk_type": chunk.chunk_type,
                "content": _clip(chunk.content, 2000),
                "summary": chunk.summary,
                "source_location": chunk.source_location,
                "metadata_json": chunk.metadata_json,
            }
            for chunk in chunks
        ],
        "active_memory_cards": [
            {
                "id": memory.id,
                "title": memory.title,
                "content": memory.user_correction or memory.content,
                "category": memory.category,
                "confidence_level": memory.confidence_level,
                "confidence_score": memory.confidence_score,
                "status": memory.status,
                "is_important": memory.is_important,
                "source_quote": memory.source_quote,
                "source_location": memory.source_location,
            }
            for memory in memories
        ],
        "source_metadata": [
            {
                "id": material.id,
                "file_name": material.file_name,
                "file_type": material.file_type,
                "importance": material.importance,
                "parse_status": material.parse_status,
                "user_description": material.user_description,
                "manual_text_excerpt": _clip(material.manual_text, 1000),
            }
            for material in materials
        ],
        "current_profile": {
            "profile_summary": profile.profile_summary,
            "source_memory_ids": profile.source_memory_ids,
            **{field: getattr(profile, field) for field in PROFILE_DIMENSION_FIELDS},
        },
    }


def build_persona_engine_payload(
    db: Session,
    persona: Persona,
    profile: PersonaProfile,
) -> dict[str, Any]:
    materials = db.scalars(
        select(SourceMaterial)
        .where(SourceMaterial.persona_id == persona.id, SourceMaterial.deleted_at.is_(None))
        .order_by(SourceMaterial.created_at.desc(), SourceMaterial.id.desc())
    ).all()
    chunks = db.scalars(
        select(ParsedChunk)
        .where(ParsedChunk.persona_id == persona.id, ParsedChunk.deleted_at.is_(None))
        .order_by(ParsedChunk.created_at.desc(), ParsedChunk.id.desc())
        .limit(80)
    ).all()
    memories = db.scalars(
        select(MemoryCard)
        .where(
            MemoryCard.persona_id == persona.id,
            MemoryCard.deleted_at.is_(None),
            MemoryCard.status.in_(REVIEWED_STATUSES),
        )
        .order_by(
            MemoryCard.is_important.desc(),
            MemoryCard.updated_at.desc(),
            MemoryCard.id.desc(),
        )
        .limit(120)
    ).all()
    return {
        "persona_card": {
            "id": persona.id,
            "name": persona.name,
            "persona_type": persona.persona_type,
            "status": persona.status,
            "relationship_to_user": persona.relationship_to_user,
            "user_nickname_by_persona": persona.user_nickname_by_persona,
            "age": persona.age,
            "gender": persona.gender,
            "language": persona.language,
            "short_bio": persona.short_bio,
            "speaking_style": persona.speaking_style,
            "emotional_style": persona.emotional_style,
            "forbidden_expressions": persona.forbidden_expressions,
        },
        "parsed_chunks": [
            {
                "id": chunk.id,
                "source_material_id": chunk.source_material_id,
                "chunk_type": chunk.chunk_type,
                "content": _clip(chunk.content, 2000),
                "summary": chunk.summary,
                "source_location": chunk.source_location,
                "metadata_json": chunk.metadata_json,
            }
            for chunk in chunks
        ],
        "active_memory_cards": [
            {
                "id": memory.id,
                "title": memory.title,
                "content": memory.user_correction or memory.content,
                "category": memory.category,
                "confidence_level": memory.confidence_level,
                "confidence_score": memory.confidence_score,
                "status": memory.status,
                "is_important": memory.is_important,
                "source_quote": memory.source_quote,
                "source_location": memory.source_location,
            }
            for memory in memories
        ],
        "source_metadata": [
            {
                "id": material.id,
                "file_name": material.file_name,
                "file_type": material.file_type,
                "importance": material.importance,
                "parse_status": material.parse_status,
                "user_description": material.user_description,
                "manual_text_excerpt": _clip(material.manual_text, 1000),
            }
            for material in materials
        ],
        "current_profile": {
            "profile_summary": profile.profile_summary,
            "source_memory_ids": profile.source_memory_ids,
            **{field: getattr(profile, field) for field in PROFILE_DIMENSION_FIELDS},
        },
    }


def _apply_persona_engine_output(profile: PersonaProfile, output: dict[str, Any]) -> None:
    output.setdefault("persona_version", "persona_engine_v2")
    profile.persona_engine_json = output
    profile.persona_engine_generated_at = _utcnow()
    if not profile.relationships and isinstance(output.get("relationships"), list):
        profile.relationships = output["relationships"]
    if not profile.expression_style and isinstance(output.get("speech_style"), dict):
        profile.expression_style = [output["speech_style"]]
    if not profile.habits and isinstance(output.get("habits"), list):
        profile.habits = output["habits"]
    if not profile.emotional_patterns and isinstance(output.get("emotional_style"), dict):
        profile.emotional_patterns = [output["emotional_style"]]
    if not profile.values_json:
        values = []
        for key in ("worldview", "decision_style"):
            value = output.get(key)
            if isinstance(value, dict):
                values.append({"field": key, **value})
        if values:
            profile.values_json = values


def _run_provider(capability: str, payload: dict[str, Any]) -> dict[str, Any]:
    return asyncio.run(ProviderGateway().run(capability, payload))


def _clip(value: str | None, max_chars: int) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}..."


def _is_persona_age_fact(value: object) -> bool:
    return (
        isinstance(value, dict)
        and value.get("field") == "age"
        and value.get("source") == "persona_card"
    )


def _is_memory_document_output(output: dict[str, Any]) -> bool:
    return "structured_memory_md" in output and "trust_score" in output


def _normalize_memory_document_output(
    output: object,
    fallback_score: int | None = 0,
    *,
    payload: dict[str, Any] | None = None,
    provider_error: str | None = None,
) -> dict[str, Any]:
    data = output if isinstance(output, dict) else {}
    document_json = (
        _structured_memory_document_json_from_payload(payload)
        if payload is not None
        else _normalize_structured_memory_document_json(
            data.get("structured_memory_document_json"),
            payload=payload,
        )
    )
    score_fallback = (
        _memory_document_payload_score(payload)
        if payload is not None
        else fallback_score or 0
    )
    trust_score = _bounded_score(data.get("trust_score"), score_fallback)
    trust_level = str(data.get("trust_level") or _trust_level(trust_score))
    if trust_level not in MEMORY_DOCUMENT_TRUST_LEVELS:
        trust_level = _trust_level(trust_score)
    suggestions = data.get("suggestions")
    if not isinstance(suggestions, list) or not suggestions:
        suggestions = ["继续上传资料，补充更多可追溯的记忆证据"]
    structured_memory_md = (
        ""
        if payload is not None
        else str(data.get("structured_memory_md") or "").strip()
    )
    if not structured_memory_md:
        structured_memory_md = _render_structured_memory_md(document_json, payload=payload)
    profile_summary = str(data.get("profile_summary") or "").strip()
    if not profile_summary:
        profile_summary = _profile_summary_from_document(document_json, payload)
    normalized = {
        **data,
        "profile_summary": profile_summary,
        "structured_memory_document_json": document_json,
        "structured_memory_md": structured_memory_md,
        "trust_score": trust_score,
        "trust_level": trust_level,
        "trust_rationale": str(
            data.get("trust_rationale") or "由结构化记忆文档生成链路计算。"
        ),
        "suggestions": [str(item) for item in suggestions],
    }
    if provider_error:
        normalized["memory_document_generation_status"] = "fallback"
        normalized["memory_document_provider_error"] = provider_error
    return normalized


def _normalize_structured_memory_document_json(
    value: object,
    *,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("modules"), dict):
        return _structured_memory_document_json_from_payload(payload)

    raw_modules = value["modules"]
    modules: dict[str, list[dict[str, Any]]] = {
        module: [] for module in MEMORY_DOCUMENT_MODULES
    }
    warnings = [str(item) for item in value.get("warnings") or [] if str(item).strip()]
    unclassified = value.get("unclassified")
    if not isinstance(unclassified, list):
        unclassified = []

    for raw_module, raw_items in raw_modules.items():
        module = str(raw_module)
        if module not in MEMORY_DOCUMENT_MODULE_SET:
            warnings.append(f"跳过未知模块：{raw_module}")
            if isinstance(raw_items, list):
                unclassified.extend(raw_items)
            continue
        if not isinstance(raw_items, list):
            warnings.append(f"跳过非数组模块：{raw_module}")
            continue
        for raw_item in raw_items:
            normalized = _normalize_memory_document_item(raw_item, module)
            if normalized is None:
                warnings.append(f"跳过字段不完整的 {module} 记忆")
                continue
            modules[module].append(normalized)

    sources = value.get("sources")
    normalized_sources = [
        _normalize_memory_document_source(source)
        for source in sources
        if isinstance(source, dict)
    ] if isinstance(sources, list) else []
    if not normalized_sources and payload is not None:
        normalized_sources = _memory_document_sources_from_payload(payload)
    return {
        "sources": normalized_sources,
        "modules": modules,
        "unclassified": unclassified,
        "warnings": warnings,
    }


def _structured_memory_document_json_from_payload(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    modules: dict[str, list[dict[str, Any]]] = {
        module: [] for module in MEMORY_DOCUMENT_MODULES
    }
    if payload is None:
        return {
            "sources": [],
            "modules": modules,
            "unclassified": [],
            "warnings": [],
        }

    for memory in payload.get("active_memory_cards") or []:
        if not isinstance(memory, dict):
            continue
        category = str(memory.get("category") or "")
        module = category if category in MEMORY_DOCUMENT_MODULE_SET else "shared_event"
        item = _normalize_memory_document_item(memory, module)
        if item is not None:
            modules[module].append(item)

    return {
        "sources": _memory_document_sources_from_payload(payload),
        "modules": modules,
        "unclassified": [],
        "warnings": [],
    }


def _memory_document_sources_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for material in payload.get("source_metadata") or []:
        if not isinstance(material, dict):
            continue
        sources.append(_normalize_memory_document_source(material))
    return sources


def _normalize_memory_document_source(source: dict[str, Any]) -> dict[str, Any]:
    label = (
        source.get("label")
        or source.get("file_name")
        or source.get("manual_text_excerpt")
        or source.get("id")
        or "未命名资料"
    )
    return {
        "id": str(source.get("id") or ""),
        "file_type": str(source.get("file_type") or "material"),
        "label": _clip(str(label), 80) or "未命名资料",
        "parse_status": source.get("parse_status"),
    }


def _normalize_memory_document_item(
    value: object,
    module: str,
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    title = _clip(str(value.get("title") or ""), 120)
    content = str(value.get("content") or "").strip()
    source_quote = str(value.get("source_quote") or content[:120]).strip()
    source_location = str(value.get("source_location") or "").strip()
    if not title or not content:
        return None
    confidence_score = _bounded_score(value.get("confidence_score"), 70)
    confidence_level = str(value.get("confidence_level") or "")
    if confidence_level not in {"high", "medium", "low"}:
        confidence_level = (
            "high" if confidence_score >= 80 else "medium" if confidence_score >= 50 else "low"
        )
    normalized = {
        "id": str(value.get("id") or ""),
        "title": title,
        "content": content,
        "category": module,
        "confidence_level": confidence_level,
        "confidence_score": confidence_score,
        "source_quote": source_quote,
        "source_location": source_location,
        "status": str(value.get("status") or "pending_review"),
        "is_important": bool(value.get("is_important")),
    }
    return normalized


def _render_structured_memory_md(
    document_json: dict[str, Any],
    *,
    payload: dict[str, Any] | None = None,
) -> str:
    section_lines = {section: [] for section in STRUCTURED_MEMORY_SECTIONS}
    for source in document_json.get("sources") or []:
        if not isinstance(source, dict):
            continue
        label = source.get("label") or source.get("id") or "未命名资料"
        section_lines["资料来源"].append(
            f"- {source.get('file_type') or 'material'}: {label}"
        )

    modules = document_json.get("modules") if isinstance(document_json.get("modules"), dict) else {}
    for module in MEMORY_DOCUMENT_MODULES:
        section = MEMORY_DOCUMENT_SECTION_BY_MODULE[module]
        for item in modules.get(module) or []:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            title = str(item.get("title") or "未命名记忆").strip()
            status = str(item.get("status") or "pending_review")
            source_location = str(item.get("source_location") or "").strip()
            importance = "[important] " if bool(item.get("is_important")) else ""
            suffix = f"（来源：{source_location}）" if source_location else ""
            line = f"- {importance}[{status}] {title}: {content}{suffix}"
            section_lines[section].append(line)
            if status not in REVIEWED_STATUSES:
                section_lines["待用户确认"].append(line)

    if not section_lines["资料来源"]:
        section_lines["资料来源"].append("- 暂无已解析资料")
    for section in STRUCTURED_MEMORY_SECTIONS:
        if not section_lines[section]:
            section_lines[section].append("- 暂无明确资料")
    return "\n\n".join(
        f"## {section}\n" + "\n".join(section_lines[section])
        for section in STRUCTURED_MEMORY_SECTIONS
    )


def _profile_summary_from_document(
    document_json: dict[str, Any],
    payload: dict[str, Any] | None,
) -> str:
    persona_card = payload.get("persona_card") if isinstance(payload, dict) else {}
    name = "TA"
    if isinstance(persona_card, dict) and persona_card.get("name"):
        name = str(persona_card["name"])

    items: list[dict[str, Any]] = []
    modules = document_json.get("modules") if isinstance(document_json.get("modules"), dict) else {}
    for module in MEMORY_DOCUMENT_MODULES:
        for item in modules.get(module) or []:
            if isinstance(item, dict) and item.get("content"):
                items.append(item)
    items.sort(
        key=lambda item: (
            0 if bool(item.get("is_important")) else 1,
            0 if item.get("status") in REVIEWED_STATUSES else 1,
            str(item.get("id") or item.get("title") or ""),
        )
    )
    contents = [str(item["content"]).strip() for item in items[:3] if str(item["content"]).strip()]
    if contents:
        return f"{name}的档案摘要：" + "；".join(contents) + "。"
    if isinstance(persona_card, dict) and persona_card.get("short_bio"):
        return str(persona_card["short_bio"])
    return "档案摘要将在新的资料解析后自动生成。"


def _memory_document_payload_score(payload: dict[str, Any] | None) -> int:
    if payload is None:
        return 0
    source_count = len([item for item in payload.get("source_metadata") or [] if isinstance(item, dict)])
    chunk_count = len([item for item in payload.get("parsed_chunks") or [] if isinstance(item, dict)])
    memories = [item for item in payload.get("active_memory_cards") or [] if isinstance(item, dict)]
    traceable_count = len(
        [
            item
            for item in memories
            if item.get("source_quote") and item.get("source_location")
        ]
    )
    reviewed_count = len(
        [item for item in memories if item.get("status") in REVIEWED_STATUSES]
    )
    if not memories:
        return 0
    score = 15
    score += min(source_count, 4) * 8
    score += min(chunk_count, 6) * 4
    score += round(traceable_count / len(memories) * 24)
    score += round(reviewed_count / len(memories) * 20)
    return max(0, min(100, score))


def _memory_document_report_from_output(output: dict[str, Any]) -> TrustReport:
    normalized = _normalize_memory_document_output(output)
    score = normalized["trust_score"]
    rationale = normalized["trust_rationale"]
    return TrustReport(
        trust_score=score,
        trust_level=normalized["trust_level"],
        components=[
            TrustComponent(
                name=MEMORY_DOCUMENT_COMPONENT_NAME,
                score=score,
                weight=1.0,
                weighted_score=float(score),
                evidence=rationale,
            )
        ],
        suggestions=normalized["suggestions"],
    )


def _bounded_score(value: object, fallback: int = 0) -> int:
    try:
        score = round(float(value))
    except (TypeError, ValueError):
        score = fallback
    return max(0, min(100, score))


def _empty_structured_memory_md() -> str:
    return "\n\n".join(f"## {section}\n- 暂无明确资料" for section in STRUCTURED_MEMORY_SECTIONS)


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
    importance_priority = 0 if memory.is_important else 1
    status_priority = 0 if memory.status == "corrected" else 1
    return (importance_priority, status_priority, -memory.confidence_score, memory.id)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
