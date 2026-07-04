from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Message
from app.models.memory_card import MemoryCard
from app.models.user import User
from app.schemas.chat import ConversationRead
from app.schemas.data_export import (
    ConversationExportResponse,
    PersonaExportSnapshot,
    PersonaMemoriesExportResponse,
    PersonaProfileExportResponse,
)
from app.schemas.memory import MemoryRead
from app.services.chat import get_conversation_or_404, message_response
from app.services.materials import get_persona_or_404
from app.services.profile import (
    calculate_trust_report,
    get_or_create_profile,
    profile_response,
)


EXPORT_WATERMARK = "AI 模拟导出：内容来自当前 Demo 数据和模型生成结果，请以用户确认资料为准。"


def export_persona_profile(
    db: Session,
    current_user: User,
    persona_id: str,
) -> PersonaProfileExportResponse:
    persona = get_persona_or_404(persona_id, current_user, db)
    profile = get_or_create_profile(db, persona)
    report = calculate_trust_report(db, persona)
    persona.trust_score = report.trust_score
    db.add(persona)
    db.flush()
    return PersonaProfileExportResponse(
        export_type="profile",
        filename=f"persona-{persona.id}-profile.json",
        exported_at=_utcnow(),
        watermark=EXPORT_WATERMARK,
        persona=PersonaExportSnapshot.model_validate(persona),
        profile=profile_response(profile, report, persona),
    )


def export_persona_memories(
    db: Session,
    current_user: User,
    persona_id: str,
) -> PersonaMemoriesExportResponse:
    persona = get_persona_or_404(persona_id, current_user, db)
    memories = db.scalars(
        select(MemoryCard)
        .where(
            MemoryCard.persona_id == persona.id,
            MemoryCard.deleted_at.is_(None),
        )
        .order_by(MemoryCard.created_at.asc(), MemoryCard.id.asc())
    ).all()
    return PersonaMemoriesExportResponse(
        export_type="memories",
        filename=f"persona-{persona.id}-memories.json",
        exported_at=_utcnow(),
        watermark=EXPORT_WATERMARK,
        persona=PersonaExportSnapshot.model_validate(persona),
        items=[MemoryRead.model_validate(memory) for memory in memories],
    )


def export_conversation(
    db: Session,
    current_user: User,
    conversation_id: str,
) -> ConversationExportResponse:
    conversation = get_conversation_or_404(db, current_user, conversation_id)
    messages = db.scalars(
        select(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.deleted_at.is_(None),
        )
        .order_by(Message.created_at.asc(), Message.id.asc())
    ).all()
    return ConversationExportResponse(
        export_type="conversation",
        filename=f"conversation-{conversation.id}.json",
        exported_at=_utcnow(),
        watermark=EXPORT_WATERMARK,
        conversation=ConversationRead.model_validate(conversation),
        messages=[message_response(db, message) for message in messages],
    )


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
