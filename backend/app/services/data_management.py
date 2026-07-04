from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_job import AIJob
from app.models.conversation import Conversation, Message, MessageCitation
from app.models.memory_card import MemoryCard
from app.models.memory_story import MemoryStory
from app.models.parsed_chunk import ParsedChunk
from app.models.persona import Persona
from app.models.persona_profile import PersonaProfile
from app.models.source_material import SourceMaterial
from app.models.user import User
from app.models.voice_avatar import AvatarModel, VoiceModel


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def mark_deleted(row, deleted_at: datetime) -> None:
    if row.deleted_at is None:
        row.deleted_at = deleted_at


def soft_delete_persona_tree(
    db: Session, persona: Persona, deleted_at: datetime
) -> list[str | None]:
    storage_urls: list[str | None] = []
    mark_deleted(persona, deleted_at)
    db.add(persona)

    persona_scoped_models = [
        SourceMaterial,
        ParsedChunk,
        MemoryCard,
        PersonaProfile,
        Conversation,
        VoiceModel,
        AvatarModel,
        AIJob,
        MemoryStory,
    ]
    for model in persona_scoped_models:
        rows = db.scalars(
            select(model).where(
                model.persona_id == persona.id,
                model.deleted_at.is_(None),
            )
        ).all()
        for row in rows:
            if isinstance(row, SourceMaterial):
                storage_urls.append(row.storage_url)
            mark_deleted(row, deleted_at)
            db.add(row)

    conversation_ids = db.scalars(
        select(Conversation.id).where(Conversation.persona_id == persona.id)
    ).all()
    if not conversation_ids:
        return storage_urls

    messages = db.scalars(
        select(Message).where(
            Message.conversation_id.in_(conversation_ids),
            Message.deleted_at.is_(None),
        )
    ).all()
    message_ids: list[str] = []
    for message in messages:
        message_ids.append(message.id)
        mark_deleted(message, deleted_at)
        db.add(message)

    if not message_ids:
        return storage_urls

    citations = db.scalars(
        select(MessageCitation).where(
            MessageCitation.message_id.in_(message_ids),
            MessageCitation.deleted_at.is_(None),
        )
    ).all()
    for citation in citations:
        mark_deleted(citation, deleted_at)
        db.add(citation)
    return storage_urls


def clear_user_domain_data(db: Session, user: User, deleted_at: datetime) -> list[str | None]:
    storage_urls: list[str | None] = []
    personas = db.scalars(select(Persona).where(Persona.user_id == user.id)).all()
    for persona in personas:
        storage_urls.extend(soft_delete_persona_tree(db, persona, deleted_at))

    orphan_jobs = db.scalars(
        select(AIJob).where(
            AIJob.user_id == user.id,
            AIJob.persona_id.is_(None),
            AIJob.deleted_at.is_(None),
        )
    ).all()
    for job in orphan_jobs:
        mark_deleted(job, deleted_at)
        db.add(job)
    return storage_urls
