from __future__ import annotations

import asyncio
import threading
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.ai_job import AIJob
from app.models.persona import Persona
from app.models.source_material import SourceMaterial
from app.models.voice_avatar import VoiceModel
from app.providers.gateway import ProviderGateway
from app.schemas.job import AIJobRead
from app.schemas.voice import (
    DEFAULT_MINIMAX_TTS_VOICE_ID,
    DefaultTTSSelection,
    DefaultTTSVoiceRead,
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
MINIMAX_VOICE_CLONE_MIN_SECONDS = 10
DEFAULT_TTS_OPTIONS = {
    "gender": ["male", "female", "neutral"],
    "age_style": ["young", "middle_aged", "elderly"],
    "style": ["gentle", "calm", "lively", "kind", "low"],
    "speed": ["slow", "normal", "fast"],
    "emotion": ["calm", "comfort", "encourage", "nostalgia"],
}
SYSTEM_VOICE_ARTIFACT_PREFIX = "minimax://system-voice/"
CLONED_VOICE_ARTIFACT_PREFIX = "minimax://voice/"
DEFAULT_TTS_VOICES = [
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Reliable_Executive",
        voice_name="可靠高管",
        language="Chinese (Mandarin)",
        description="稳重可靠的普通话男声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_News_Anchor",
        voice_name="新闻主播",
        language="Chinese (Mandarin)",
        description="新闻播报风格的普通话女声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Unrestrained_Young_Man",
        voice_name="洒脱青年",
        language="Chinese (Mandarin)",
        description="松弛外放的年轻男声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Mature_Woman",
        voice_name="成熟女性",
        language="Chinese (Mandarin)",
        description="成熟稳重的普通话女声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Arrogant_Miss",
        voice_name="傲娇小姐",
        language="Chinese (Mandarin)",
        description="有个性、略带骄傲感的女声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Kind-hearted_Antie",
        voice_name="亲切阿姨",
        language="Chinese (Mandarin)",
        description="亲切温和的阿姨声线。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_HK_Flight_Attendant",
        voice_name="港风空乘",
        language="Chinese (Mandarin)",
        description="服务感较强的空乘声线。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Humorous_Elder",
        voice_name="幽默长者",
        language="Chinese (Mandarin)",
        description="幽默长者声线。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Gentleman",
        voice_name="温和绅士",
        language="Chinese (Mandarin)",
        description="温和绅士男声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Warm_Bestie",
        voice_name="暖心挚友",
        language="Chinese (Mandarin)",
        description="温暖亲近的朋友声线。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Stubborn_Friend",
        voice_name="固执朋友",
        language="Chinese (Mandarin)",
        description="固执朋友感声线。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Sweet_Lady",
        voice_name="甜美女士",
        language="Chinese (Mandarin)",
        description="甜美温柔女声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Southern_Young_Man",
        voice_name="南方青年",
        language="Chinese (Mandarin)",
        description="南方年轻男声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Wise_Women",
        voice_name="睿智女性",
        language="Chinese (Mandarin)",
        description="沉稳智慧女声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Gentle_Youth",
        voice_name="温柔青年",
        language="Chinese (Mandarin)",
        description="温柔青年声线。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Warm_Girl",
        voice_name="温暖女孩",
        language="Chinese (Mandarin)",
        description="温暖年轻女声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Male_Announcer",
        voice_name="男播音员",
        language="Chinese (Mandarin)",
        description="播音男声。",
    ),
    DefaultTTSVoiceRead(
        voice_id=DEFAULT_MINIMAX_TTS_VOICE_ID,
        voice_name="亲切长者",
        language="Chinese (Mandarin)",
        description="亲切长者声线，适合作为默认纪念陪伴音色。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Radio_Host",
        voice_name="电台主持",
        language="Chinese (Mandarin)",
        description="电台主持声线。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Lyrical_Voice",
        voice_name="抒情声线",
        language="Chinese (Mandarin)",
        description="抒情声线。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Straightforward_Boy",
        voice_name="直率男孩",
        language="Chinese (Mandarin)",
        description="直率男孩声线。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Sincere_Adult",
        voice_name="真诚成年人",
        language="Chinese (Mandarin)",
        description="真诚成人声线。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Gentle_Senior",
        voice_name="温和长辈",
        language="Chinese (Mandarin)",
        description="温和长辈声线。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Crisp_Girl",
        voice_name="清亮女孩",
        language="Chinese (Mandarin)",
        description="清脆女声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Pure-hearted_Boy",
        voice_name="纯真男孩",
        language="Chinese (Mandarin)",
        description="纯真男孩声线。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Soft_Girl",
        voice_name="柔和女孩",
        language="Chinese (Mandarin)",
        description="柔和女声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_IntellectualGirl",
        voice_name="知性女孩",
        language="Chinese (Mandarin)",
        description="知性女声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Warm_HeartedGirl",
        voice_name="暖心女孩",
        language="Chinese (Mandarin)",
        description="暖心女声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Laid_BackGirl",
        voice_name="松弛女孩",
        language="Chinese (Mandarin)",
        description="松弛女声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_ExplorativeGirl",
        voice_name="探索女孩",
        language="Chinese (Mandarin)",
        description="探索感年轻女声。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_Warm-HeartedAunt",
        voice_name="暖心阿姨",
        language="Chinese (Mandarin)",
        description="暖心阿姨声线。",
    ),
    DefaultTTSVoiceRead(
        voice_id="Chinese (Mandarin)_BashfulGirl",
        voice_name="害羞女孩",
        language="Chinese (Mandarin)",
        description="羞涩女声。",
    ),
]
DEFAULT_TTS_VOICE_IDS = {voice.voice_id for voice in DEFAULT_TTS_VOICES}


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
    _validate_default_tts_voice(payload.voice_id)
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
        "model_artifact_url": selected.model_artifact_url,
        "voice_id": _voice_id_for_model(selected),
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
    job.provider_type = result["provider_type"]
    job.provider_name = result["provider_name"]
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
    source_material = _get_owned_material_or_404(
        db,
        persona,
        voice_model.reference_audio_asset_id,
    )
    provider_payload = {
        "persona_id": persona.id,
        "voice_model_id": voice_model.id,
        "reference_audio_asset_id": voice_model.reference_audio_asset_id,
        "storage_url": source_material.storage_url,
        "file_name": source_material.file_name,
        "mime_type": source_material.mime_type,
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

    gateway_payload = {**provider_payload, "job_id": job.id}
    preflight_error = _voice_clone_preflight_error(source_material)
    if preflight_error:
        result = {
            "provider_type": "local",
            "provider_name": "voice_preflight",
            "capability": "voice_clone",
            "status": "failed",
            "input": gateway_payload,
            "output": {
                "clone_status": "failed",
                "error_message": preflight_error,
            },
        }
    else:
        try:
            result = _run_gateway("voice_clone", gateway_payload)
        except Exception as exc:
            result = {
                "provider_type": "third_party",
                "provider_name": "minimax",
                "capability": "voice_clone",
                "status": "failed",
                "input": gateway_payload,
                "output": {
                    "clone_status": "failed",
                    "error_message": str(exc),
                },
            }
    output = result["output"]
    job.provider_type = result["provider_type"]
    job.provider_name = result["provider_name"]
    if output["clone_status"] == "failed":
        voice_model.status = "clone_failed"
        voice_model.provider_type = result["provider_type"]
        voice_model.provider_name = result["provider_name"]
        voice_model.user_selected = False
        job.status = "failed"
        job.error_message = output["error_message"]
        selected = _create_default_tts_model(db, persona, DefaultTTSSelection())
        db.flush()
        voice_status: VoiceStatus = "default_tts"
    else:
        _clear_selected_voice_models(db, persona)
        voice_model.provider_type = result["provider_type"]
        voice_model.provider_name = result["provider_name"]
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
    settings = get_settings()
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
        default_tts_voices=DEFAULT_TTS_VOICES,
        tts_model=settings.minimax_tts_model,
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
    _validate_default_tts_voice(payload.voice_id)
    _clear_selected_voice_models(db, persona)
    model = VoiceModel(
        persona_id=persona.id,
        provider_type="local",
        provider_name="mock_default_tts",
        status="default_tts",
        model_artifact_url=_system_voice_artifact_url(payload.voice_id),
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
        f"voice_id={payload.voice_id};"
        f"gender={payload.gender};"
        f"age_style={payload.age_style};"
        f"style={payload.style};"
        f"speed={payload.speed};"
        f"emotion={payload.emotion}"
    )


def _validate_default_tts_voice(voice_id: str) -> None:
    if voice_id not in DEFAULT_TTS_VOICE_IDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown default TTS voice_id",
        )


def _system_voice_artifact_url(voice_id: str) -> str:
    return f"{SYSTEM_VOICE_ARTIFACT_PREFIX}{quote(voice_id, safe='')}"


def _voice_id_for_model(model: VoiceModel) -> str | None:
    artifact = model.model_artifact_url or ""
    if artifact.startswith(CLONED_VOICE_ARTIFACT_PREFIX):
        return artifact.rsplit("/", 1)[-1]
    if artifact.startswith(SYSTEM_VOICE_ARTIFACT_PREFIX):
        return unquote(artifact.removeprefix(SYSTEM_VOICE_ARTIFACT_PREFIX))
    if model.status == "default_tts":
        return DEFAULT_MINIMAX_TTS_VOICE_ID
    return None


def _voice_clone_preflight_error(material: SourceMaterial) -> str | None:
    if not _is_wav_audio(material):
        return None
    duration_seconds = _wav_duration_seconds(material.storage_url)
    if duration_seconds is None:
        return "无法读取 WAV 音频时长，请重新录制或上传 mp3/m4a/wav 人声音频。"
    if duration_seconds < MINIMAX_VOICE_CLONE_MIN_SECONDS:
        return (
            f"音频时长约 {duration_seconds:.1f} 秒，"
            f"MiniMax 音色克隆要求样本至少 {MINIMAX_VOICE_CLONE_MIN_SECONDS} 秒。"
            "请重新录制或上传更长的人声音频。"
        )
    return None


def _is_wav_audio(material: SourceMaterial) -> bool:
    file_name = (material.file_name or "").lower()
    mime_type = (material.mime_type or "").lower()
    return file_name.endswith(".wav") or "wav" in mime_type


def _wav_duration_seconds(storage_url: str | None) -> float | None:
    if not storage_url:
        return None
    path = Path(storage_url)
    if not path.exists() or not path.is_file():
        return None
    try:
        with wave.open(path.as_posix(), "rb") as audio:
            frame_rate = audio.getframerate()
            if frame_rate <= 0:
                return None
            return audio.getnframes() / frame_rate
    except (EOFError, wave.Error):
        return None


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
