from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.memory_card import MemoryCard
from app.models.persona import Persona
from app.models.persona_profile import PersonaProfile
from app.models.source_material import SourceMaterial
from app.models.user import User
from app.schemas.persona import (
    PersonaCreate,
    PersonaListResponse,
    PersonaRead,
    PersonaStats,
    PersonaUpdate,
)
from app.services.data_management import soft_delete_persona_tree, utcnow_naive
from app.services.avatar import remove_local_avatar_model_files_for_persona
from app.services.material_storage import remove_local_material_files
from app.services.memory_markdown import remove_memory_context_files
from app.services.persona_prompt import build_persona_prompt_context


router = APIRouter(prefix="/personas", tags=["personas"])


def _get_persona_or_404(persona_id: str, user: User, db: Session) -> Persona:
    persona = db.scalar(
        select(Persona).where(
            Persona.id == persona_id,
            Persona.user_id == user.id,
            Persona.deleted_at.is_(None),
        )
    )
    if persona is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return persona


def _count(db: Session, statement) -> int:
    return int(db.scalar(statement) or 0)


def _persona_stats(persona: Persona, user: User, db: Session) -> PersonaStats:
    return PersonaStats(
        materials_count=_count(
            db,
            select(func.count(SourceMaterial.id)).where(
                SourceMaterial.persona_id == persona.id,
                SourceMaterial.user_id == user.id,
                SourceMaterial.deleted_at.is_(None),
            ),
        ),
        memories_count=_count(
            db,
            select(func.count(MemoryCard.id)).where(
                MemoryCard.persona_id == persona.id,
                MemoryCard.deleted_at.is_(None),
            ),
        ),
        conversations_count=_count(
            db,
            select(func.count(Conversation.id)).where(
                Conversation.persona_id == persona.id,
                Conversation.user_id == user.id,
                Conversation.deleted_at.is_(None),
            ),
        ),
    )


def _persona_profile(persona: Persona, db: Session) -> PersonaProfile | None:
    return db.scalar(select(PersonaProfile).where(PersonaProfile.persona_id == persona.id))


def _persona_response(persona: Persona, user: User, db: Session) -> PersonaRead:
    profile = _persona_profile(persona, db)
    return PersonaRead(
        id=persona.id,
        name=persona.name,
        persona_type=persona.persona_type,
        status=persona.status,
        relationship_to_user=persona.relationship_to_user,
        user_nickname_by_persona=persona.user_nickname_by_persona,
        age=persona.age,
        gender=persona.gender,
        language=persona.language,
        birth_date=persona.birth_date,
        death_date=persona.death_date,
        short_bio=persona.short_bio,
        speaking_style=persona.speaking_style,
        emotional_style=persona.emotional_style,
        forbidden_expressions=persona.forbidden_expressions,
        avatar_image_url=persona.avatar_image_url,
        trust_score=persona.trust_score,
        stats=_persona_stats(persona, user, db),
        prompt_context=build_persona_prompt_context(persona, profile),
    )


@router.get("", response_model=PersonaListResponse)
def list_personas(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    personas = db.scalars(
        select(Persona)
        .where(Persona.user_id == current_user.id, Persona.deleted_at.is_(None))
        .order_by(Persona.created_at.desc(), Persona.id.desc())
    ).all()
    return PersonaListResponse(
        items=[_persona_response(persona, current_user, db) for persona in personas]
    )


@router.post("", response_model=PersonaRead, status_code=status.HTTP_201_CREATED)
def create_persona(
    payload: PersonaCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = Persona(user_id=current_user.id, **payload.model_dump())
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return _persona_response(persona, current_user, db)


@router.get("/{persona_id}", response_model=PersonaRead)
def get_persona(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = _get_persona_or_404(persona_id, current_user, db)
    return _persona_response(persona, current_user, db)


@router.patch("/{persona_id}", response_model=PersonaRead)
def update_persona(
    persona_id: str,
    payload: PersonaUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = _get_persona_or_404(persona_id, current_user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(persona, field, value)
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return _persona_response(persona, current_user, db)


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = _get_persona_or_404(persona_id, current_user, db)
    storage_urls = soft_delete_persona_tree(db, persona, utcnow_naive())
    db.commit()
    remove_local_material_files(storage_urls)
    remove_local_avatar_model_files_for_persona(current_user.id, persona.id)
    remove_memory_context_files(persona.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
