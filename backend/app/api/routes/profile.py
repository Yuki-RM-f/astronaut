from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.profile import PersonaProfileRead, PersonaProfileUpdate
from app.services.materials import get_persona_or_404
from app.services.profile import (
    build_profile_from_memories,
    calculate_trust_report,
    get_or_create_profile,
    mark_manual_overrides,
    profile_response,
    record_profile_job,
    refresh_profile_and_trust,
)


router = APIRouter(tags=["profile"])


@router.get("/personas/{persona_id}/profile", response_model=PersonaProfileRead)
def get_profile(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    profile = get_or_create_profile(db, persona)
    report = calculate_trust_report(db, persona)
    persona.trust_score = report.trust_score
    db.add(persona)
    db.commit()
    db.refresh(profile)
    return profile_response(profile, report)


@router.patch("/personas/{persona_id}/profile", response_model=PersonaProfileRead)
def update_profile(
    persona_id: str,
    payload: PersonaProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    profile = get_or_create_profile(db, persona)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(profile, field, value)
    mark_manual_overrides(profile, set(updates))
    report = calculate_trust_report(db, persona)
    persona.trust_score = report.trust_score
    db.add_all([persona, profile])
    db.commit()
    db.refresh(profile)
    return profile_response(profile, report)


@router.post(
    "/personas/{persona_id}/profile/regenerate",
    response_model=PersonaProfileRead,
)
def regenerate_profile(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    profile = build_profile_from_memories(db, persona)
    report = calculate_trust_report(db, persona)
    persona.trust_score = report.trust_score
    record_profile_job(db, persona, "update_profile", report)
    db.add(persona)
    db.commit()
    db.refresh(profile)
    return profile_response(profile, report)


@router.post(
    "/personas/{persona_id}/recalculate-trust",
    response_model=PersonaProfileRead,
)
def recalculate_trust(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    profile = get_or_create_profile(db, persona)
    report = refresh_profile_and_trust(db, persona)
    record_profile_job(db, persona, "calculate_trust_score", report)
    db.commit()
    db.refresh(profile)
    return profile_response(profile, report)
