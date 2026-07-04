from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.ai_job import AIJob
from app.models.memory_card import MemoryCard
from app.models.parsed_chunk import ParsedChunk
from app.models.persona import Persona
from app.models.source_material import SourceMaterial
from app.providers.gateway import ProviderGateway
from app.services.audit import snapshot_entity, write_audit_event
from app.services.material_extractors import ExtractedText, extract_text_from_material_path
from app.services.profile import generate_memory_document_trust


MEMORY_MODULE_CATEGORIES = (
    "basic_fact",
    "relationship",
    "preference",
    "habit",
    "expression_style",
    "shared_event",
)
MEMORY_MODULE_CATEGORY_SET = set(MEMORY_MODULE_CATEGORIES)


@dataclass(frozen=True)
class MemoryExtractionResult:
    cards: list[MemoryCard]
    structured_memory_json: dict[str, Any]
    provider_type: str
    provider_name: str


def run_parse_job(db: Session, material: SourceMaterial, job: AIJob) -> list[MemoryCard]:
    if (
        job.status == "canceled"
        or job.deleted_at is not None
        or material.deleted_at is not None
    ):
        return []
    job.status = "running"
    job.started_at = _utcnow()
    job.error_message = None
    material.parse_status = "running"
    db.add_all([material, job])
    db.flush()

    try:
        parsed_payload = run_gateway_for_material(material)
        chunk = create_parsed_chunk(db, material, parsed_payload)
        memory_extraction = create_memory_cards(db, material, chunk, parsed_payload)
        memories = memory_extraction.cards
        material.parse_status = "succeeded"
        db.add(material)
        db.flush()
        memory_document_output: dict[str, Any] = {}
        memory_document_provider: dict[str, str] = {}
        memory_document_warning: dict[str, str] = {}
        persona = db.get(Persona, material.persona_id)
        if persona is not None:
            try:
                (
                    _report,
                    _input_json,
                    memory_document_output,
                    document_provider_type,
                    document_provider_name,
                ) = generate_memory_document_trust(db, persona, runner=_run_gateway)
                memory_document_provider = {
                    "memory_document_provider_type": document_provider_type,
                    "memory_document_provider_name": document_provider_name,
                }
            except Exception as exc:
                memory_document_warning = {
                    "memory_document_error": str(exc),
                    "memory_document_warning": "结构化记忆文档生成失败，记忆卡片已保留待审核。",
                }
        job.status = "succeeded"
        job.provider_type = parsed_payload.get("provider_type", "local")
        job.provider_name = parsed_payload["provider_name"]
        job.output_json = {
            "parsed_chunk_id": chunk.id,
            "memory_card_ids": [memory.id for memory in memories],
            "structured_memory_json": memory_extraction.structured_memory_json,
            "memory_extraction_provider_type": memory_extraction.provider_type,
            "memory_extraction_provider_name": memory_extraction.provider_name,
            "provider_names": parsed_payload.get("provider_names"),
            **memory_document_output,
            **memory_document_provider,
            **memory_document_warning,
        }
        job.finished_at = _utcnow()
        db.add_all([material, job])
        db.flush()
        return memories
    except Exception as exc:
        material.parse_status = "failed"
        job.status = "failed"
        job.error_message = str(exc)
        job.finished_at = _utcnow()
        db.add_all([material, job])
        db.flush()
        return []


def run_gateway_for_material(material: SourceMaterial) -> dict[str, Any]:
    payload = _base_payload(material)
    if material.file_type in {"manual", "text"}:
        extracted = _material_text(material)
        payload["text"] = extracted.text
        payload["text_extraction"] = extracted.metadata
        result = _run_gateway("text_parser", payload)
        chunk = result["output"]["chunks"][0]
        return {
            "provider_name": result["provider_name"],
            "provider_type": result.get("provider_type", "local"),
            "chunk_type": material.file_type,
            "content": chunk["content"],
            "summary": chunk["summary"],
            "source_location": chunk.get("source_location") or _source_location(material),
            "metadata": {
                "text_extraction": extracted.metadata,
                "text_parser": result["output"],
                "provider_type": result.get("provider_type", "local"),
            },
        }

    if material.file_type == "image":
        ocr_result = _run_gateway("ocr", payload)
        image_result = _run_gateway(
            "image_understanding",
            {**payload, "ocr_text": ocr_result["output"]["ocr_text"]},
        )
        output = image_result["output"]
        content = "。".join(
            [
                output["caption"],
                ocr_result["output"]["ocr_text"],
                output["memory_candidate_text"],
            ]
        )
        return {
            "provider_name": image_result["provider_name"],
            "provider_type": image_result.get("provider_type", "local"),
            "provider_names": {
                "ocr": ocr_result["provider_name"],
                "image_understanding": image_result["provider_name"],
            },
            "chunk_type": "image",
            "content": content,
            "summary": output["caption"],
            "source_location": output["source_location"],
            "metadata": {
                "ocr": ocr_result["output"],
                "image_understanding": image_result["output"],
                "provider_type": image_result.get("provider_type", "local"),
            },
        }

    if material.file_type == "audio":
        result = _run_gateway("asr", payload)
        output = result["output"]
        return {
            "provider_name": result["provider_name"],
            "provider_type": result.get("provider_type", "local"),
            "chunk_type": "audio",
            "content": output["transcript"],
            "summary": output["transcript"][:80],
            "source_location": output["source_location"],
            "metadata": {"asr": output, "provider_type": result.get("provider_type", "local")},
            "start_time_seconds": 0.0,
            "end_time_seconds": 5.0,
        }

    if material.file_type == "video":
        result = _run_gateway("video_understanding", payload)
        output = result["output"]
        content = "。".join(
            [output["transcript"], output["scene_summary"], output["memory_candidate_text"]]
        )
        return {
            "provider_name": result["provider_name"],
            "provider_type": result.get("provider_type", "local"),
            "chunk_type": "video",
            "content": content,
            "summary": output["scene_summary"],
            "source_location": output["source_location"],
            "metadata": {
                "video_understanding": output,
                "provider_type": result.get("provider_type", "local"),
            },
            "start_time_seconds": 0.0,
            "end_time_seconds": 10.0,
        }

    raise ValueError(f"Unsupported material file type: {material.file_type}")


def create_parsed_chunk(
    db: Session,
    material: SourceMaterial,
    parsed_payload: dict[str, Any],
) -> ParsedChunk:
    chunk = ParsedChunk(
        persona_id=material.persona_id,
        source_material_id=material.id,
        chunk_type=parsed_payload["chunk_type"],
        content=parsed_payload["content"],
        summary=parsed_payload.get("summary"),
        source_location=parsed_payload.get("source_location"),
        start_time_seconds=parsed_payload.get("start_time_seconds"),
        end_time_seconds=parsed_payload.get("end_time_seconds"),
        metadata_json=parsed_payload.get("metadata"),
    )
    db.add(chunk)
    db.flush()
    return chunk


def create_memory_cards(
    db: Session,
    material: SourceMaterial,
    chunk: ParsedChunk,
    parsed_payload: dict[str, Any],
) -> MemoryExtractionResult:
    result = _run_gateway(
        "memory_extraction",
        _memory_extraction_payload(db, material, chunk),
    )
    structured_memory_json = _normalize_structured_memory_json(
        result.get("output"),
        source_material_id=material.id,
    )
    cards: list[MemoryCard] = []
    for module in MEMORY_MODULE_CATEGORIES:
        for candidate in structured_memory_json["modules"][module]:
            card = MemoryCard(
                persona_id=material.persona_id,
                title=candidate["title"],
                content=candidate["content"],
                category=candidate["category"],
                confidence_level=candidate["confidence_level"],
                confidence_score=candidate["confidence_score"],
                source_material_id=material.id,
                parsed_chunk_id=chunk.id,
                source_type=material.file_type,
                source_quote=candidate["source_quote"],
                source_location=candidate["source_location"] or chunk.source_location,
                evidence_json={
                    "provider_name": result["provider_name"],
                    "provider_type": result.get("provider_type", "local"),
                    "parsed_summary": parsed_payload.get("summary"),
                    "parsed_provider_name": parsed_payload.get("provider_name"),
                    "structured_memory_source": "memory_extraction",
                    "memory_module": module,
                    "structured_memory_warnings": structured_memory_json.get("warnings") or [],
                },
                status="pending_review",
                is_important=False,
                created_by="system",
            )
            db.add(card)
            cards.append(card)
    db.flush()
    for card in cards:
        write_audit_event(
            db,
            user_id=material.user_id,
            persona_id=material.persona_id,
            target_type="memory",
            target_id=card.id,
            event_type="memory.created",
            action="资料解析生成记忆卡片",
            after_snapshot=snapshot_entity(card),
            metadata_json={
                "source_material_id": material.id,
                "parsed_chunk_id": chunk.id,
            },
        )
    return MemoryExtractionResult(
        cards=cards,
        structured_memory_json=structured_memory_json,
        provider_type=result.get("provider_type", "local"),
        provider_name=result["provider_name"],
    )


def _memory_extraction_payload(
    db: Session,
    material: SourceMaterial,
    chunk: ParsedChunk,
) -> dict[str, Any]:
    persona = db.get(Persona, material.persona_id)
    persona_card: dict[str, Any] = {}
    if persona is not None:
        persona_card = {
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
        }
    return {
        "source_material_id": material.id,
        "source_type": material.file_type,
        "content": chunk.content,
        "source_location": chunk.source_location,
        "persona_card": persona_card,
        "source_material": {
            "id": material.id,
            "file_type": material.file_type,
            "file_name": material.file_name,
            "mime_type": material.mime_type,
            "file_size": material.file_size,
            "importance": material.importance,
            "user_description": material.user_description,
            "location_hint": material.location_hint,
        },
        "parsed_chunk": {
            "id": chunk.id,
            "chunk_type": chunk.chunk_type,
            "content": chunk.content,
            "summary": chunk.summary,
            "source_location": chunk.source_location,
            "metadata_json": chunk.metadata_json,
        },
        "required_modules": list(MEMORY_MODULE_CATEGORIES),
    }


def _normalize_structured_memory_json(
    output: object,
    *,
    source_material_id: str,
) -> dict[str, Any]:
    if not isinstance(output, dict) or not isinstance(output.get("structured_memory_json"), dict):
        raise ValueError("memory_extraction output must include structured_memory_json")

    data = output["structured_memory_json"]
    raw_modules = data.get("modules")
    if not isinstance(raw_modules, dict):
        raise ValueError("structured_memory_json.modules must be an object")

    unknown_modules = sorted(set(raw_modules) - MEMORY_MODULE_CATEGORY_SET)
    if unknown_modules:
        raise ValueError(
            "structured_memory_json.modules contains unknown module: "
            + ", ".join(unknown_modules)
        )

    warnings = [str(item) for item in data.get("warnings") or [] if str(item).strip()]
    modules: dict[str, list[dict[str, Any]]] = {
        category: [] for category in MEMORY_MODULE_CATEGORIES
    }
    for category in MEMORY_MODULE_CATEGORIES:
        raw_items = raw_modules.get(category) or []
        if not isinstance(raw_items, list):
            raise ValueError(f"structured_memory_json.modules.{category} must be a list")
        for index, raw_item in enumerate(raw_items, start=1):
            normalized = _normalize_module_memory(raw_item, category)
            if normalized is None:
                warnings.append(f"跳过 {category} 第 {index} 条：缺少必填字段或来源证据")
                continue
            modules[category].append(normalized)

    unclassified = data.get("unclassified")
    if not isinstance(unclassified, list):
        unclassified = []

    return {
        "source_material_id": str(data.get("source_material_id") or source_material_id),
        "modules": modules,
        "unclassified": unclassified,
        "warnings": warnings,
    }


def _normalize_module_memory(raw_item: object, category: str) -> dict[str, Any] | None:
    if not isinstance(raw_item, dict):
        return None
    if raw_item.get("category") != category:
        return None
    title = _clean_field(raw_item.get("title"))
    content = _clean_field(raw_item.get("content"))
    source_quote = _clean_field(raw_item.get("source_quote"))
    source_location = _clean_field(raw_item.get("source_location"))
    if not all([title, content, source_quote, source_location]):
        return None
    confidence_score = _bounded_confidence(raw_item.get("confidence_score"))
    return {
        "title": title,
        "content": content,
        "category": category,
        "confidence_level": _confidence_level(raw_item.get("confidence_level"), confidence_score),
        "confidence_score": confidence_score,
        "source_quote": source_quote,
        "source_location": source_location,
    }


def _clean_field(value: object) -> str:
    return " ".join(str(value or "").split())


def _bounded_confidence(value: object) -> int:
    try:
        score = round(float(value))
    except (TypeError, ValueError):
        score = 50
    return max(0, min(100, score))


def _confidence_level(value: object, score: int) -> str:
    level = str(value or "").strip()
    if level in {"high", "medium", "low"}:
        return level
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def _run_gateway(capability: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(ProviderGateway().run(capability, payload))

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def run_in_thread() -> None:
        try:
            result["value"] = asyncio.run(ProviderGateway().run(capability, payload))
        except BaseException as exc:  # pragma: no cover - re-raised in caller
            error["value"] = exc

    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()
    if error:
        raise error["value"]
    return result["value"]


def _base_payload(material: SourceMaterial) -> dict[str, Any]:
    return {
        "source_material_id": material.id,
        "persona_id": material.persona_id,
        "file_type": material.file_type,
        "file_name": material.file_name,
        "mime_type": material.mime_type,
        "storage_url": material.storage_url,
        "manual_text": material.manual_text,
        "user_description": material.user_description,
        "location_hint": material.location_hint,
        "importance": material.importance,
        "source_location": _source_location(material),
    }


def _material_text(material: SourceMaterial) -> ExtractedText:
    if material.manual_text:
        return ExtractedText(
            text=material.manual_text,
            metadata={
                "extractor": "manual",
                "source_location": "manual:body",
                "has_text": bool(material.manual_text.strip()),
            },
        )
    if material.storage_url:
        path = Path(material.storage_url)
        if path.exists():
            return extract_text_from_material_path(
                path,
                file_name=material.file_name,
                mime_type=material.mime_type,
            )
    parts = [material.file_name or "资料", material.user_description or ""]
    text = "。".join(part for part in parts if part)
    return ExtractedText(
        text=text,
        metadata={
            "extractor": "fallback_description",
            "source_location": _source_location(material),
            "has_text": bool(text),
        },
    )


def _source_location(material: SourceMaterial) -> str:
    if material.file_type == "manual":
        return "manual:body"
    if material.file_name:
        return f"{material.file_type}:{material.file_name}"
    return f"{material.file_type}:{material.id}"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
