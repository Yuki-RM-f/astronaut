from __future__ import annotations

import asyncio
import re
import shutil
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_job import AIJob
from app.models.persona import Persona
from app.models.source_material import SourceMaterial
from app.models.user import User, uuid_str
from app.models.voice_avatar import AvatarModel
from app.providers.gateway import ProviderGateway
from app.schemas.avatar import (
    AvatarConfigResponse,
    AvatarGenerateCreate,
    AvatarGenerateResponse,
    AvatarModelRead,
    AvatarStatus,
    AvatarStyle,
    DefaultAvatarSelection,
)
from app.schemas.job import AIJobRead


AVATAR_FAILURE_NOTICE = (
    "这张照片暂时没有生成成功。你可以换一张更清晰的正脸照，或者先使用默认纪念形象继续对话。"
)
AVATAR_STYLE_OPTIONS: list[AvatarStyle] = ["semi_realistic", "cartoon", "memorial"]
LOCAL_AVATAR_MODELS_ROOT = Path("storage") / "avatar_models"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_avatar_config(db: Session, persona: Persona) -> AvatarConfigResponse:
    selected = get_selected_avatar_model(db, persona)
    return _avatar_config_response(persona, selected, list_avatar_models(db, persona))


def select_default_avatar(
    db: Session,
    persona: Persona,
    payload: DefaultAvatarSelection,
) -> AvatarConfigResponse:
    model = _create_default_avatar_model(db, persona, payload.style)
    db.commit()
    db.refresh(model)
    return _avatar_config_response(persona, model, list_avatar_models(db, persona))


def upload_avatar_model(
    db: Session,
    persona: Persona,
    *,
    file_name: str,
    content: bytes,
) -> AvatarConfigResponse:
    if not file_name.lower().endswith(".glb"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar model upload requires a .glb file",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar model upload cannot be empty",
        )

    _clear_selected_avatar_models(db, persona)
    model_id = uuid_str()
    model = AvatarModel(
        id=model_id,
        persona_id=persona.id,
        provider_type="user_upload",
        provider_name="glb_upload",
        status="uploaded_ready",
        model_url=f"/api/avatar-models/{model_id}/file",
        format="glb",
        user_selected=True,
    )
    db.add(model)
    _write_local_avatar_model(
        user_id=persona.user_id,
        persona_id=persona.id,
        avatar_model_id=model_id,
        file_name=file_name,
        content=content,
    )
    db.commit()
    db.refresh(model)
    return _avatar_config_response(persona, model, list_avatar_models(db, persona))


def generate_avatar(
    db: Session,
    persona: Persona,
    payload: AvatarGenerateCreate,
) -> AvatarGenerateResponse:
    material = _get_owned_image_material_or_404(db, persona, payload.source_image_material_id)
    provider_payload = {
        "persona_id": persona.id,
        "persona_name": persona.name,
        "source_image_material_id": material.id,
        "file_name": material.file_name,
        "storage_url": material.storage_url,
        "user_description": material.user_description,
        "style": payload.style,
        "simulate_failure": payload.simulate_failure,
    }
    job = _create_running_job(
        persona=persona,
        job_type="avatar_3d",
        provider_name="mock_avatar_3d",
        input_json=provider_payload,
        source_material_id=material.id,
    )
    db.add(job)
    db.flush()

    result = _run_gateway("avatar_3d", {**provider_payload, "job_id": job.id})
    output = result["output"]
    if output["generation_status"] == "failed":
        avatar_model = AvatarModel(
            persona_id=persona.id,
            provider_type="local",
            provider_name="mock_avatar_3d",
            status="generation_failed",
            source_image_material_id=material.id,
            style=payload.style,
            user_selected=False,
        )
        db.add(avatar_model)
        job.status = "failed"
        job.error_message = output["error_message"]
        selected = _create_default_avatar_model(db, persona, "memorial")
        db.flush()
        avatar_status: AvatarStatus = "default_avatar"
    else:
        _clear_selected_avatar_models(db, persona)
        avatar_model = AvatarModel(
            persona_id=persona.id,
            provider_type="local",
            provider_name="mock_avatar_3d",
            status="generated_ready",
            source_image_material_id=material.id,
            style=payload.style,
            model_url=output["model_url"],
            preview_image_url=output["preview_image_url"],
            format=output["format"],
            expression_config_json=output["expression_config_json"],
            animation_config_json=output["animation_config_json"],
            lip_sync_config_json=output["lip_sync_config_json"],
            user_selected=True,
        )
        db.add(avatar_model)
        selected = avatar_model
        job.status = "succeeded"
        avatar_status = "generated_ready"

    job.output_json = result
    job.finished_at = _utcnow()
    db.add(job)
    db.commit()
    db.refresh(avatar_model)
    db.refresh(selected)
    db.refresh(job)
    return AvatarGenerateResponse(
        avatar_status=avatar_status,
        avatar_model=AvatarModelRead.model_validate(avatar_model),
        selected_avatar_model=AvatarModelRead.model_validate(selected),
        failure_notice=AVATAR_FAILURE_NOTICE,
        provider=_provider_summary(result),
        job=AIJobRead.model_validate(job),
    )


def get_selected_avatar_model(db: Session, persona: Persona) -> AvatarModel | None:
    return db.scalar(
        select(AvatarModel)
        .where(AvatarModel.persona_id == persona.id, AvatarModel.user_selected.is_(True))
        .order_by(AvatarModel.updated_at.desc(), AvatarModel.id.desc())
    )


def list_avatar_models(db: Session, persona: Persona) -> list[AvatarModel]:
    return db.scalars(
        select(AvatarModel)
        .where(AvatarModel.persona_id == persona.id)
        .order_by(AvatarModel.created_at.asc(), AvatarModel.id.asc())
    ).all()


def get_avatar_model_file_path(
    db: Session,
    current_user: User,
    avatar_model_id: str,
) -> Path:
    row = db.execute(
        select(AvatarModel, Persona)
        .join(Persona, AvatarModel.persona_id == Persona.id)
        .where(
            AvatarModel.id == avatar_model_id,
            AvatarModel.deleted_at.is_(None),
            Persona.user_id == current_user.id,
            Persona.deleted_at.is_(None),
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    model, persona = row
    path = _find_local_avatar_model_file(
        user_id=persona.user_id,
        persona_id=persona.id,
        avatar_model_id=model.id,
    )
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return path


def remove_local_avatar_model_files_for_persona(user_id: str, persona_id: str) -> None:
    persona_dir = _avatar_persona_dir(user_id=user_id, persona_id=persona_id)
    try:
        root = LOCAL_AVATAR_MODELS_ROOT.resolve(strict=False)
        resolved = persona_dir.resolve(strict=False)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return
    if persona_dir.exists():
        shutil.rmtree(persona_dir, ignore_errors=True)


def _avatar_status(selected: AvatarModel | None) -> AvatarStatus:
    if selected is None:
        return "no_avatar"
    if selected.status == "uploaded_ready":
        return "uploaded_ready"
    if selected.status == "generated_ready":
        return "generated_ready"
    return "default_avatar"


def _avatar_config_response(
    persona: Persona,
    selected: AvatarModel | None,
    avatar_models: list[AvatarModel] | None = None,
) -> AvatarConfigResponse:
    return AvatarConfigResponse(
        persona_id=persona.id,
        avatar_status=_avatar_status(selected),
        selected_avatar_model=(
            AvatarModelRead.model_validate(selected) if selected is not None else None
        ),
        avatar_models=[
            AvatarModelRead.model_validate(model) for model in (avatar_models or [])
        ],
        style_options=AVATAR_STYLE_OPTIONS,
        failure_notice=AVATAR_FAILURE_NOTICE,
    )


def _create_default_avatar_model(
    db: Session,
    persona: Persona,
    style: AvatarStyle,
) -> AvatarModel:
    _clear_selected_avatar_models(db, persona)
    model = AvatarModel(
        persona_id=persona.id,
        provider_type="local",
        provider_name="mock_default_avatar",
        status="default_avatar",
        style=style,
        model_url=f"mock://avatar/default/{style}.glb",
        preview_image_url=f"mock://avatar/default/{style}.png",
        format="glb",
        expression_config_json=_expression_config(),
        animation_config_json=_animation_config(),
        lip_sync_config_json=_lip_sync_config(),
        user_selected=True,
    )
    db.add(model)
    return model


def _write_local_avatar_model(
    *,
    user_id: str,
    persona_id: str,
    avatar_model_id: str,
    file_name: str,
    content: bytes,
) -> Path:
    storage_dir = _avatar_persona_dir(user_id=user_id, persona_id=persona_id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    path = storage_dir / f"{avatar_model_id}-{_safe_file_name(file_name)}"
    path.write_bytes(content)
    return path


def _find_local_avatar_model_file(
    *,
    user_id: str,
    persona_id: str,
    avatar_model_id: str,
) -> Path | None:
    storage_dir = _avatar_persona_dir(user_id=user_id, persona_id=persona_id)
    if not storage_dir.is_dir():
        return None
    matches = sorted(storage_dir.glob(f"{avatar_model_id}-*.glb"))
    if not matches:
        return None
    path = matches[0]
    try:
        root = LOCAL_AVATAR_MODELS_ROOT.resolve(strict=False)
        resolved = path.resolve(strict=False)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return None
    return path if path.is_file() else None


def _avatar_persona_dir(*, user_id: str, persona_id: str) -> Path:
    return LOCAL_AVATAR_MODELS_ROOT / user_id / persona_id


def _safe_file_name(file_name: str) -> str:
    base_name = file_name.replace("\\", "/").split("/")[-1].strip()
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", base_name).strip("._")
    if not safe_name.lower().endswith(".glb"):
        safe_name = f"{safe_name or 'avatar'}.glb"
    return safe_name


def _clear_selected_avatar_models(db: Session, persona: Persona) -> None:
    selected_models = db.scalars(
        select(AvatarModel).where(
            AvatarModel.persona_id == persona.id,
            AvatarModel.user_selected.is_(True),
        )
    ).all()
    for model in selected_models:
        model.user_selected = False
        db.add(model)


def _get_owned_image_material_or_404(
    db: Session,
    persona: Persona,
    material_id: str,
) -> SourceMaterial:
    material = db.scalar(
        select(SourceMaterial).where(
            SourceMaterial.id == material_id,
            SourceMaterial.user_id == persona.user_id,
            SourceMaterial.persona_id == persona.id,
            SourceMaterial.deleted_at.is_(None),
        )
    )
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if material.file_type != "image":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar generation requires an image source material",
        )
    return material


def _create_running_job(
    *,
    persona: Persona,
    job_type: str,
    provider_name: str,
    input_json: dict[str, Any],
    source_material_id: str | None = None,
) -> AIJob:
    return AIJob(
        user_id=persona.user_id,
        persona_id=persona.id,
        source_material_id=source_material_id,
        job_type=job_type,
        provider_type="local",
        provider_name=provider_name,
        status="running",
        input_json=input_json,
        started_at=_utcnow(),
    )


def _expression_config() -> dict[str, bool]:
    return {
        "blink": True,
        "smile": True,
        "nod": True,
        "comfort": True,
    }


def _animation_config() -> dict[str, bool]:
    return {
        "idle_breath": True,
        "blink": True,
        "nod": True,
        "smile": True,
        "listen": True,
    }


def _lip_sync_config() -> dict[str, str | int]:
    return {
        "mode": "audio_envelope",
        "mouth_open_blendshape": "aa",
        "sample_rate_ms": 80,
    }


def _provider_summary(result: dict[str, Any]) -> dict[str, str]:
    return {
        "provider_name": str(result["provider_name"]),
        "capability": str(result["capability"]),
        "status": str(result["status"]),
    }


def _run_gateway(capability: str, payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] | None = None

    def runner() -> None:
        nonlocal result
        result = asyncio.run(ProviderGateway().run(capability, payload))

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()
    if result is None:
        raise RuntimeError("Provider gateway did not return a result")
    return result
