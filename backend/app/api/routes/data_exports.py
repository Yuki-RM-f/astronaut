from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.data_export import (
    ConversationExportResponse,
    PersonaMemoriesExportResponse,
    PersonaProfileExportResponse,
)
from app.services.data_exports import (
    export_conversation,
    export_persona_memories,
    export_persona_profile,
)


router = APIRouter(tags=["exports"])


@router.get(
    "/personas/{persona_id}/export/profile",
    response_model=PersonaProfileExportResponse,
)
def export_profile(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return export_persona_profile(db, current_user, persona_id)


@router.get(
    "/personas/{persona_id}/export/memories",
    response_model=PersonaMemoriesExportResponse,
)
def export_memories(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return export_persona_memories(db, current_user, persona_id)


@router.get(
    "/conversations/{conversation_id}/export",
    response_model=ConversationExportResponse,
)
def export_chat_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return export_conversation(db, current_user, conversation_id)
