from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.guided_memory import (
    GuidedMemoryCandidateResponse,
    GuidedMemoryCandidatesCreate,
)
from app.services.guided_memory import extract_guided_memory_candidates
from app.services.materials import get_persona_or_404


router = APIRouter(tags=["guided-memory"])


@router.post(
    "/personas/{persona_id}/guided-memory-candidates",
    response_model=GuidedMemoryCandidateResponse,
)
def guided_memory_candidates(
    persona_id: str,
    payload: GuidedMemoryCandidatesCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    return extract_guided_memory_candidates(db, persona, payload.kind)
