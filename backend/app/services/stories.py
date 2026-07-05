from __future__ import annotations

import asyncio
import re
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
from app.services.memory_markdown import build_chat_memory_context
from app.services.voice import DEFAULT_TTS_NOTICE


REVIEWED_MEMORY_STATUSES = {"confirmed", "corrected"}
STORY_SOURCE_LIMIT = 3
DEFAULT_STORY_LIMIT = 3
DEFAULT_STORY_KIND = "default_memory_story"
THINK_BLOCK_RE = re.compile(r"<think\b[^>]*>.*?</think>", re.IGNORECASE | re.DOTALL)
THINK_OPEN_RE = re.compile(r"<think\b[^>]*>.*", re.IGNORECASE | re.DOTALL)
THINK_CLOSE_RE = re.compile(r"</think>", re.IGNORECASE)
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
    return _generate_story_for_theme(db, persona, payload.theme)


def seed_default_stories(db: Session, persona: Persona) -> list[MemoryStoryRead]:
    memories = _reviewed_memories(db, persona)
    if not memories:
        return list_stories(db, persona)

    existing_defaults = _default_seed_stories(db, persona)
    needed = max(0, DEFAULT_STORY_LIMIT - len(existing_defaults))
    if needed <= 0:
        return list_stories(db, persona)

    used_seed_ids = {
        str((story.metadata_json or {}).get("seed_memory_id"))
        for story in existing_defaults
        if isinstance(story.metadata_json, dict)
        and (story.metadata_json or {}).get("seed_memory_id")
    }
    candidates = [memory for memory in memories if memory.id not in used_seed_ids]
    start_index = len(existing_defaults) + 1
    for offset, memory in enumerate(candidates[:needed], start=start_index):
        _generate_story_for_theme(
            db,
            persona,
            _seed_story_theme(memory),
            story_kind=DEFAULT_STORY_KIND,
            anchor_memory_id=memory.id,
            seed_index=offset,
        )

    return list_stories(db, persona)


def _generate_story_for_theme(
    db: Session,
    persona: Persona,
    theme: str,
    *,
    story_kind: str | None = None,
    anchor_memory_id: str | None = None,
    seed_index: int | None = None,
) -> MemoryStoryRead:
    memories = _reviewed_memories(db, persona)
    if not memories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Story generation requires confirmed or corrected memories",
        )

    memory_context = build_chat_memory_context(db, persona, theme)
    ranked_memories = _rank_story_memories(
        memories,
        theme,
        memory_context.long_term_memory_md,
        memory_context.short_term_memory_md,
    )
    if anchor_memory_id:
        ranked_memories = _with_anchor_first(ranked_memories, memories, anchor_memory_id)
    retrieved_memories = ranked_memories[:STORY_SOURCE_LIMIT] or memories[:STORY_SOURCE_LIMIT]
    story_payload = {
        "persona_id": persona.id,
        "persona_name": persona.name,
        "user_nickname_by_persona": persona.user_nickname_by_persona,
        "story_theme": theme,
        "long_term_memory_md": memory_context.long_term_memory_md,
        "short_term_memory_md": memory_context.short_term_memory_md,
        "source_memory_ids": [memory.id for memory in retrieved_memories],
        "retrieved_memories": [_memory_payload(memory) for memory in retrieved_memories],
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
    story_output = _clean_story_output(
        story_result["output"],
        persona=persona,
        theme=theme,
        fallback_memories=retrieved_memories,
    )
    story_job.status = "succeeded"
    story_job.output_json = {**story_result, "output": story_output}
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
        theme=theme,
        title=story_output["title"],
        content=story_output["content"],
        audio_url=speech_result["output"]["audio_url"],
        source_memory_ids=story_output["source_memory_ids"],
        source_memories=story_output["source_memories"],
        is_favorite=False,
        metadata_json={
            "provider": _provider_summary(story_result),
            "memory_context": {
                "source": "memory_markdown",
                "long_term_path": memory_context.long_term_path,
                "short_term_path": memory_context.short_term_path,
                "selected_memory_ids": story_payload["source_memory_ids"],
            },
            "generate_story_job_id": story_job.id,
            "synthesize_speech_job_id": speech_job.id,
            "voice": {
                "voice_status": "default_tts",
                "default_tts_notice": DEFAULT_TTS_NOTICE,
            },
        },
    )
    if story_kind:
        story.metadata_json["story_kind"] = story_kind
    if anchor_memory_id:
        story.metadata_json["seed_memory_id"] = anchor_memory_id
    if seed_index is not None:
        story.metadata_json["seed_index"] = seed_index
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
            metadata_json={"story_id": story.id, "story_theme": theme},
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
        .order_by(
            MemoryCard.is_important.desc(),
            MemoryCard.updated_at.desc(),
            MemoryCard.id.desc(),
        )
    ).all()


def _default_seed_stories(db: Session, persona: Persona) -> list[MemoryStory]:
    stories = db.scalars(
        select(MemoryStory)
        .where(MemoryStory.persona_id == persona.id, MemoryStory.deleted_at.is_(None))
        .order_by(MemoryStory.created_at.asc(), MemoryStory.id.asc())
    ).all()
    return [
        story
        for story in stories
        if isinstance(story.metadata_json, dict)
        and story.metadata_json.get("story_kind") == DEFAULT_STORY_KIND
    ]


def _seed_story_theme(memory: MemoryCard) -> str:
    title = _clean_whitespace(memory.title or "")
    if title:
        return title[:50]
    content = _clean_whitespace(memory.user_correction or memory.content or "")
    return content[:50] or "共同回忆"


def _with_anchor_first(
    ranked_memories: list[MemoryCard],
    all_memories: list[MemoryCard],
    anchor_memory_id: str,
) -> list[MemoryCard]:
    anchor = next((memory for memory in all_memories if memory.id == anchor_memory_id), None)
    if anchor is None:
        return ranked_memories
    return [anchor, *[memory for memory in ranked_memories if memory.id != anchor.id]]


def _rank_story_memories(
    memories: list[MemoryCard],
    theme: str,
    long_term_memory_md: str,
    short_term_memory_md: str,
) -> list[MemoryCard]:
    query = _normalize(theme)
    terms = _tokens(theme)
    if not query and not terms:
        return memories

    def score(memory: MemoryCard) -> tuple[int, bool, datetime, str]:
        document = _normalize(
            "\n".join(
                item
                for item in [
                    memory.title,
                    memory.content,
                    memory.user_correction,
                    memory.source_quote,
                    memory.source_location,
                    _memory_context_excerpt(long_term_memory_md, memory.id),
                    _memory_context_excerpt(short_term_memory_md, memory.id),
                ]
                if item
            )
        )
        match_score = 0
        if query and query in document:
            match_score += 10
        match_score += sum(1 for term in terms if term and term in document)
        updated_at = memory.updated_at or memory.created_at or _utcnow()
        return (match_score, memory.is_important, updated_at, memory.id)

    return sorted(memories, key=score, reverse=True)


def _memory_payload(memory: MemoryCard) -> dict[str, Any]:
    quote = memory.source_quote or memory.content
    return {
        "id": memory.id,
        "title": memory.title,
        "content": memory.user_correction or memory.content,
        "quote": quote,
        "is_important": memory.is_important,
        "source_location": memory.source_location,
    }


def _clean_story_output(
    output: dict[str, Any],
    *,
    persona: Persona,
    theme: str,
    fallback_memories: list[MemoryCard],
) -> dict[str, Any]:
    fallback_by_id = {memory.id: memory for memory in fallback_memories}
    raw_ids = output.get("source_memory_ids")
    requested_ids = [str(item) for item in raw_ids] if isinstance(raw_ids, list) else []
    source_ids = [memory_id for memory_id in requested_ids if memory_id in fallback_by_id]
    if not source_ids:
        source_ids = [memory.id for memory in fallback_memories[:STORY_SOURCE_LIMIT]]

    source_memories = [
        _story_source_payload(fallback_by_id[memory_id])
        for memory_id in source_ids
        if memory_id in fallback_by_id
    ]
    source_cards = [
        fallback_by_id[memory_id]
        for memory_id in source_ids
        if memory_id in fallback_by_id
    ]
    title = _clean_whitespace(
        _strip_model_thinking(str(output.get("title") or theme or "共同回忆"))
    )
    content = _clean_whitespace(_strip_model_thinking(str(output.get("content") or "")))
    if not content or not _contains_chinese(content):
        content = _fallback_story_content(persona, theme, source_cards or fallback_memories)
    return {
        "title": title or f"{theme}里的回忆",
        "content": content,
        "source_memory_ids": [item["memory_card_id"] for item in source_memories],
        "source_memories": source_memories,
    }


def _story_source_payload(memory: MemoryCard) -> dict[str, Any]:
    content = memory.user_correction or memory.content
    return {
        "memory_card_id": memory.id,
        "title": memory.title,
        "quote": memory.source_quote or content,
        "source_location": memory.source_location,
    }


def _fallback_story_content(persona: Persona, theme: str, memories: list[MemoryCard]) -> str:
    nickname = persona.user_nickname_by_persona or "你"
    theme_text = _clean_whitespace(theme or "共同回忆")
    memory_lines = [
        _clean_whitespace(memory.user_correction or memory.content)
        for memory in memories[:STORY_SOURCE_LIMIT]
        if _clean_whitespace(memory.user_correction or memory.content)
    ]
    if not memory_lines:
        return f"{nickname}，这段关于{theme_text}的回忆，我还需要更多已确认的资料，不能硬说成真的。"
    return (
        f"{nickname}，我想给你讲一段关于{theme_text}的回忆。我记得"
        f"{'；'.join(memory_lines)}。这些我只能按已经确认的记忆慢慢说给你听。"
    )


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


def _strip_model_thinking(text: str) -> str:
    stripped = THINK_BLOCK_RE.sub("", text)
    stripped = THINK_CLOSE_RE.sub("", stripped)
    if re.search(r"<think\b", stripped, re.IGNORECASE):
        stripped = THINK_OPEN_RE.sub("", stripped)
    return stripped.strip()


def _clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _tokens(text: str) -> list[str]:
    normalized = _normalize(text)
    ascii_words = re.findall(r"[a-z0-9_]+", normalized)
    chinese = re.findall(r"[\u4e00-\u9fff]+", normalized)
    grams: list[str] = ascii_words[:]
    for chunk in chinese:
        grams.append(chunk)
        if len(chunk) > 1:
            grams.extend(chunk[index : index + 2] for index in range(len(chunk) - 1))
    return grams


def _normalize(text: Any) -> str:
    return re.sub(r"\s+", "", str(text or "").lower())


def _memory_context_excerpt(markdown: str, memory_id: str) -> str:
    if not markdown or memory_id not in markdown:
        return ""
    index = markdown.find(memory_id)
    start = max(0, markdown.rfind("\n### ", 0, index))
    end = markdown.find("\n### ", index + len(memory_id))
    if end < 0:
        end = min(len(markdown), index + 1000)
    return markdown[start:end]


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
