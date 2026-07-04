from __future__ import annotations

import asyncio
import re
import threading
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
from app.services.memory_markdown import (
    MemoryMarkdownContext,
    build_chat_memory_context,
    refresh_long_term_memory_md,
    refresh_short_term_memory_md,
)
from app.services.profile import get_or_create_profile, refresh_profile_and_trust
from app.services.audit import snapshot_entity, write_audit_event
from app.services.conflict_detector import detect_conflicts_for_memory
from app.services.voice import synthesize_speech


FACT_STATUSES = {"corrected", "confirmed"}
EMOTIONAL_TERMS = ("想你", "难过", "撑不住", "遗憾", "害怕", "孤单", "想念")
BANNED_REPLY_TERMS = ("AI 助手", "AI助手", "语言模型", "我是系统", "我真的回来了")
THINK_BLOCK_RE = re.compile(r"<think\b[^>]*>.*?</think>", re.IGNORECASE | re.DOTALL)
THINK_OPEN_RE = re.compile(r"<think\b[^>]*>.*", re.IGNORECASE | re.DOTALL)
THINK_CLOSE_RE = re.compile(r"</think>", re.IGNORECASE)


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
        .where(
            MessageCitation.message_id == message_id,
            MessageCitation.deleted_at.is_(None),
        )
        .order_by(MessageCitation.created_at.asc(), MessageCitation.id.asc())
    ).all()


def message_response(db: Session, message: Message) -> MessageRead:
    citations = [
        MessageCitationRead.model_validate(citation)
        for citation in list_message_citations(db, message.id)
    ]
    content = _message_output_content(message)
    return MessageRead.model_validate(message).model_copy(
        update={"content": content, "citations": citations}
    )


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
    memory_context = build_chat_memory_context(db, persona, content)
    history = build_conversation_history(db, conversation)
    selected_memories = _selected_memory_cards(
        db,
        persona,
        memory_context.selected_memory_ids,
    )
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

    draft_reply_content = generate_persona_reply(
        persona=persona,
        profile=profile,
        selected_memories=selected_memories,
        history=history,
        user_message=content,
    )
    chat_result = run_chat_gateway(
        persona=persona,
        profile=profile,
        memory_context=memory_context,
        history=history,
        user_message=content,
        draft_reply=draft_reply_content,
    )
    reply_content = _sanitize_reply(chat_result["output"]["reply_text"], persona)
    if not reply_content:
        reply_content = draft_reply_content
    persona_message = Message(
        conversation_id=conversation.id,
        role="persona",
        content=reply_content,
        metadata_json={
            "provider": chat_result["provider_name"],
            "capability": chat_result["capability"],
            "memory_context": {
                "source": "memory_markdown",
                "long_term_path": memory_context.long_term_path,
                "short_term_path": memory_context.short_term_path,
                "selected_memory_ids": [memory.id for memory in selected_memories],
                "long_term_compressed": memory_context.long_term_compressed,
                "short_term_compressed": memory_context.short_term_compressed,
                "compression_failed": memory_context.compression_failed,
                "compression_provider": memory_context.compression_provider,
            },
            "retrieval": [
                {
                    "memory_card_id": memory.id,
                    "source": "memory_markdown",
                }
                for memory in selected_memories
            ],
        },
        created_at=persona_message_time,
    )
    db.add(persona_message)
    db.flush()

    for index, memory in enumerate(selected_memories, start=1):
        db.add(
            MessageCitation(
                message_id=persona_message.id,
                memory_card_id=memory.id,
                source_material_id=memory.source_material_id,
                parsed_chunk_id=memory.parsed_chunk_id,
                quote=memory.user_correction or memory.source_quote or memory.content,
                source_location=memory.source_location,
                created_at=persona_message_time + timedelta(microseconds=index),
            )
        )
        write_audit_event(
            db,
            user_id=conversation.user_id,
            persona_id=persona.id,
            target_type="memory",
            target_id=memory.id,
            event_type="memory.retrieved",
            severity="debug",
            action="对话检索引用记忆",
            metadata_json={
                "conversation_id": conversation.id,
                "user_message_id": user_message.id,
                "persona_message_id": persona_message.id,
            },
        )
    conversation.updated_at = _utcnow()
    db.add(conversation)
    refresh_short_term_memory_md(db, persona)
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
        "storage_url": source_material.storage_url,
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


def soft_delete_conversation(db: Session, conversation: Conversation) -> None:
    deleted_at = _utcnow()
    conversation.deleted_at = deleted_at
    db.add(conversation)

    messages = db.scalars(
        select(Message).where(
            Message.conversation_id == conversation.id,
            Message.deleted_at.is_(None),
        )
    ).all()
    message_ids: list[str] = []
    for message in messages:
        message_ids.append(message.id)
        message.deleted_at = deleted_at
        db.add(message)

    if message_ids:
        citations = db.scalars(
            select(MessageCitation).where(
                MessageCitation.message_id.in_(message_ids),
                MessageCitation.deleted_at.is_(None),
            )
        ).all()
        for citation in citations:
            citation.deleted_at = deleted_at
            db.add(citation)

    db.commit()


def run_chat_gateway(
    persona: Persona,
    profile: PersonaProfile,
    memory_context: MemoryMarkdownContext,
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
        "long_term_memory_md": memory_context.long_term_memory_md,
        "short_term_memory_md": memory_context.short_term_memory_md,
        "selected_memory_ids": memory_context.selected_memory_ids,
        "conversation_history": [
            {"role": message.role, "content": _history_message_content(message, persona)}
            for message in history
        ],
        "user_message": user_message,
        "confidence_score": persona.trust_score,
        "voice_mode": "not_implemented_milestone_5",
        "avatar_mode": "not_implemented_milestone_5",
        "used_memory_ids": memory_context.selected_memory_ids,
        "draft_reply": draft_reply,
    }
    return _run_gateway("chat_llm", payload)


def generate_persona_reply(
    persona: Persona,
    profile: PersonaProfile,
    selected_memories: list[MemoryCard],
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

    if not selected_memories:
        reply = (
            f"{nickname}，这件事我记不太清，不能硬说成真的。"
            "你可以再给我一点资料，或者把你记得的细节慢慢告诉我。"
        )
        if emotional_prefix:
            reply = f"{emotional_prefix}{reply}"
        return _sanitize_reply(reply, persona)

    memory = selected_memories[0]
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

    before = snapshot_entity(memory)
    memory.content = payload.content
    if payload.title is not None:
        memory.title = payload.title
    memory.status = "corrected"
    memory.user_correction = payload.content
    db.add(memory)

    persona = db.get(Persona, memory.persona_id)
    if persona is not None:
        refresh_profile_and_trust(db, persona)
        refresh_long_term_memory_md(db, persona)

    db.flush()
    if persona is not None:
        write_audit_event(
            db,
            user_id=user.id,
            persona_id=persona.id,
            target_type="memory",
            target_id=memory.id,
            event_type="memory.corrected_in_chat",
            action="对话中纠正被引用的记忆",
            before_snapshot=before,
            after_snapshot=snapshot_entity(memory),
            metadata_json={"message_id": message.id},
        )
        detect_conflicts_for_memory(db, memory)

    db.commit()
    db.refresh(memory)
    return MemoryCorrectionResponse(
        memory=MemoryRead.model_validate(memory),
        message="记忆已纠正，后续对话会优先使用这条修正后的内容。",
    )


def _selected_memory_cards(
    db: Session,
    persona: Persona,
    memory_ids: list[str],
) -> list[MemoryCard]:
    if not memory_ids:
        return []
    rows = db.scalars(
        select(MemoryCard).where(
            MemoryCard.persona_id == persona.id,
            MemoryCard.id.in_(memory_ids),
            MemoryCard.status.in_(FACT_STATUSES),
            MemoryCard.deleted_at.is_(None),
        )
    ).all()
    by_id = {memory.id: memory for memory in rows}
    return [by_id[memory_id] for memory_id in memory_ids if memory_id in by_id]


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


def _profile_hint(profile: PersonaProfile) -> str:
    summary = (profile.profile_summary or "").strip()
    if not summary:
        return ""
    return f"按我现在整理出的档案，我会尽量保持这样的语气：{summary}"


def _is_emotional_message(text: str) -> bool:
    return any(term in text for term in EMOTIONAL_TERMS)


def _sanitize_reply(reply: str, persona: Persona) -> str:
    sanitized = _strip_model_thinking(reply)
    forbidden_text = persona.forbidden_expressions or ""
    for term in BANNED_REPLY_TERMS:
        sanitized = sanitized.replace(term, "")
    for term in _forbidden_terms(forbidden_text):
        sanitized = sanitized.replace(term, "")
    return re.sub(r"\s+", " ", sanitized).strip()


def _message_output_content(message: Message) -> str:
    if message.role != "persona":
        return message.content
    return _strip_model_thinking(message.content)


def _history_message_content(message: Message, persona: Persona) -> str:
    if message.role != "persona":
        return message.content
    return _sanitize_reply(message.content, persona)


def _strip_model_thinking(text: str) -> str:
    stripped = THINK_BLOCK_RE.sub("", text)
    stripped = THINK_CLOSE_RE.sub("", stripped)
    if re.search(r"<think\b", stripped, re.IGNORECASE):
        stripped = THINK_OPEN_RE.sub("", stripped)
    return stripped.strip()


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
