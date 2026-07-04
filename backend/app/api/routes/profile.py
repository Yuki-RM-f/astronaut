from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.profile import PersonaProfileRead, PersonaProfileUpdate
from app.services.materials import get_persona_or_404
from app.services.profile import (
    calculate_trust_report,
    get_or_create_profile,
    mark_manual_overrides,
    profile_response,
    record_profile_job,
    regenerate_with_persona_engine,
    refresh_profile_and_trust,
)
from app.services.audit import snapshot_entity, write_audit_event


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
    return profile_response(profile, report, persona)


@router.patch("/personas/{persona_id}/profile", response_model=PersonaProfileRead)
def update_profile(
    persona_id: str,
    payload: PersonaProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    profile = get_or_create_profile(db, persona)
    before_profile = snapshot_entity(profile)
    previous_trust = persona.trust_score
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(profile, field, value)
    mark_manual_overrides(profile, set(updates))
    report = calculate_trust_report(db, persona)
    persona.trust_score = report.trust_score
    db.add_all([persona, profile])
    db.flush()
    write_audit_event(
        db,
        user_id=current_user.id,
        persona_id=persona.id,
        target_type="profile",
        target_id=profile.id,
        event_type="profile.field_edited",
        action="手动编辑人格画像字段",
        before_snapshot=before_profile,
        after_snapshot=snapshot_entity(profile),
        metadata_json={"fields": sorted(updates.keys())},
    )
    _write_trust_changed_if_needed(
        db,
        current_user.id,
        persona.id,
        previous_trust,
        report.trust_score,
    )
    db.commit()
    db.refresh(profile)
    return profile_response(profile, report, persona)


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
    previous_trust = persona.trust_score
    profile, report, job_extra = regenerate_with_persona_engine(db, persona)
    write_audit_event(
        db,
        user_id=current_user.id,
        persona_id=persona.id,
        target_type="profile",
        target_id=profile.id,
        event_type="profile.regenerated",
        action="显式重生成人格画像",
        after_snapshot=snapshot_entity(profile),
        metadata_json=job_extra,
    )
    _write_trust_changed_if_needed(
        db,
        current_user.id,
        persona.id,
        previous_trust,
        report.trust_score,
    )
    db.commit()
    db.refresh(profile)
    return profile_response(profile, report, persona)


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
    previous_trust = persona.trust_score
    report = refresh_profile_and_trust(db, persona)
    record_profile_job(db, persona, "calculate_trust_score", report)
    _write_trust_changed_if_needed(
        db,
        current_user.id,
        persona.id,
        previous_trust,
        report.trust_score,
    )
    db.commit()
    db.refresh(profile)
    return profile_response(profile, report, persona)


def _write_trust_changed_if_needed(
    db: Session,
    user_id: str,
    persona_id: str,
    before_score: int | None,
    after_score: int | None,
) -> None:
    if before_score == after_score:
        return
    write_audit_event(
        db,
        user_id=user_id,
        persona_id=persona_id,
        target_type="profile",
        target_id=persona_id,
        event_type="trust.changed",
        action="可信度分数变化",
        severity="info",
        changed_fields=["trust_score"],
        before_snapshot={"trust_score": before_score},
        after_snapshot={"trust_score": after_score},
    )
