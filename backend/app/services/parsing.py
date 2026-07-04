from __future__ import annotations

import asyncio
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.ai_job import AIJob
from app.models.memory_card import MemoryCard
from app.models.parsed_chunk import ParsedChunk
from app.models.source_material import SourceMaterial
from app.providers.gateway import ProviderGateway


def run_parse_job(db: Session, material: SourceMaterial, job: AIJob) -> list[MemoryCard]:
    job.status = "running"
    job.started_at = _utcnow()
    job.error_message = None
    material.parse_status = "running"
    db.add_all([material, job])
    db.flush()

    try:
        parsed_payload = run_gateway_for_material(material)
        chunk = create_parsed_chunk(db, material, parsed_payload)
        memories = create_memory_cards(db, material, chunk, parsed_payload)
        material.parse_status = "succeeded"
        job.status = "succeeded"
        job.provider_type = "mock"
        job.provider_name = parsed_payload["provider_name"]
        job.output_json = {
            "parsed_chunk_id": chunk.id,
            "memory_card_ids": [memory.id for memory in memories],
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
        payload["text"] = _material_text(material)
        result = _run_gateway("text_parser", payload)
        chunk = result["output"]["chunks"][0]
        return {
            "provider_name": result["provider_name"],
            "chunk_type": material.file_type,
            "content": chunk["content"],
            "summary": chunk["summary"],
            "source_location": _source_location(material),
            "metadata": {"text_parser": result["output"]},
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
            "chunk_type": "image",
            "content": content,
            "summary": output["caption"],
            "source_location": output["source_location"],
            "metadata": {
                "ocr": ocr_result["output"],
                "image_understanding": image_result["output"],
            },
        }

    if material.file_type == "audio":
        result = _run_gateway("asr", payload)
        output = result["output"]
        return {
            "provider_name": result["provider_name"],
            "chunk_type": "audio",
            "content": output["transcript"],
            "summary": output["transcript"][:80],
            "source_location": output["source_location"],
            "metadata": {"asr": output},
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
            "chunk_type": "video",
            "content": content,
            "summary": output["scene_summary"],
            "source_location": output["source_location"],
            "metadata": {"video_understanding": output},
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
) -> list[MemoryCard]:
    result = _run_gateway(
        "memory_extraction",
        {
            "source_material_id": material.id,
            "source_type": material.file_type,
            "content": chunk.content,
            "source_location": chunk.source_location,
        },
    )
    cards: list[MemoryCard] = []
    for candidate in result["output"]["memories"]:
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
                "parsed_summary": parsed_payload.get("summary"),
            },
            status="pending_review",
            created_by="system",
        )
        db.add(card)
        cards.append(card)
    db.flush()
    return cards


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
        "manual_text": material.manual_text,
        "user_description": material.user_description,
        "location_hint": material.location_hint,
        "importance": material.importance,
        "source_location": _source_location(material),
    }


def _material_text(material: SourceMaterial) -> str:
    if material.manual_text:
        return material.manual_text
    if material.storage_url:
        path = Path(material.storage_url)
        if path.exists():
            return path.read_text(encoding="utf-8", errors="ignore")
    parts = [material.file_name or "资料", material.user_description or ""]
    return "。".join(part for part in parts if part)


def _source_location(material: SourceMaterial) -> str:
    if material.file_type == "manual":
        return "manual:body"
    if material.file_name:
        return f"{material.file_type}:{material.file_name}"
    return f"{material.file_type}:{material.id}"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
