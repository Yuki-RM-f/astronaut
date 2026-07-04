from __future__ import annotations

import asyncio
import threading
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_job import AIJob
from app.models.persona import Persona
from app.models.source_material import SourceMaterial
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


def _avatar_status(selected: AvatarModel | None) -> AvatarStatus:
    if selected is None:
        return "no_avatar"
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
