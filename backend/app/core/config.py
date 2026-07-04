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
    local_gpu_worker_url: str = "http://gpu-worker:9000"


@lru_cache
def get_settings() -> Settings:
    runtime_env = _load_runtime_env()
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
        openai_compatible_base_url=_setting(
            "OPENAI_COMPATIBLE_BASE_URL", "", runtime_env, "OPENAI_BASE_URL"
        ),
        openai_compatible_api_key=_setting(
            "OPENAI_COMPATIBLE_API_KEY", "", runtime_env, "OPENAI_API_KEY"
        ),
        openai_compatible_model=_setting(
            "OPENAI_COMPATIBLE_MODEL", "", runtime_env, "OPENAI_MODEL"
        ),
        local_gpu_worker_url=_setting(
            "LOCAL_GPU_WORKER_URL", "http://gpu-worker:9000", runtime_env
        ),
    )
