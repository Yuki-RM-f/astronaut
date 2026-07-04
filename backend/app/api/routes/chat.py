from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas.chat import (
    ConversationCreate,
    ConversationListResponse,
    ConversationRead,
    MemoryCorrectionCreate,
    MemoryCorrectionResponse,
    MessageCitationListResponse,
    MessageListResponse,
    MessageRead,
    MessageSend,
    VoiceMessageSend,
)
from app.services.chat import (
    correct_cited_memory,
    get_conversation_or_404,
    get_message_or_404,
    list_message_citations,
    message_response,
    send_text_message,
    send_voice_message,
    soft_delete_conversation,
)
from app.services.materials import get_persona_or_404


router = APIRouter(tags=["chat"])


@router.get(
    "/personas/{persona_id}/conversations",
    response_model=ConversationListResponse,
)
def list_conversations(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    conversations = db.scalars(
        select(Conversation)
        .where(
            Conversation.user_id == current_user.id,
            Conversation.persona_id == persona.id,
            Conversation.deleted_at.is_(None),
        )
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
    ).all()
    return ConversationListResponse(
        items=[
            ConversationRead.model_validate(conversation)
            for conversation in conversations
        ]
    )


@router.post(
    "/personas/{persona_id}/conversations",
    response_model=ConversationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    persona_id: str,
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    conversation = Conversation(
        user_id=current_user.id,
        persona_id=persona.id,
        title=payload.title or f"和 {persona.name} 的对话",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return ConversationRead.model_validate(conversation)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
)
def list_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = get_conversation_or_404(db, current_user, conversation_id)
    messages = db.scalars(
        select(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.deleted_at.is_(None),
        )
        .order_by(Message.created_at.asc(), Message.id.asc())
    ).all()
    return MessageListResponse(items=[message_response(db, message) for message in messages])


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = get_conversation_or_404(db, current_user, conversation_id)
    soft_delete_conversation(db, conversation)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    conversation_id: str,
    payload: MessageSend,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = get_conversation_or_404(db, current_user, conversation_id)
    persona = get_persona_or_404(conversation.persona_id, current_user, db)
    reply = send_text_message(db, conversation, persona, payload.content)
    return message_response(db, reply)


@router.post(
    "/conversations/{conversation_id}/voice-message",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
def send_voice(
    conversation_id: str,
    payload: VoiceMessageSend,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = get_conversation_or_404(db, current_user, conversation_id)
    persona = get_persona_or_404(conversation.persona_id, current_user, db)
    reply = send_voice_message(db, conversation, persona, payload)
    return message_response(db, reply)


@router.get(
    "/messages/{message_id}/citations",
    response_model=MessageCitationListResponse,
)
def get_citations(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = get_message_or_404(db, current_user, message_id)
    return MessageCitationListResponse(
        items=[
            citation
            for citation in list_message_citations(db, message.id)
        ]
    )


@router.post(
    "/messages/{message_id}/correct-memory",
    response_model=MemoryCorrectionResponse,
)
def correct_memory(
    message_id: str,
    payload: MemoryCorrectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = get_message_or_404(db, current_user, message_id)
    return correct_cited_memory(db, current_user, message, payload)
