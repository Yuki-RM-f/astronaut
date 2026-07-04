from app.core import config
from app.core.config import get_settings


def test_settings_accept_openai_runtime_aliases(monkeypatch):
    monkeypatch.delenv("OPENAI_COMPATIBLE_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_COMPATIBLE_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setattr(
        config,
        "_load_runtime_env",
        lambda: {
            "OPENAI_BASE_URL": "https://openai-compatible.example/v1",
            "OPENAI_API_KEY": "alias-secret",
            "OPENAI_MODEL": "alias-model",
        },
    )
    get_settings.cache_clear()

    try:
        settings = get_settings()
    finally:
        get_settings.cache_clear()

    assert settings.openai_compatible_base_url == "https://openai-compatible.example/v1"
    assert settings.openai_compatible_api_key == "alias-secret"
    assert settings.openai_compatible_model == "alias-model"
    assert "alias-secret" not in repr(settings)


def test_settings_preserve_openai_compatible_names(monkeypatch):
    monkeypatch.delenv("OPENAI_COMPATIBLE_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_COMPATIBLE_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setattr(
        config,
        "_load_runtime_env",
        lambda: {
            "OPENAI_COMPATIBLE_BASE_URL": "https://compatible.example/v1",
            "OPENAI_COMPATIBLE_API_KEY": "compatible-secret",
            "OPENAI_COMPATIBLE_MODEL": "compatible-model",
            "OPENAI_BASE_URL": "https://alias.example/v1",
            "OPENAI_API_KEY": "alias-secret",
            "OPENAI_MODEL": "alias-model",
        },
    )
    get_settings.cache_clear()

    try:
        settings = get_settings()
    finally:
        get_settings.cache_clear()

    assert settings.openai_compatible_base_url == "https://compatible.example/v1"
    assert settings.openai_compatible_api_key == "compatible-secret"
    assert settings.openai_compatible_model == "compatible-model"
    assert "compatible-secret" not in repr(settings)
