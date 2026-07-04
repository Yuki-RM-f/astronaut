from __future__ import annotations

from app.core import config
from app.core.config import Settings, get_settings
from app.schemas.provider_settings import ProviderSettingsResponse, ProviderStatus


SECRET_KEYS = {
    "OPENAI_COMPATIBLE_API_KEY",
    "OPENAI_API_KEY",
    "DASHSCOPE_API_KEY",
    "MINIMAX_API_KEY",
    "TRIPO_API_KEY",
}

ALLOWED_RUNTIME_KEYS = {
    "DEFAULT_LLM_PROVIDER",
    "OPENAI_COMPATIBLE_BASE_URL",
    "OPENAI_COMPATIBLE_API_KEY",
    "OPENAI_COMPATIBLE_MODEL",
    "OPENAI_BASE_URL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "DASHSCOPE_API_KEY",
    "DASHSCOPE_REGION",
    "DASHSCOPE_WORKSPACE_ID",
    "DASHSCOPE_BASE_URL",
    "DASHSCOPE_COMPAT_BASE_URL",
    "QWEN_TEXT_MODEL",
    "QWEN_VISION_MODEL",
    "QWEN_OCR_MODEL",
    "QWEN_ASR_MODEL",
    "MINIMAX_API_KEY",
    "MINIMAX_BASE_URL",
    "MINIMAX_TTS_MODEL",
    "MINIMAX_CLONE_MODEL",
    "MINIMAX_DEFAULT_VOICE_ID",
    "TRIPO_API_KEY",
    "TRIPO_BASE_URL",
}


def provider_settings_report(settings: Settings | None = None) -> ProviderSettingsResponse:
    active_settings = settings or get_settings()
    runtime_env_path = config._runtime_env_path()
    return ProviderSettingsResponse(
        default_llm_provider=active_settings.default_llm_provider,
        runtime_env_path=str(runtime_env_path),
        runtime_env_exists=runtime_env_path.exists(),
        providers=[
            ProviderStatus(
                id="mock",
                label="Mock Provider",
                configured=True,
                secret_status="not_required",
                capabilities=[
                    "text_parser",
                    "ocr",
                    "asr",
                    "image_understanding",
                    "video_understanding",
                    "memory_extraction",
                    "chat_llm",
                    "story_generation",
                    "tts",
                    "voice_clone",
                    "avatar_3d",
                ],
                settings={"default_llm_provider": active_settings.default_llm_provider},
            ),
            ProviderStatus(
                id="dashscope",
                label="DashScope / Qwen",
                configured=bool(active_settings.dashscope_api_key),
                secret_status=_secret_status(active_settings.dashscope_api_key),
                capabilities=[
                    "text_parser",
                    "ocr",
                    "asr",
                    "image_understanding",
                    "video_understanding",
                    "memory_extraction",
                ],
                settings={
                    "region": active_settings.dashscope_region,
                    "workspace_id": active_settings.dashscope_workspace_id,
                    "base_url": active_settings.dashscope_base_url,
                    "compat_base_url": active_settings.dashscope_compat_base_url,
                    "qwen_text_model": active_settings.qwen_text_model,
                    "qwen_vision_model": active_settings.qwen_vision_model,
                    "qwen_ocr_model": active_settings.qwen_ocr_model,
                    "qwen_asr_model": active_settings.qwen_asr_model,
                },
            ),
            ProviderStatus(
                id="minimax",
                label="MiniMax",
                configured=bool(active_settings.minimax_api_key),
                secret_status=_secret_status(active_settings.minimax_api_key),
                capabilities=[
                    "tts",
                    "voice_clone",
                    "chat_llm",
                    "story_generation",
                    "memory_context_compression",
                ],
                settings={
                    "base_url": active_settings.minimax_base_url,
                    "chat_model": active_settings.openai_compatible_model,
                    "tts_model": active_settings.minimax_tts_model,
                    "clone_model": active_settings.minimax_clone_model,
                    "default_voice_id": active_settings.minimax_default_voice_id,
                },
            ),
            ProviderStatus(
                id="openai_compatible",
                label="OpenAI-Compatible LLM",
                configured=bool(
                    active_settings.openai_compatible_api_key
                    and active_settings.openai_compatible_base_url
                ),
                secret_status=_secret_status(active_settings.openai_compatible_api_key),
                capabilities=["chat_llm", "story_generation", "memory_context_compression"],
                settings={
                    "base_url": active_settings.openai_compatible_base_url,
                    "model": active_settings.openai_compatible_model,
                },
            ),
            ProviderStatus(
                id="tripo",
                label="Tripo 3D",
                configured=bool(active_settings.tripo_api_key),
                secret_status=_secret_status(active_settings.tripo_api_key),
                capabilities=["future_avatar_3d"],
                settings={"base_url": active_settings.tripo_base_url},
            ),
        ],
    )


def update_runtime_provider_settings(values: dict[str, str]) -> ProviderSettingsResponse:
    unknown_keys = sorted(set(values) - ALLOWED_RUNTIME_KEYS)
    if unknown_keys:
        raise ValueError(f"Unsupported provider setting keys: {', '.join(unknown_keys)}")

    runtime_env_path = config._runtime_env_path()
    runtime_values = config._load_runtime_env()
    for key, value in values.items():
        if value:
            runtime_values[key] = value
        else:
            runtime_values.pop(key, None)

    runtime_env_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_env_path.write_text(_serialize_runtime_env(runtime_values), encoding="utf-8")
    get_settings.cache_clear()
    return provider_settings_report()


def _secret_status(value: str) -> str:
    return "configured" if value else "missing"


def _serialize_runtime_env(values: dict[str, str]) -> str:
    lines = [f"{key}={values[key]}" for key in sorted(values)]
    return "\n".join(lines) + ("\n" if lines else "")
