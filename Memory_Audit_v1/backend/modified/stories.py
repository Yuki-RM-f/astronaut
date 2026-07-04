from __future__ import annotations

import asyncio
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
    MemoryStoryFavoriteUpdate,
    MemoryStoryRead,
    StoryMemorySource,
)
from app.services.audit import write_audit_event
from app.services.voice import DEFAULT_TTS_NOTICE


REVIEWED_MEMORY_STATUSES = {"confirmed", "corrected"}


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
    db.add(story_job)
    db.add(speech_job)
    db.commit()
    db.refresh(story)

    for mem_id in story_output.get("source_memory_ids", []):
        write_audit_event(
            db,
            user_id=persona.user_id,  # type: ignore[attr-defined]
            persona_id=persona.id,
            target_type="memory_card",
            target_id=mem_id,
            event_type="memory.cited_in_story",
            severity="info",
            action=f"Memory used in story '{story.title}'",
            metadata_json={"story_id": story.id},
        )

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
