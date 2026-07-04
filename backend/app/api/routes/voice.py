from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.voice import (
    DefaultTTSSelection,
    SpeechSynthesisCreate,
    SpeechSynthesisResponse,
    VoiceCloneCreate,
    VoiceCloneResponse,
    VoiceConfigResponse,
    VoiceSampleCreate,
    VoiceSampleResponse,
)
from app.services.materials import get_persona_or_404
from app.services.voice import (
    clone_voice,
    create_voice_sample,
    get_voice_config,
    select_default_tts,
    synthesize_speech,
)


router = APIRouter(tags=["voice"])


@router.get("/personas/{persona_id}/voice", response_model=VoiceConfigResponse)
def get_persona_voice(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    return get_voice_config(db, persona)


@router.post("/personas/{persona_id}/voice/default-tts", response_model=VoiceConfigResponse)
def set_default_tts(
    persona_id: str,
    payload: DefaultTTSSelection,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    return select_default_tts(db, persona, payload)


@router.post(
    "/personas/{persona_id}/voice/samples",
    response_model=VoiceSampleResponse,
    status_code=201,
)
def create_sample(
    persona_id: str,
    payload: VoiceSampleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    return create_voice_sample(db, persona, payload)


@router.post(
    "/personas/{persona_id}/voice/clone",
    response_model=VoiceCloneResponse,
)
def clone_persona_voice(
    persona_id: str,
    payload: VoiceCloneCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    return clone_voice(db, persona, payload)


@router.post(
    "/personas/{persona_id}/voice/synthesize",
    response_model=SpeechSynthesisResponse,
)
def synthesize_persona_speech(
    persona_id: str,
    payload: SpeechSynthesisCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    return synthesize_speech(db, persona, payload)
