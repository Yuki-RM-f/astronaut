from pathlib import Path

from app.core import config
from app.core.config import get_settings


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_user(client, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "passw0rd", "display_name": "Demo"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def isolate_provider_env(monkeypatch, runtime_env_path: Path) -> None:
    for key in [
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
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(config, "_runtime_env_path", lambda: runtime_env_path)
    get_settings.cache_clear()


def test_provider_settings_report_masks_runtime_secrets(client, monkeypatch, tmp_path):
    runtime_env = tmp_path / "runtime.env"
    runtime_env.write_text(
        "\n".join(
            [
                "DEFAULT_LLM_PROVIDER=dashscope",
                "DASHSCOPE_API_KEY=dashscope-secret",
                "DASHSCOPE_WORKSPACE_ID=ws-demo",
                "QWEN_TEXT_MODEL=qwen-plus",
                "MINIMAX_API_KEY=minimax-secret",
                "MINIMAX_BASE_URL=https://api.minimaxi.com/v1",
                "EMBEDDING_PROVIDER=local_gpu",
                "LOCAL_GPU_WORKER_URL=http://host.docker.internal:9000",
            ]
        ),
        encoding="utf-8",
    )
    isolate_provider_env(monkeypatch, runtime_env)
    token = register_user(client, "provider-report@example.com")

    response = client.get("/api/settings/providers", headers=auth(token))

    assert response.status_code == 200
    assert "dashscope-secret" not in response.text
    assert "minimax-secret" not in response.text
    body = response.json()
    assert body["runtime_env_exists"] is True
    assert body["default_llm_provider"] == "dashscope"
    providers = {provider["id"]: provider for provider in body["providers"]}
    assert providers["dashscope"]["configured"] is True
    assert providers["dashscope"]["secret_status"] == "configured"
    assert providers["dashscope"]["settings"]["workspace_id"] == "ws-demo"
    assert providers["minimax"]["configured"] is True
    assert providers["mock"]["configured"] is True
    assert "local_gpu" not in providers


def test_update_provider_settings_writes_allowlisted_runtime_env(client, monkeypatch, tmp_path):
    runtime_env = tmp_path / "runtime.env"
    runtime_env.write_text("DEFAULT_LLM_PROVIDER=mock\n", encoding="utf-8")
    isolate_provider_env(monkeypatch, runtime_env)
    token = register_user(client, "provider-update@example.com")

    response = client.put(
        "/api/settings/providers",
        headers=auth(token),
        json={
            "values": {
                "DEFAULT_LLM_PROVIDER": "dashscope",
                "DASHSCOPE_API_KEY": "new-dashscope-secret",
                "DASHSCOPE_WORKSPACE_ID": "ws-new",
                "MINIMAX_API_KEY": "new-minimax-secret",
                "MINIMAX_BASE_URL": "https://api.minimaxi.com/v1",
            }
        },
    )

    assert response.status_code == 200
    assert "new-dashscope-secret" not in response.text
    assert "new-minimax-secret" not in response.text
    body = response.json()
    assert body["default_llm_provider"] == "dashscope"
    assert {provider["id"]: provider for provider in body["providers"]}["dashscope"][
        "configured"
    ]
    saved = runtime_env.read_text(encoding="utf-8")
    assert "DEFAULT_LLM_PROVIDER=dashscope" in saved
    assert "DASHSCOPE_API_KEY=new-dashscope-secret" in saved
    assert "MINIMAX_API_KEY=new-minimax-secret" in saved


def test_update_provider_settings_rejects_unknown_runtime_keys(client, monkeypatch, tmp_path):
    runtime_env = tmp_path / "runtime.env"
    isolate_provider_env(monkeypatch, runtime_env)
    token = register_user(client, "provider-bad-key@example.com")

    response = client.put(
        "/api/settings/providers",
        headers=auth(token),
        json={"values": {"UNTRACKED_SECRET": "do-not-write"}},
    )

    assert response.status_code == 400
    assert not runtime_env.exists()


def test_update_provider_settings_rejects_embedding_runtime_keys(
    client,
    monkeypatch,
    tmp_path,
):
    runtime_env = tmp_path / "runtime.env"
    isolate_provider_env(monkeypatch, runtime_env)
    token = register_user(client, "provider-embedding-key@example.com")

    response = client.put(
        "/api/settings/providers",
        headers=auth(token),
        json={
            "values": {
                "EMBEDDING_PROVIDER": "local_gpu",
                "LOCAL_GPU_WORKER_URL": "http://host.docker.internal:9000",
            }
        },
    )

    assert response.status_code == 400
    assert not runtime_env.exists()
