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


def test_settings_accept_dashscope_and_tripo_runtime_values(monkeypatch):
    for key in [
        "DASHSCOPE_API_KEY",
        "DASHSCOPE_REGION",
        "DASHSCOPE_WORKSPACE_ID",
        "DASHSCOPE_BASE_URL",
        "DASHSCOPE_COMPAT_BASE_URL",
        "QWEN_TEXT_MODEL",
        "QWEN_VISION_MODEL",
        "QWEN_OCR_MODEL",
        "QWEN_ASR_MODEL",
        "TRIPO_API_KEY",
        "TRIPO_BASE_URL",
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(
        config,
        "_load_runtime_env",
        lambda: {
            "DASHSCOPE_API_KEY": "dashscope-secret",
            "DASHSCOPE_REGION": "cn-beijing",
            "DASHSCOPE_WORKSPACE_ID": "workspace-123",
            "DASHSCOPE_BASE_URL": "https://workspace-123.cn-beijing.maas.aliyuncs.com/api/v1",
            "DASHSCOPE_COMPAT_BASE_URL": "https://workspace-123.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
            "QWEN_TEXT_MODEL": "qwen-plus",
            "QWEN_VISION_MODEL": "qwen3.7-plus",
            "QWEN_OCR_MODEL": "qwen-vl-ocr-latest",
            "QWEN_ASR_MODEL": "qwen3-asr-flash",
            "TRIPO_API_KEY": "tripo-secret",
            "TRIPO_BASE_URL": "https://api.tripo3d.ai",
        },
    )
    get_settings.cache_clear()

    try:
        settings = get_settings()
    finally:
        get_settings.cache_clear()

    assert settings.dashscope_api_key == "dashscope-secret"
    assert settings.dashscope_region == "cn-beijing"
    assert settings.dashscope_workspace_id == "workspace-123"
    assert settings.dashscope_base_url.endswith("/api/v1")
    assert settings.dashscope_compat_base_url.endswith("/compatible-mode/v1")
    assert settings.qwen_text_model == "qwen-plus"
    assert settings.qwen_vision_model == "qwen3.7-plus"
    assert settings.qwen_ocr_model == "qwen-vl-ocr-latest"
    assert settings.qwen_asr_model == "qwen3-asr-flash"
    assert settings.tripo_api_key == "tripo-secret"
    assert settings.tripo_base_url == "https://api.tripo3d.ai"
    assert "dashscope-secret" not in repr(settings)
    assert "tripo-secret" not in repr(settings)


def test_settings_accept_minimax_voice_runtime_from_openai_aliases(monkeypatch):
    for key in [
        "MINIMAX_API_KEY",
        "MINIMAX_BASE_URL",
        "MINIMAX_TTS_MODEL",
        "MINIMAX_CLONE_MODEL",
        "MINIMAX_DEFAULT_VOICE_ID",
        "OPENAI_COMPATIBLE_BASE_URL",
        "OPENAI_COMPATIBLE_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(
        config,
        "_load_runtime_env",
        lambda: {
            "OPENAI_BASE_URL": "https://api.minimaxi.com/v1",
            "OPENAI_API_KEY": "minimax-secret",
        },
    )
    get_settings.cache_clear()

    try:
        settings = get_settings()
    finally:
        get_settings.cache_clear()

    assert settings.minimax_api_key == "minimax-secret"
    assert settings.minimax_base_url == "https://api.minimaxi.com/v1"
    assert settings.minimax_tts_model == "speech-2.8-hd"
    assert settings.minimax_clone_model == "speech-2.8-hd"
    assert settings.minimax_default_voice_id == "male-qn-qingse"
    assert "minimax-secret" not in repr(settings)


def test_settings_no_longer_exposes_local_embedding_runtime_values(monkeypatch):
    for key in [
        "EMBEDDING_PROVIDER",
        "LOCAL_EMBEDDING_MODEL",
        "LOCAL_EMBEDDING_DIMENSIONS",
        "LOCAL_EMBEDDING_BATCH_SIZE",
        "LOCAL_GPU_WORKER_URL",
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(
        config,
        "_load_runtime_env",
        lambda: {
            "EMBEDDING_PROVIDER": "local_gpu",
            "LOCAL_EMBEDDING_MODEL": "BAAI/bge-m3",
            "LOCAL_EMBEDDING_DIMENSIONS": "1024",
            "LOCAL_EMBEDDING_BATCH_SIZE": "16",
            "LOCAL_GPU_WORKER_URL": "http://host.docker.internal:9000",
        },
    )
    get_settings.cache_clear()

    try:
        settings = get_settings()
    finally:
        get_settings.cache_clear()

    assert not hasattr(settings, "embedding_provider")
    assert not hasattr(settings, "local_embedding_model")
    assert not hasattr(settings, "local_embedding_dimensions")
    assert not hasattr(settings, "local_embedding_batch_size")
    assert not hasattr(settings, "local_gpu_worker_url")
