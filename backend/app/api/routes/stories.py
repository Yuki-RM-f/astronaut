from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.story import (
    MemoryStoryCreate,
    MemoryStoryExportResponse,
    MemoryStoryFavoriteUpdate,
    MemoryStoryListResponse,
    MemoryStoryRead,
)
from app.services.materials import get_persona_or_404
from app.services.stories import (
    export_story,
    export_story_audio,
    generate_story,
    list_stories,
    update_story_favorite,
)


router = APIRouter(tags=["stories"])


@router.get("/personas/{persona_id}/stories", response_model=MemoryStoryListResponse)
def get_persona_stories(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    return MemoryStoryListResponse(items=list_stories(db, persona))


@router.post(
    "/personas/{persona_id}/stories",
    response_model=MemoryStoryRead,
    status_code=201,
)
def create_persona_story(
    persona_id: str,
    payload: MemoryStoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    return generate_story(db, persona, payload)


@router.post("/stories/{story_id}/favorite", response_model=MemoryStoryRead)
def favorite_story(
    story_id: str,
    payload: MemoryStoryFavoriteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_story_favorite(db, current_user, story_id, payload)


@router.get(
    "/personas/{persona_id}/export/story/{story_id}",
    response_model=MemoryStoryExportResponse,
)
def export_persona_story(
    persona_id: str,
    story_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    return export_story(db, persona, story_id)


@router.get("/personas/{persona_id}/export/story/{story_id}/audio")
def export_persona_story_audio(
    persona_id: str,
    story_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    filename, content, notice = export_story_audio(db, persona, story_id)
    return Response(
        content=content,
        media_type="audio/wav",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-AI-Simulation-Notice": notice,
        },
    )
