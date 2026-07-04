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
from app.models.voice_avatar import VoiceModel
from app.providers.gateway import ProviderGateway
from app.schemas.job import AIJobRead
from app.schemas.voice import (
    DefaultTTSSelection,
    VoiceCloneCreate,
    VoiceCloneResponse,
    SpeechSynthesisCreate,
    SpeechSynthesisResponse,
    VoiceConfigResponse,
    VoiceModelRead,
    VoiceSampleCreate,
    VoiceSampleResponse,
    VoiceStatus,
)


DEFAULT_TTS_NOTICE = (
    "当前使用系统默认声音，不是 TA 的真实声音。上传 TA 的清晰语音后，可以尝试生成模拟音色。"
)
DEFAULT_TTS_OPTIONS = {
    "gender": ["male", "female", "neutral"],
    "age_style": ["young", "middle_aged", "elderly"],
    "style": ["gentle", "calm", "lively", "kind", "low"],
    "speed": ["slow", "normal", "fast"],
    "emotion": ["calm", "comfort", "encourage", "nostalgia"],
}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_selected_voice_model(db: Session, persona: Persona) -> VoiceModel | None:
    return db.scalar(
        select(VoiceModel)
        .where(VoiceModel.persona_id == persona.id, VoiceModel.user_selected.is_(True))
        .order_by(VoiceModel.updated_at.desc(), VoiceModel.id.desc())
    )


def list_voice_models(db: Session, persona: Persona) -> list[VoiceModel]:
    return db.scalars(
        select(VoiceModel)
        .where(VoiceModel.persona_id == persona.id)
        .order_by(VoiceModel.created_at.asc(), VoiceModel.id.asc())
    ).all()


def get_voice_config(db: Session, persona: Persona) -> VoiceConfigResponse:
    selected = get_selected_voice_model(db, persona)
    return _voice_config_response(persona, selected, list_voice_models(db, persona))


def select_default_tts(
    db: Session,
    persona: Persona,
    payload: DefaultTTSSelection,
) -> VoiceConfigResponse:
    model = _create_default_tts_model(db, persona, payload)
    db.commit()
    db.refresh(model)
    return _voice_config_response(persona, model)


def synthesize_speech(
    db: Session,
    persona: Persona,
    payload: SpeechSynthesisCreate,
) -> SpeechSynthesisResponse:
    selected = get_selected_voice_model(db, persona)
    if selected is None:
        selected = _create_default_tts_model(db, persona, DefaultTTSSelection())
        db.flush()

    voice_status = _voice_status(selected)
    provider_payload = {
        "persona_id": persona.id,
        "persona_name": persona.name,
        "text": payload.text,
        "voice_model_id": selected.id,
        "voice_status": voice_status,
        "provider_name": selected.provider_name or "mock_default_tts",
        "default_tts_notice": DEFAULT_TTS_NOTICE,
    }
    job = AIJob(
        user_id=persona.user_id,
        persona_id=persona.id,
        job_type="synthesize_speech",
        provider_type=selected.provider_type or "local",
        provider_name="mock_tts",
        status="running",
        input_json=provider_payload,
        started_at=_utcnow(),
    )
    db.add(job)
    db.flush()

    result = _run_gateway("tts", {**provider_payload, "job_id": job.id})
    job.status = "succeeded"
    job.output_json = result
    job.finished_at = _utcnow()
    db.add(job)
    db.commit()
    db.refresh(job)
    db.refresh(selected)

    return SpeechSynthesisResponse(
        audio_url=result["output"]["audio_url"],
        voice_status=voice_status,
        selected_voice_model=VoiceModelRead.model_validate(selected),
        default_tts_notice=DEFAULT_TTS_NOTICE,
        provider={
            "provider_name": result["provider_name"],
            "capability": result["capability"],
            "status": result["status"],
        },
        job=AIJobRead.model_validate(job),
    )


def create_voice_sample(
    db: Session,
    persona: Persona,
    payload: VoiceSampleCreate,
) -> VoiceSampleResponse:
    material = _get_owned_material_or_404(db, persona, payload.source_material_id)
    if material.file_type != "audio":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Voice samples require an audio source material",
        )

    provider_payload = {
        "persona_id": persona.id,
        "source_material_id": material.id,
        "file_name": material.file_name,
        "storage_url": material.storage_url,
        "user_description": material.user_description,
    }
    job = _create_running_job(
        persona=persona,
        job_type="extract_voice_sample",
        provider_name="mock_voice_sample",
        input_json=provider_payload,
        source_material_id=material.id,
    )
    db.add(job)
    db.flush()

    result = _run_gateway("extract_voice_sample", {**provider_payload, "job_id": job.id})
    output = result["output"]
    voice_model = VoiceModel(
        persona_id=persona.id,
        provider_type="local",
        provider_name="mock_voice_sample",
        status="sample_ready",
        reference_audio_asset_id=material.id,
        sample_text=output["sample_text"],
        sample_audio_url=output["sample_audio_url"],
        quality_score=output["quality_score"],
        user_selected=False,
    )
    db.add(voice_model)
    job.status = "succeeded"
    job.output_json = result
    job.finished_at = _utcnow()
    db.add(job)
    db.commit()
    db.refresh(voice_model)
    db.refresh(job)
    return VoiceSampleResponse(
        voice_status="sample_ready",
        voice_model=VoiceModelRead.model_validate(voice_model),
        provider=_provider_summary(result),
        job=AIJobRead.model_validate(job),
    )


def clone_voice(
    db: Session,
    persona: Persona,
    payload: VoiceCloneCreate,
) -> VoiceCloneResponse:
    voice_model = _get_clone_source_model(db, persona, payload.voice_model_id)
    provider_payload = {
        "persona_id": persona.id,
        "voice_model_id": voice_model.id,
        "reference_audio_asset_id": voice_model.reference_audio_asset_id,
        "sample_audio_url": voice_model.sample_audio_url,
        "sample_text": voice_model.sample_text,
        "simulate_failure": payload.simulate_failure,
    }
    job = _create_running_job(
        persona=persona,
        job_type="clone_voice",
        provider_name="mock_voice_clone",
        input_json=provider_payload,
        source_material_id=voice_model.reference_audio_asset_id,
    )
    db.add(job)
    db.flush()

    result = _run_gateway("voice_clone", {**provider_payload, "job_id": job.id})
    output = result["output"]
    if output["clone_status"] == "failed":
        voice_model.status = "clone_failed"
        voice_model.provider_name = "mock_voice_clone"
        voice_model.user_selected = False
        job.status = "failed"
        job.error_message = output["error_message"]
        selected = _create_default_tts_model(db, persona, DefaultTTSSelection())
        db.flush()
        voice_status: VoiceStatus = "default_tts"
    else:
        _clear_selected_voice_models(db, persona)
        voice_model.provider_type = "local"
        voice_model.provider_name = "mock_voice_clone"
        voice_model.status = "cloned_ready"
        voice_model.model_artifact_url = output["model_artifact_url"]
        voice_model.sample_audio_url = output["preview_audio_url"]
        voice_model.quality_score = output["quality_score"]
        voice_model.user_selected = True
        selected = voice_model
        job.status = "succeeded"
        voice_status = "cloned_ready"

    job.output_json = result
    job.finished_at = _utcnow()
    db.add(voice_model)
    db.add(job)
    db.commit()
    db.refresh(voice_model)
    db.refresh(selected)
    db.refresh(job)
    return VoiceCloneResponse(
        voice_status=voice_status,
        voice_model=VoiceModelRead.model_validate(voice_model),
        selected_voice_model=VoiceModelRead.model_validate(selected),
        default_tts_notice=DEFAULT_TTS_NOTICE,
        provider=_provider_summary(result),
        job=AIJobRead.model_validate(job),
    )


def _voice_config_response(
    persona: Persona,
    selected: VoiceModel | None,
    voice_models: list[VoiceModel] | None = None,
) -> VoiceConfigResponse:
    return VoiceConfigResponse(
        persona_id=persona.id,
        voice_status=_voice_status(selected),
        selected_voice_model=(
            VoiceModelRead.model_validate(selected) if selected is not None else None
        ),
        voice_models=[
            VoiceModelRead.model_validate(model) for model in (voice_models or [])
        ],
        default_tts_notice=DEFAULT_TTS_NOTICE,
        default_tts_options=DEFAULT_TTS_OPTIONS,
    )


def _voice_status(selected: VoiceModel | None) -> VoiceStatus:
    if selected is None:
        return "no_voice"
    if selected.status in {
        "default_tts",
        "sample_ready",
        "cloning",
        "cloned_ready",
        "clone_failed",
    }:
        return selected.status
    return "no_voice"


def _create_default_tts_model(
    db: Session,
    persona: Persona,
    payload: DefaultTTSSelection,
) -> VoiceModel:
    _clear_selected_voice_models(db, persona)
    model = VoiceModel(
        persona_id=persona.id,
        provider_type="local",
        provider_name="mock_default_tts",
        status="default_tts",
        sample_text=_default_tts_summary(payload),
        sample_audio_url=None,
        quality_score=None,
        user_selected=True,
    )
    db.add(model)
    return model


def _clear_selected_voice_models(db: Session, persona: Persona) -> None:
    models = db.scalars(
        select(VoiceModel).where(
            VoiceModel.persona_id == persona.id,
            VoiceModel.user_selected.is_(True),
        )
    ).all()
    for model in models:
        model.user_selected = False
        db.add(model)


def _get_owned_material_or_404(
    db: Session,
    persona: Persona,
    source_material_id: str,
) -> SourceMaterial:
    material = db.scalar(
        select(SourceMaterial).where(
            SourceMaterial.id == source_material_id,
            SourceMaterial.user_id == persona.user_id,
            SourceMaterial.persona_id == persona.id,
            SourceMaterial.deleted_at.is_(None),
        )
    )
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return material


def _get_clone_source_model(
    db: Session,
    persona: Persona,
    voice_model_id: str | None,
) -> VoiceModel:
    query = select(VoiceModel).where(
        VoiceModel.persona_id == persona.id,
        VoiceModel.status.in_({"sample_ready", "clone_failed"}),
    )
    if voice_model_id is not None:
        query = query.where(VoiceModel.id == voice_model_id)
    else:
        query = query.order_by(VoiceModel.created_at.desc(), VoiceModel.id.desc())
    voice_model = db.scalar(query)
    if voice_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if voice_model.reference_audio_asset_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Voice clone requires a sample source material",
        )
    return voice_model


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


def _provider_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider_name": result["provider_name"],
        "capability": result["capability"],
        "status": result["status"],
    }


def _default_tts_summary(payload: DefaultTTSSelection) -> str:
    return (
        "default_tts:"
        f"gender={payload.gender};"
        f"age_style={payload.age_style};"
        f"style={payload.style};"
        f"speed={payload.speed};"
        f"emotion={payload.emotion}"
    )


def _run_gateway(capability: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(ProviderGateway().run(capability, payload))

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def run_in_thread() -> None:
        try:
            result["value"] = asyncio.run(ProviderGateway().run(capability, payload))
        except BaseException as exc:  # pragma: no cover - re-raised in caller
            error["value"] = exc

    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()
    if error:
        raise error["value"]
    return result["value"]
