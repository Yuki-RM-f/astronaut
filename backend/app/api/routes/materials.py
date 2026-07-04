from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.source_material import SourceMaterial
from app.models.user import User
from app.schemas.job import AIJobRead
from app.schemas.material import (
    AllowedImportance,
    ManualMaterialCreate,
    MaterialListResponse,
    MaterialRead,
)
from app.services.materials import (
    create_manual_material,
    create_uploaded_material,
    get_material_or_404,
    get_persona_or_404,
    infer_file_type,
    material_with_jobs,
    queue_material_parse,
    soft_delete_material,
)


router = APIRouter(tags=["materials"])


@router.post(
    "/personas/{persona_id}/materials/upload",
    response_model=MaterialListResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_materials(
    persona_id: str,
    files: list[UploadFile] = File(...),
    importance: AllowedImportance = Form("normal"),
    user_description: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    for uploaded_file in files:
        infer_file_type(uploaded_file.filename, uploaded_file.content_type)

    items: list[MaterialRead] = []
    for uploaded_file in files:
        content = await uploaded_file.read()
        material, _job = create_uploaded_material(
            db,
            current_user,
            persona,
            file_name=uploaded_file.filename or "upload",
            mime_type=uploaded_file.content_type,
            content=content,
            importance=importance,
            user_description=user_description,
        )
        items.append(material_with_jobs(db, material))
    return MaterialListResponse(items=items)


@router.post(
    "/personas/{persona_id}/materials/manual",
    response_model=MaterialRead,
    status_code=status.HTTP_201_CREATED,
)
def create_manual(
    persona_id: str,
    payload: ManualMaterialCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    material, _job = create_manual_material(
        db,
        current_user,
        persona,
        manual_text=payload.manual_text,
        importance=payload.importance,
        user_description=payload.user_description,
        material_time=payload.material_time,
        people_tags=payload.people_tags,
        location_hint=payload.location_hint,
    )
    return material_with_jobs(db, material)


@router.get("/personas/{persona_id}/materials", response_model=MaterialListResponse)
def list_materials(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    materials = db.scalars(
        select(SourceMaterial)
        .where(
            SourceMaterial.user_id == current_user.id,
            SourceMaterial.persona_id == persona.id,
            SourceMaterial.deleted_at.is_(None),
        )
        .order_by(SourceMaterial.created_at.desc(), SourceMaterial.id.desc())
    ).all()
    return MaterialListResponse(
        items=[material_with_jobs(db, material) for material in materials]
    )


@router.get("/materials/{material_id}", response_model=MaterialRead)
def get_material(
    material_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    material = get_material_or_404(material_id, current_user, db)
    return material_with_jobs(db, material)


@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    material_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    material = get_material_or_404(material_id, current_user, db)
    soft_delete_material(db, material)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/materials/{material_id}/parse",
    response_model=AIJobRead,
    status_code=status.HTTP_201_CREATED,
)
def parse_material(
    material_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    material = get_material_or_404(material_id, current_user, db)
    return queue_material_parse(db, material)
