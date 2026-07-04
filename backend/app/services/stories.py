from __future__ import annotations

import asyncio
import struct
import threading
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_job import AIJob
from app.models.memory_card import MemoryCard
from app.models.memory_story import MemoryStory
from app.models.persona import Persona
from app.models.user import User
from app.providers.gateway import ProviderGateway
from app.schemas.story import (
    MemoryStoryCreate,
    MemoryStoryExportResponse,
    MemoryStoryFavoriteUpdate,
    MemoryStoryRead,
    StoryMemorySource,
)
from app.services.audit import write_audit_event
from app.services.voice import DEFAULT_TTS_NOTICE


REVIEWED_MEMORY_STATUSES = {"confirmed", "corrected"}
MOCK_AUDIO_EXPORT_NOTICE = (
    "当前音频来自 mock TTS audio_url，不是 TA 的真实声音，也不是已落盘的真实音频文件。"
)
MOCK_AUDIO_FILE_NOTICE = "AI simulation mock TTS audio; not TA real voice; default TTS fallback."


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def list_stories(db: Session, persona: Persona) -> list[MemoryStoryRead]:
    stories = db.scalars(
        select(MemoryStory)
        .where(MemoryStory.persona_id == persona.id, MemoryStory.deleted_at.is_(None))
        .order_by(MemoryStory.created_at.desc(), MemoryStory.id.desc())
    ).all()
    return [_story_response(story) for story in stories]


def generate_story(
    db: Session,
    persona: Persona,
    payload: MemoryStoryCreate,
) -> MemoryStoryRead:
    memories = _reviewed_memories(db, persona)
    if not memories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Story generation requires confirmed or corrected memories",
        )

    story_payload = {
        "persona_id": persona.id,
        "persona_name": persona.name,
        "user_nickname_by_persona": persona.user_nickname_by_persona,
        "story_theme": payload.theme,
        "retrieved_memories": [_memory_payload(memory) for memory in memories],
    }
    story_job = _create_running_job(
        persona=persona,
        job_type="generate_story",
        provider_name="mock_story_generation",
        input_json=story_payload,
    )
    db.add(story_job)
    db.flush()

    story_result = _run_gateway(
        "story_generation",
        {**story_payload, "job_id": story_job.id},
    )
    story_output = story_result["output"]
    story_job.status = "succeeded"
    story_job.output_json = story_result
    story_job.finished_at = _utcnow()

    speech_payload = {
        "persona_id": persona.id,
        "persona_name": persona.name,
        "text": story_output["content"],
        "voice_status": "default_tts",
        "default_tts_notice": DEFAULT_TTS_NOTICE,
    }
    speech_job = _create_running_job(
        persona=persona,
        job_type="synthesize_speech",
        provider_name="mock_tts",
        input_json=speech_payload,
    )
    db.add(speech_job)
    db.flush()
    speech_result = _run_gateway("tts", {**speech_payload, "job_id": speech_job.id})
    speech_job.status = "succeeded"
    speech_job.output_json = speech_result
    speech_job.finished_at = _utcnow()

    story = MemoryStory(
        persona_id=persona.id,
        theme=payload.theme,
        title=story_output["title"],
        content=story_output["content"],
        audio_url=speech_result["output"]["audio_url"],
        source_memory_ids=story_output["source_memory_ids"],
        source_memories=story_output["source_memories"],
        is_favorite=False,
        metadata_json={
            "provider": _provider_summary(story_result),
            "generate_story_job_id": story_job.id,
            "synthesize_speech_job_id": speech_job.id,
            "voice": {
                "voice_status": "default_tts",
                "default_tts_notice": DEFAULT_TTS_NOTICE,
            },
        },
    )
    db.add(story)
    db.flush()
    for memory_id in story.source_memory_ids or []:
        write_audit_event(
            db,
            user_id=persona.user_id,
            persona_id=persona.id,
            target_type="memory",
            target_id=str(memory_id),
            event_type="memory.cited_in_story",
            severity="debug",
            action="故事生成引用记忆",
            metadata_json={"story_id": story.id, "story_theme": payload.theme},
        )
    db.add(story_job)
    db.add(speech_job)
    db.commit()
    db.refresh(story)
    return _story_response(story)


def update_story_favorite(
    db: Session,
    user: User,
    story_id: str,
    payload: MemoryStoryFavoriteUpdate,
) -> MemoryStoryRead:
    story = _get_story_or_404(db, user, story_id)
    story.is_favorite = payload.is_favorite
    db.add(story)
    db.commit()
    db.refresh(story)
    return _story_response(story)


def export_story(
    db: Session,
    persona: Persona,
    story_id: str,
) -> MemoryStoryExportResponse:
    story = _get_persona_story_or_404(db, persona, story_id)

    source_memories = [
        StoryMemorySource.model_validate(item) for item in (story.source_memories or [])
    ]
    return MemoryStoryExportResponse(
        story_id=story.id,
        persona_id=story.persona_id,
        theme=story.theme,
        title=story.title,
        export_text=_story_export_text(story, source_memories),
        text_filename=f"story-{story.id}.txt",
        audio_url=story.audio_url,
        audio_filename=f"story-{story.id}.wav" if story.audio_url else None,
        audio_export_notice=MOCK_AUDIO_EXPORT_NOTICE,
        source_memory_ids=[str(item) for item in (story.source_memory_ids or [])],
        source_memories=source_memories,
    )


def export_story_audio(
    db: Session,
    persona: Persona,
    story_id: str,
) -> tuple[str, bytes, str]:
    story = _get_persona_story_or_404(db, persona, story_id)
    filename = f"story-{story.id}.wav"
    return filename, _mock_story_wav_bytes(story), MOCK_AUDIO_FILE_NOTICE


def _reviewed_memories(db: Session, persona: Persona) -> list[MemoryCard]:
    return db.scalars(
        select(MemoryCard)
        .where(
            MemoryCard.persona_id == persona.id,
            MemoryCard.deleted_at.is_(None),
            MemoryCard.status.in_(REVIEWED_MEMORY_STATUSES),
        )
        .order_by(MemoryCard.updated_at.desc(), MemoryCard.id.desc())
        .limit(3)
    ).all()


def _memory_payload(memory: MemoryCard) -> dict[str, Any]:
    quote = memory.source_quote or memory.content
    return {
        "id": memory.id,
        "title": memory.title,
        "content": memory.user_correction or memory.content,
        "quote": quote,
        "source_location": memory.source_location,
    }


def _story_response(story: MemoryStory) -> MemoryStoryRead:
    return MemoryStoryRead(
        id=story.id,
        persona_id=story.persona_id,
        theme=story.theme,
        title=story.title,
        content=story.content,
        audio_url=story.audio_url,
        source_memory_ids=[str(item) for item in (story.source_memory_ids or [])],
        source_memories=[
            StoryMemorySource.model_validate(item) for item in (story.source_memories or [])
        ],
        is_favorite=story.is_favorite,
        metadata_json=story.metadata_json,
        created_at=story.created_at,
        updated_at=story.updated_at,
    )


def _story_export_text(story: MemoryStory, sources: list[StoryMemorySource]) -> str:
    lines = [
        story.title,
        "",
        f"主题：{story.theme}",
        "",
        story.content,
        "",
        "来源记忆：",
    ]
    if not sources:
        lines.append("- 无")
    for source in sources:
        location = f"（{source.source_location}）" if source.source_location else ""
        lines.append(f"- {source.title}{location}: {source.quote}")
    lines.extend(["", MOCK_AUDIO_EXPORT_NOTICE, DEFAULT_TTS_NOTICE])
    return "\n".join(lines)


def _get_persona_story_or_404(db: Session, persona: Persona, story_id: str) -> MemoryStory:
    story = db.scalar(
        select(MemoryStory).where(
            MemoryStory.id == story_id,
            MemoryStory.persona_id == persona.id,
            MemoryStory.deleted_at.is_(None),
        )
    )
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return story


def _get_story_or_404(db: Session, user: User, story_id: str) -> MemoryStory:
    story = db.scalar(
        select(MemoryStory)
        .join(Persona, MemoryStory.persona_id == Persona.id)
        .where(
            MemoryStory.id == story_id,
            MemoryStory.deleted_at.is_(None),
            Persona.user_id == user.id,
            Persona.deleted_at.is_(None),
        )
    )
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return story


def _mock_story_wav_bytes(story: MemoryStory) -> bytes:
    sample_rate = 8000
    channels = 1
    sample_width = 2
    silence = b"\x00\x00" * (sample_rate // 4)
    fmt_chunk = struct.pack(
        "<HHIIHH",
        1,
        channels,
        sample_rate,
        sample_rate * channels * sample_width,
        channels * sample_width,
        sample_width * 8,
    )
    comment = f"{MOCK_AUDIO_FILE_NOTICE} story_id={story.id}".encode("ascii")
    info_chunk = b"INFO" + _riff_chunk(b"ICMT", comment)
    chunks = (
        _riff_chunk(b"fmt ", fmt_chunk)
        + _riff_chunk(b"LIST", info_chunk)
        + _riff_chunk(b"data", silence)
    )
    return b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks


def _riff_chunk(chunk_id: bytes, data: bytes) -> bytes:
    padding = b"\x00" if len(data) % 2 else b""
    return chunk_id + struct.pack("<I", len(data)) + data + padding


def _create_running_job(
    *,
    persona: Persona,
    job_type: str,
    provider_name: str,
    input_json: dict[str, Any],
) -> AIJob:
    return AIJob(
        user_id=persona.user_id,
        persona_id=persona.id,
        job_type=job_type,
        provider_type="local",
        provider_name=provider_name,
        status="running",
        input_json=input_json,
        started_at=_utcnow(),
    )


def _provider_summary(result: dict[str, Any]) -> dict[str, str]:
    return {
        "provider_name": str(result["provider_name"]),
        "capability": str(result["capability"]),
        "status": str(result["status"]),
    }


def _run_gateway(capability: str, payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] | None = None

    def runner() -> None:
        nonlocal result
        result = asyncio.run(ProviderGateway().run(capability, payload))

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()
    if result is None:
        raise RuntimeError("Provider gateway did not return a result")
    return result
