from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.ai_job import AIJob
from app.models.user import User
from app.schemas.job import AIJobListResponse, AIJobRead
from app.services.materials import get_persona_or_404


router = APIRouter(tags=["jobs"])

CANCELABLE_STATUSES = {"pending", "running", "retrying"}


def _get_job_or_404(job_id: str, user: User, db: Session) -> AIJob:
    job = db.scalar(
        select(AIJob).where(
            AIJob.id == job_id,
            AIJob.user_id == user.id,
            AIJob.deleted_at.is_(None),
        )
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return job


@router.get("/personas/{persona_id}/jobs", response_model=AIJobListResponse)
def list_jobs(
    persona_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona = get_persona_or_404(persona_id, current_user, db)
    jobs = db.scalars(
        select(AIJob)
        .where(
            AIJob.user_id == current_user.id,
            AIJob.persona_id == persona.id,
            AIJob.deleted_at.is_(None),
        )
        .order_by(AIJob.created_at.desc(), AIJob.id.desc())
    ).all()
    return AIJobListResponse(items=[AIJobRead.model_validate(job) for job in jobs])


@router.get("/jobs/{job_id}", response_model=AIJobRead)
def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_job_or_404(job_id, current_user, db)


@router.post("/jobs/{job_id}/retry", response_model=AIJobRead)
def retry_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = _get_job_or_404(job_id, current_user, db)
    if job.status == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot retry a running job",
        )
    job.status = "retrying"
    job.retry_count += 1
    job.error_message = None
    job.started_at = None
    job.finished_at = None
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/{job_id}/cancel", response_model=AIJobRead)
def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = _get_job_or_404(job_id, current_user, db)
    if job.status not in CANCELABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel job with status {job.status}",
        )
    job.status = "canceled"
    job.finished_at = datetime.now(UTC).replace(tzinfo=None)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
