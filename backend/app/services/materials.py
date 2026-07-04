from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_job import AIJob
from app.models.persona import Persona
from app.models.source_material import SourceMaterial
from app.models.user import User, uuid_str
from app.schemas.job import AIJobRead
from app.schemas.material import MaterialRead
from app.services.parsing import run_parse_job


TEXT_EXTENSIONS = {".txt", ".md", ".pdf", ".doc", ".docx"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
JOB_TYPES = {
    "manual": "parse_text",
    "text": "parse_text",
    "image": "ocr_image",
    "audio": "asr_audio",
    "video": "extract_video_audio",
}


def get_persona_or_404(persona_id: str, user: User, db: Session) -> Persona:
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


def get_material_or_404(material_id: str, user: User, db: Session) -> SourceMaterial:
    material = db.scalar(
        select(SourceMaterial).where(
            SourceMaterial.id == material_id,
            SourceMaterial.user_id == user.id,
            SourceMaterial.deleted_at.is_(None),
        )
    )
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return material


def infer_file_type(file_name: str | None, mime_type: str | None) -> str:
    suffix = Path(file_name or "").suffix.lower()
    normalized_mime = (mime_type or "").lower()
    if normalized_mime.startswith("text/") or suffix in TEXT_EXTENSIONS:
        return "text"
    if normalized_mime.startswith("image/") or suffix in IMAGE_EXTENSIONS:
        return "image"
    if normalized_mime.startswith("audio/") or suffix in AUDIO_EXTENSIONS:
        return "audio"
    if normalized_mime.startswith("video/") or suffix in VIDEO_EXTENSIONS:
        return "video"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported material file type",
    )


def create_parse_job(db: Session, material: SourceMaterial) -> AIJob:
    job = AIJob(
        user_id=material.user_id,
        persona_id=material.persona_id,
        source_material_id=material.id,
        job_type=JOB_TYPES[material.file_type],
        status="pending",
        input_json={"source_material_id": material.id, "file_type": material.file_type},
    )
    db.add(job)
    return job


def create_manual_material(
    db: Session,
    user: User,
    persona: Persona,
    *,
    manual_text: str,
    importance: str,
    user_description: str | None,
    material_time: datetime | None,
    people_tags: dict | list | None,
    location_hint: str | None,
) -> tuple[SourceMaterial, AIJob]:
    material = SourceMaterial(
        user_id=user.id,
        persona_id=persona.id,
        file_type="manual",
        manual_text=manual_text,
        importance=importance,
        user_description=user_description,
        material_time=material_time,
        people_tags=people_tags,
        location_hint=location_hint,
        parse_status="pending",
    )
    db.add(material)
    db.flush()
    job = create_parse_job(db, material)
    db.flush()
    run_parse_job(db, material, job)
    db.commit()
    db.refresh(material)
    db.refresh(job)
    return material, job


def create_uploaded_material(
    db: Session,
    user: User,
    persona: Persona,
    *,
    file_name: str,
    mime_type: str | None,
    content: bytes,
    importance: str,
    user_description: str | None,
) -> tuple[SourceMaterial, AIJob]:
    file_type = infer_file_type(file_name, mime_type)
    material_id = uuid_str()
    storage_url = _write_local_material(
        user_id=user.id,
        persona_id=persona.id,
        material_id=material_id,
        file_name=file_name,
        content=content,
    )
    material = SourceMaterial(
        id=material_id,
        user_id=user.id,
        persona_id=persona.id,
        file_name=file_name,
        file_type=file_type,
        mime_type=mime_type,
        file_size=len(content),
        storage_url=storage_url,
        importance=importance,
        user_description=user_description,
        parse_status="pending",
    )
    db.add(material)
    db.flush()
    job = create_parse_job(db, material)
    db.flush()
    run_parse_job(db, material, job)
    db.commit()
    db.refresh(material)
    db.refresh(job)
    return material, job


def queue_material_parse(
    db: Session,
    material: SourceMaterial,
) -> AIJob:
    job = create_parse_job(db, material)
    db.flush()
    run_parse_job(db, material, job)
    db.commit()
    db.refresh(job)
    return job


def soft_delete_material(db: Session, material: SourceMaterial) -> None:
    material.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    db.add(material)
    db.commit()


def material_response(material: SourceMaterial, jobs: list[AIJob]) -> MaterialRead:
    return MaterialRead(
        id=material.id,
        persona_id=material.persona_id,
        file_name=material.file_name,
        file_type=material.file_type,
        mime_type=material.mime_type,
        file_size=material.file_size,
        storage_url=material.storage_url,
        manual_text=material.manual_text,
        user_description=material.user_description,
        material_time=material.material_time,
        people_tags=material.people_tags,
        location_hint=material.location_hint,
        importance=material.importance,
        parse_status=material.parse_status,
        created_at=material.created_at,
        updated_at=material.updated_at,
        jobs=[AIJobRead.model_validate(job) for job in jobs],
    )


def material_with_jobs(db: Session, material: SourceMaterial) -> MaterialRead:
    jobs = db.scalars(
        select(AIJob)
        .where(
            AIJob.user_id == material.user_id,
            AIJob.source_material_id == material.id,
        )
        .order_by(AIJob.created_at.desc(), AIJob.id.desc())
    ).all()
    return material_response(material, jobs)


def _write_local_material(
    *,
    user_id: str,
    persona_id: str,
    material_id: str,
    file_name: str,
    content: bytes,
) -> str:
    storage_dir = Path("storage") / "materials" / user_id / persona_id
    storage_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_file_name(file_name)
    path = storage_dir / f"{material_id}-{safe_name}"
    path.write_bytes(content)
    return path.as_posix()


def _safe_file_name(file_name: str) -> str:
    base_name = file_name.replace("\\", "/").split("/")[-1].strip()
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", base_name).strip("._")
    return safe_name or "upload"
