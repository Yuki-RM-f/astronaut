from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.avatar import (
    AvatarConfigResponse,
    AvatarGenerateCreate,
    AvatarGenerateResponse,
    DefaultAvatarSelection,
)
from app.services.avatar import (
    generate_avatar,
    get_avatar_config,
    select_default_avatar,
)
from app.services.materials import get_persona_or_404


router = APIRouter(tags=["avatar"])


@router.get("/personas/{persona_id}/avatar", response_model=AvatarConfigResponse)
def get_persona_avatar(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    return get_avatar_config(db, persona)


@router.post("/personas/{persona_id}/avatar/default", response_model=AvatarConfigResponse)
def set_default_avatar(
    persona_id: str,
    payload: DefaultAvatarSelection,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    return select_default_avatar(db, persona, payload)


@router.post(
    "/personas/{persona_id}/avatar/generate",
    response_model=AvatarGenerateResponse,
)
def generate_persona_avatar(
    persona_id: str,
    payload: AvatarGenerateCreate,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    result = generate_avatar(db, persona, payload)
    if result.job.status == "succeeded":
        response.status_code = status.HTTP_201_CREATED
    return result
