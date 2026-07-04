from __future__ import annotations

import asyncio
import re
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_job import AIJob
from app.models.conversation import Conversation, Message, MessageCitation
from app.models.memory_card import MemoryCard
from app.models.persona import Persona
from app.models.persona_profile import PersonaProfile
from app.models.source_material import SourceMaterial
from app.models.user import User
from app.providers.gateway import ProviderGateway
from app.schemas.chat import (
    MessageCitationRead,
    MessageRead,
    MemoryCorrectionCreate,
    MemoryCorrectionResponse,
    VoiceMessageSend,
)
from app.schemas.memory import MemoryRead
from app.schemas.voice import SpeechSynthesisCreate
from app.services.profile import get_or_create_profile, refresh_profile_and_trust
from app.services.voice import synthesize_speech


INACTIVE_MEMORY_STATUSES = {"rejected", "disabled"}
FACT_STATUSES = {"corrected", "confirmed"}
WEAK_REFERENCE_STATUSES = {"pending_review", "auto_generated"}
STATUS_PRIORITY = {
    "corrected": 500,
    "confirmed": 400,
    "pending_review": 100,
    "auto_generated": 80,
}
KEY_TERMS = (
    "馄饨",
    "饺子",
    "红烧鱼",
    "糖醋鱼",
    "清蒸鱼",
    "做饭",
    "做什么",
    "喜欢",
    "常说",
    "慢慢来",
    "想你",
    "难过",
    "撑不住",
    "吃",
    "鱼",
)
EMOTIONAL_TERMS = ("想你", "难过", "撑不住", "遗憾", "害怕", "孤单", "想念")
BANNED_REPLY_TERMS = ("AI 助手", "AI助手", "语言模型", "我是系统", "我真的回来了")


@dataclass(frozen=True)
class RetrievedMemory:
    memory: MemoryCard
    score: int
    overlap: int


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_conversation_or_404(
    db: Session,
    user: User,
    conversation_id: str,
) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
            Conversation.deleted_at.is_(None),
        )
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return conversation


def get_message_or_404(db: Session, user: User, message_id: str) -> Message:
    message = db.scalar(
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Message.id == message_id,
            Conversation.user_id == user.id,
            Conversation.deleted_at.is_(None),
        )
    )
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return message


def list_message_citations(db: Session, message_id: str) -> list[MessageCitation]:
    return db.scalars(
        select(MessageCitation)
        .where(MessageCitation.message_id == message_id)
        .order_by(MessageCitation.created_at.asc(), MessageCitation.id.asc())
    ).all()


def message_response(db: Session, message: Message) -> MessageRead:
    citations = [
        MessageCitationRead.model_validate(citation)
        for citation in list_message_citations(db, message.id)
    ]
    return MessageRead.model_validate(message).model_copy(
        update={"citations": citations}
    )


def retrieve_memories(
    db: Session,
    persona: Persona,
    user_message: str,
    limit: int = 4,
) -> list[RetrievedMemory]:
    query_terms = _terms(user_message)
    memories = db.scalars(
        select(MemoryCard).where(
            MemoryCard.persona_id == persona.id,
            MemoryCard.deleted_at.is_(None),
            MemoryCard.status.not_in(INACTIVE_MEMORY_STATUSES),
        )
    ).all()

    scored: list[RetrievedMemory] = []
    for memory in memories:
        if not _memory_is_retrievable(memory):
            continue
        overlap = len(query_terms & _memory_terms(memory))
        if overlap == 0:
            continue
        score = STATUS_PRIORITY.get(memory.status, 0)
        score += overlap * 30
        score += min(memory.confidence_score or 0, 100)
        score += _category_boost(memory, user_message)
        scored.append(RetrievedMemory(memory=memory, score=score, overlap=overlap))

    fact_scored = [item for item in scored if item.memory.status in FACT_STATUSES]
    if fact_scored:
        scored = fact_scored

    return sorted(
        scored,
        key=lambda item: (
            item.score,
            STATUS_PRIORITY.get(item.memory.status, 0),
            item.memory.updated_at,
            item.memory.id,
        ),
        reverse=True,
    )[:limit]


def build_conversation_history(
    db: Session,
    conversation: Conversation,
    limit: int = 8,
) -> list[Message]:
    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit)
    ).all()
    return list(reversed(messages))


def send_text_message(
    db: Session,
    conversation: Conversation,
    persona: Persona,
    content: str,
) -> Message:
    profile = get_or_create_profile(db, persona)
    retrieved = retrieve_memories(db, persona, content)
    history = build_conversation_history(db, conversation)
    used_memories = _used_memories(retrieved)
    user_message_time = _utcnow()
    persona_message_time = user_message_time + timedelta(microseconds=1)

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=content,
        metadata_json=None,
        created_at=user_message_time,
    )
    db.add(user_message)
    db.flush()

    reply_content = generate_persona_reply(
        persona=persona,
        profile=profile,
        retrieved_memories=used_memories,
        history=history,
        user_message=content,
    )
    chat_result = run_chat_gateway(
        persona=persona,
        profile=profile,
        retrieved_memories=used_memories,
        history=history,
        user_message=content,
        draft_reply=reply_content,
    )
    reply_content = chat_result["output"]["reply_text"]
    persona_message = Message(
        conversation_id=conversation.id,
        role="persona",
        content=reply_content,
        metadata_json={
            "provider": chat_result["provider_name"],
            "capability": chat_result["capability"],
            "retrieval": [
                {
                    "memory_card_id": item.memory.id,
                    "score": item.score,
                    "overlap": item.overlap,
                    "status": item.memory.status,
                }
                for item in used_memories
            ],
        },
        created_at=persona_message_time,
    )
    db.add(persona_message)
    db.flush()

    for item in used_memories:
        memory = item.memory
        db.add(
            MessageCitation(
                message_id=persona_message.id,
                memory_card_id=memory.id,
                source_material_id=memory.source_material_id,
                parsed_chunk_id=memory.parsed_chunk_id,
                quote=memory.user_correction or memory.source_quote or memory.content,
                source_location=memory.source_location,
            )
        )
    conversation.updated_at = _utcnow()
    db.add(conversation)
    db.commit()
    db.refresh(persona_message)
    return persona_message


def send_voice_message(
    db: Session,
    conversation: Conversation,
    persona: Persona,
    payload: VoiceMessageSend,
) -> Message:
    source_material = _get_audio_source_or_404(
        db,
        conversation,
        persona,
        payload.source_material_id,
    )
    asr_payload = {
        "persona_id": persona.id,
        "conversation_id": conversation.id,
        "source_material_id": source_material.id,
        "file_name": source_material.file_name,
        "user_description": source_material.user_description,
    }
    asr_job = AIJob(
        user_id=conversation.user_id,
        persona_id=persona.id,
        source_material_id=source_material.id,
        job_type="asr_audio",
        provider_type="local",
        provider_name="mock_asr",
        status="running",
        input_json=asr_payload,
        started_at=_utcnow(),
    )
    db.add(asr_job)
    db.flush()

    asr_result = _run_gateway("asr", {**asr_payload, "job_id": asr_job.id})
    transcript = asr_result["output"]["transcript"]
    asr_job.status = "succeeded"
    asr_job.output_json = asr_result
    asr_job.finished_at = _utcnow()
    db.add(asr_job)
    db.flush()

    reply = send_text_message(db, conversation, persona, transcript)
    synthesis = synthesize_speech(
        db,
        persona,
        SpeechSynthesisCreate(text=reply.content),
    )
    metadata = dict(reply.metadata_json or {})
    metadata["voice"] = {
        "source_material_id": source_material.id,
        "transcript": transcript,
        "asr_job_id": asr_job.id,
        "synthesize_job_id": synthesis.job.id,
        "audio_url": synthesis.audio_url,
        "voice_status": synthesis.voice_status,
    }
    reply.audio_url = synthesis.audio_url
    reply.metadata_json = metadata
    db.add(reply)
    db.commit()
    db.refresh(reply)
    return reply


def run_chat_gateway(
    persona: Persona,
    profile: PersonaProfile,
    retrieved_memories: list[RetrievedMemory],
    history: list[Message],
    user_message: str,
    draft_reply: str,
) -> dict[str, Any]:
    payload = {
        "persona_name": persona.name,
        "persona_type": persona.persona_type,
        "relationship_to_user": persona.relationship_to_user,
        "user_nickname_by_persona": persona.user_nickname_by_persona,
        "speaking_style": persona.speaking_style,
        "emotional_style": persona.emotional_style,
        "forbidden_expressions": persona.forbidden_expressions,
        "profile_summary": profile.profile_summary,
        "retrieved_memories": [
            {
                "memory_card_id": item.memory.id,
                "status": item.memory.status,
                "content": item.memory.user_correction or item.memory.content,
                "source_quote": item.memory.source_quote,
                "source_location": item.memory.source_location,
            }
            for item in retrieved_memories
        ],
        "conversation_history": [
            {"role": message.role, "content": message.content} for message in history
        ],
        "user_message": user_message,
        "confidence_score": persona.trust_score,
        "voice_mode": "not_implemented_milestone_5",
        "avatar_mode": "not_implemented_milestone_5",
        "used_memory_ids": [item.memory.id for item in retrieved_memories],
        "draft_reply": draft_reply,
    }
    return _run_gateway("chat_llm", payload)


def generate_persona_reply(
    persona: Persona,
    profile: PersonaProfile,
    retrieved_memories: list[RetrievedMemory],
    history: list[Message],
    user_message: str,
) -> str:
    del history
    nickname = persona.user_nickname_by_persona
    profile_hint = _profile_hint(profile)
    emotional_prefix = (
        f"{nickname}，我听见你现在很难受，我会先陪你把这口气慢慢缓下来。"
        if _is_emotional_message(user_message)
        else ""
    )

    if not retrieved_memories:
        reply = (
            f"{nickname}，这件事我记不太清，不能硬说成真的。"
            "你可以再给我一点资料，或者把你记得的细节慢慢告诉我。"
        )
        if emotional_prefix:
            reply = f"{emotional_prefix}{reply}"
        return _sanitize_reply(reply, persona)

    memory = retrieved_memories[0].memory
    memory_text = memory.user_correction or memory.content
    reply = f"{nickname}，我记得，{memory_text}"
    if _is_emotional_message(user_message):
        reply = (
            f"{emotional_prefix}我也会记着这段和你有关的事：{memory_text}"
            "你难过的时候，可以慢慢跟我说。"
        )
    else:
        style_note = "我会慢慢和你说。" if profile_hint else ""
        reply = f"{reply}{style_note}你愿意的话，可以继续问我这段记忆。"
    return _sanitize_reply(reply, persona)


def correct_cited_memory(
    db: Session,
    user: User,
    message: Message,
    payload: MemoryCorrectionCreate,
) -> MemoryCorrectionResponse:
    citation = db.scalar(
        select(MessageCitation)
        .join(Message, MessageCitation.message_id == Message.id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            MessageCitation.message_id == message.id,
            MessageCitation.memory_card_id == payload.memory_id,
            Conversation.user_id == user.id,
            Conversation.deleted_at.is_(None),
        )
    )
    if citation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    memory = db.scalar(
        select(MemoryCard)
        .join(Persona, MemoryCard.persona_id == Persona.id)
        .where(
            MemoryCard.id == payload.memory_id,
            MemoryCard.deleted_at.is_(None),
            Persona.user_id == user.id,
            Persona.deleted_at.is_(None),
        )
    )
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    memory.content = payload.content
    if payload.title is not None:
        memory.title = payload.title
    memory.status = "corrected"
    memory.user_correction = payload.content
    db.add(memory)

    persona = db.get(Persona, memory.persona_id)
    if persona is not None:
        refresh_profile_and_trust(db, persona)

    db.commit()
    db.refresh(memory)
    return MemoryCorrectionResponse(
        memory=MemoryRead.model_validate(memory),
        message="记忆已纠正，后续对话会优先使用这条修正后的内容。",
    )


def _used_memories(retrieved: list[RetrievedMemory]) -> list[RetrievedMemory]:
    if not retrieved:
        return []
    top = retrieved[0]
    if top.memory.status not in FACT_STATUSES and top.overlap < 2:
        return []
    return [top]


def _get_audio_source_or_404(
    db: Session,
    conversation: Conversation,
    persona: Persona,
    source_material_id: str,
) -> SourceMaterial:
    source_material = db.scalar(
        select(SourceMaterial).where(
            SourceMaterial.id == source_material_id,
            SourceMaterial.user_id == conversation.user_id,
            SourceMaterial.persona_id == persona.id,
            SourceMaterial.deleted_at.is_(None),
        )
    )
    if source_material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if source_material.file_type != "audio":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Voice messages require an audio source material",
        )
    return source_material


def _memory_is_retrievable(memory: MemoryCard) -> bool:
    if memory.status in FACT_STATUSES:
        return True
    return (
        memory.status in WEAK_REFERENCE_STATUSES
        and memory.confidence_level in {"high", "medium"}
    )


def _memory_terms(memory: MemoryCard) -> set[str]:
    return _terms(" ".join([memory.title or "", memory.content or ""]))


def _terms(text: str) -> set[str]:
    normalized = re.sub(r"\s+", "", text.lower())
    terms = set(re.findall(r"[a-z0-9]+", text.lower()))
    for chunk in re.findall(r"[\u4e00-\u9fff]+", normalized):
        if len(chunk) <= 2:
            terms.add(chunk)
        else:
            terms.update(chunk[index : index + 2] for index in range(len(chunk) - 1))
            terms.add(chunk)
    for term in KEY_TERMS:
        if term in text:
            terms.add(term)
    return {term for term in terms if term}


def _category_boost(memory: MemoryCard, user_message: str) -> int:
    if memory.category == "expression_style" and any(
        term in user_message for term in ("说", "口头禅", "怎么讲")
    ):
        return 30
    if memory.category in {"shared_event", "story_material"} and any(
        term in user_message for term in ("记得", "以前", "那次")
    ):
        return 20
    if memory.category == "preference" and any(
        term in user_message for term in ("喜欢", "吃", "做什么")
    ):
        return 20
    return 0


def _profile_hint(profile: PersonaProfile) -> str:
    summary = (profile.profile_summary or "").strip()
    if not summary:
        return ""
    return f"按我现在整理出的档案，我会尽量保持这样的语气：{summary}"


def _is_emotional_message(text: str) -> bool:
    return any(term in text for term in EMOTIONAL_TERMS)


def _sanitize_reply(reply: str, persona: Persona) -> str:
    sanitized = reply
    forbidden_text = persona.forbidden_expressions or ""
    for term in BANNED_REPLY_TERMS:
        sanitized = sanitized.replace(term, "")
    for term in _forbidden_terms(forbidden_text):
        sanitized = sanitized.replace(term, "")
    return re.sub(r"\s+", " ", sanitized).strip()


def _forbidden_terms(text: str) -> list[str]:
    terms: list[str] = []
    for quoted in re.findall(r"[「\"]([^」\"]+)[」\"]", text):
        if quoted:
            terms.append(quoted)
    return terms


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
