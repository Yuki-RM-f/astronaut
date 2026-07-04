from __future__ import annotations

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from fastapi.responses import FileResponse
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
    get_avatar_model_file_path,
    get_avatar_config,
    select_default_avatar,
    upload_avatar_model,
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


@router.post(
    "/personas/{persona_id}/avatar/upload",
    response_model=AvatarConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_persona_avatar_model(
    persona_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    content = await file.read()
    return upload_avatar_model(
        db,
        persona,
        file_name=file.filename or "avatar.glb",
        content=content,
    )


@router.get("/avatar-models/{avatar_model_id}/file")
def get_avatar_model_file(
    avatar_model_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    path = get_avatar_model_file_path(db, current_user, avatar_model_id)
    return FileResponse(
        path,
        media_type="model/gltf-binary",
        filename=path.name,
    )
