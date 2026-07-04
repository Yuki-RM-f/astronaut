from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


def _runtime_env_path() -> Path:
    return Path(__file__).resolve().parents[3] / ".env" / "runtime.env"


def _load_runtime_env() -> dict[str, str]:
    path = _runtime_env_path()
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _setting(
    name: str,
    default: str,
    runtime_env: dict[str, str],
    *aliases: str,
) -> str:
    names = (name, *aliases)
    for key in names:
        value = os.environ.get(key)
        if value:
            return value
    for key in names:
        value = runtime_env.get(key)
        if value:
            return value
    return default


def _setting_int(
    name: str,
    default: int,
    runtime_env: dict[str, str],
    *aliases: str,
) -> int:
    value = _setting(name, str(default), runtime_env, *aliases)
    try:
        return int(value)
    except ValueError:
        return default


def _dashscope_base_url(region: str, workspace_id: str, *, compatible: bool) -> str:
    suffix = "compatible-mode/v1" if compatible else "api/v1"
    if workspace_id:
        region_hosts = {
            "cn-beijing": "cn-beijing.maas.aliyuncs.com",
            "ap-southeast-1": "ap-southeast-1.maas.aliyuncs.com",
            "cn-hongkong": "cn-hongkong.maas.aliyuncs.com",
            "eu-central-1": "eu-central-1.maas.aliyuncs.com",
            "ap-northeast-1": "ap-northeast-1.maas.aliyuncs.com",
        }
        host = region_hosts.get(region, f"{region}.maas.aliyuncs.com")
        return f"https://{workspace_id}.{host}/{suffix}"
    if region == "us-east-1":
        host = "dashscope-us.aliyuncs.com"
    elif region == "ap-southeast-1":
        host = "dashscope-intl.aliyuncs.com"
    else:
        host = "dashscope.aliyuncs.com"
    return f"https://{host}/{suffix}"


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/persona_memory"
    redis_url: str = "redis://redis:6379/0"
    minio_endpoint: str = "minio:9000"
    minio_bucket: str = "persona-memory"
    jwt_secret: str = field(default="change-me", repr=False)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    default_llm_provider: str = "mock"
    openai_compatible_base_url: str = ""
    openai_compatible_api_key: str = field(default="", repr=False)
    openai_compatible_model: str = ""
    dashscope_api_key: str = field(default="", repr=False)
    dashscope_region: str = "cn-beijing"
    dashscope_workspace_id: str = ""
    dashscope_base_url: str = ""
    dashscope_compat_base_url: str = ""
    qwen_text_model: str = "qwen-plus"
    qwen_vision_model: str = "qwen3.7-plus"
    qwen_ocr_model: str = "qwen-vl-ocr-latest"
    qwen_asr_model: str = "qwen3-asr-flash"
    dashscope_request_timeout_seconds: int = 60
    tripo_api_key: str = field(default="", repr=False)
    tripo_base_url: str = "https://api.tripo3d.ai"
    cosyvoice_tts_model: str = "cosyvoice-v3.5-flash"
    cosyvoice_clone_model: str = "cosyvoice-v3.5-flash"
    minimax_api_key: str = field(default="", repr=False)
    minimax_base_url: str = "https://api.minimaxi.com/v1"
    minimax_tts_model: str = "speech-2.8-hd"
    minimax_clone_model: str = "speech-2.8-hd"
    minimax_default_voice_id: str = "male-qn-qingse"
    minimax_request_timeout_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    runtime_env = _load_runtime_env()
    dashscope_region = _setting("DASHSCOPE_REGION", "cn-beijing", runtime_env)
    dashscope_workspace_id = _setting("DASHSCOPE_WORKSPACE_ID", "", runtime_env)
    openai_compatible_base_url = _setting(
        "OPENAI_COMPATIBLE_BASE_URL", "", runtime_env, "OPENAI_BASE_URL"
    )
    openai_compatible_api_key = _setting(
        "OPENAI_COMPATIBLE_API_KEY", "", runtime_env, "OPENAI_API_KEY"
    )
    openai_compatible_model = _setting(
        "OPENAI_COMPATIBLE_MODEL", "", runtime_env, "OPENAI_MODEL"
    )
    minimax_base_url = _setting("MINIMAX_BASE_URL", "", runtime_env)
    if not minimax_base_url and "minimaxi.com" in openai_compatible_base_url:
        minimax_base_url = openai_compatible_base_url
    if not minimax_base_url:
        minimax_base_url = "https://api.minimaxi.com/v1"
    minimax_api_key = _setting("MINIMAX_API_KEY", "", runtime_env)
    if not minimax_api_key and "minimaxi.com" in minimax_base_url:
        minimax_api_key = openai_compatible_api_key
    return Settings(
        app_env=_setting("APP_ENV", "development", runtime_env),
        frontend_url=_setting("FRONTEND_URL", "http://localhost:3000", runtime_env),
        backend_url=_setting("BACKEND_URL", "http://localhost:8000", runtime_env),
        database_url=_setting(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@postgres:5432/persona_memory",
            runtime_env,
        ),
        redis_url=_setting("REDIS_URL", "redis://redis:6379/0", runtime_env),
        minio_endpoint=_setting("MINIO_ENDPOINT", "minio:9000", runtime_env),
        minio_bucket=_setting("MINIO_BUCKET", "persona-memory", runtime_env),
        jwt_secret=_setting("JWT_SECRET", "change-me", runtime_env),
        default_llm_provider=_setting("DEFAULT_LLM_PROVIDER", "mock", runtime_env),
        openai_compatible_base_url=openai_compatible_base_url,
        openai_compatible_api_key=openai_compatible_api_key,
        openai_compatible_model=openai_compatible_model,
        dashscope_api_key=_setting("DASHSCOPE_API_KEY", "", runtime_env),
        dashscope_region=dashscope_region,
        dashscope_workspace_id=dashscope_workspace_id,
        dashscope_base_url=_setting(
            "DASHSCOPE_BASE_URL",
            _dashscope_base_url(
                dashscope_region,
                dashscope_workspace_id,
                compatible=False,
            ),
            runtime_env,
        ),
        dashscope_compat_base_url=_setting(
            "DASHSCOPE_COMPAT_BASE_URL",
            _dashscope_base_url(
                dashscope_region,
                dashscope_workspace_id,
                compatible=True,
            ),
            runtime_env,
        ),
        qwen_text_model=_setting("QWEN_TEXT_MODEL", "qwen-plus", runtime_env),
        qwen_vision_model=_setting("QWEN_VISION_MODEL", "qwen3.7-plus", runtime_env),
        qwen_ocr_model=_setting("QWEN_OCR_MODEL", "qwen-vl-ocr-latest", runtime_env),
        qwen_asr_model=_setting("QWEN_ASR_MODEL", "qwen3-asr-flash", runtime_env),
        dashscope_request_timeout_seconds=_setting_int(
            "DASHSCOPE_REQUEST_TIMEOUT_SECONDS", 60, runtime_env
        ),
        tripo_api_key=_setting("TRIPO_API_KEY", "", runtime_env),
        tripo_base_url=_setting("TRIPO_BASE_URL", "https://api.tripo3d.ai", runtime_env),
        cosyvoice_tts_model=_setting(
            "COSYVOICE_TTS_MODEL", "cosyvoice-v3.5-flash", runtime_env
        ),
        cosyvoice_clone_model=_setting(
            "COSYVOICE_CLONE_MODEL", "cosyvoice-v3.5-flash", runtime_env
        ),
        minimax_api_key=minimax_api_key,
        minimax_base_url=minimax_base_url,
        minimax_tts_model=_setting("MINIMAX_TTS_MODEL", "speech-2.8-hd", runtime_env),
        minimax_clone_model=_setting(
            "MINIMAX_CLONE_MODEL", "speech-2.8-hd", runtime_env
        ),
        minimax_default_voice_id=_setting(
            "MINIMAX_DEFAULT_VOICE_ID", "male-qn-qingse", runtime_env
        ),
        minimax_request_timeout_seconds=_setting_int(
            "MINIMAX_REQUEST_TIMEOUT_SECONDS", 60, runtime_env
        ),
    )
