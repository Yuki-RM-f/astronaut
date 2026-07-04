DEFAULT_TTS_NOTICE = (
    "当前使用系统默认声音，不是 TA 的真实声音。上传 TA 的清晰语音后，可以尝试生成模拟音色。"
)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_user(client, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "passw0rd", "display_name": "Demo"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def persona_payload(name: str = "外婆") -> dict[str, str]:
    return {
        "name": name,
        "persona_type": "deceased_relative",
        "status": "deceased",
        "relationship_to_user": "外婆",
        "user_nickname_by_persona": "小铭",
        "age": 72,
        "gender": "female",
        "language": "zh-CN",
        "short_bio": "她很温柔，喜欢做饭。",
        "speaking_style": "温柔、慢慢说",
        "emotional_style": "先安慰，再鼓励",
        "forbidden_expressions": "不要说我真的回来了",
    }


def create_persona(client, token: str, name: str = "外婆") -> dict:
    response = client.post(
        "/api/personas",
        headers=auth(token),
        json=persona_payload(name),
    )
    assert response.status_code == 201
    return response.json()


def default_tts_payload() -> dict[str, str]:
    return {
        "gender": "female",
        "age_style": "elderly",
        "style": "gentle",
        "speed": "normal",
        "emotion": "comfort",
    }


def upload_audio_material(client, token: str, persona_id: str) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/materials/upload",
        headers=auth(token),
        files=[("files", ("sample.mp3", b"voice-bytes", "audio/mpeg"))],
        data={"importance": "important", "user_description": "外婆的清晰语音"},
    )
    assert response.status_code == 201
    return response.json()["items"][0]


def create_manual_material(client, token: str, persona_id: str) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/materials/manual",
        headers=auth(token),
        json={"manual_text": "不是音频资料", "importance": "normal"},
    )
    assert response.status_code == 201
    return response.json()


def test_get_voice_config_starts_with_no_voice_and_default_tts_notice(client):
    token = register_user(client, "voice-initial@example.com")
    persona = create_persona(client, token)

    response = client.get(f"/api/personas/{persona['id']}/voice", headers=auth(token))

    assert response.status_code == 200
    data = response.json()
    assert data["voice_status"] == "no_voice"
    assert data["selected_voice_model"] is None
    assert data["voice_models"] == []
    assert data["default_tts_notice"] == DEFAULT_TTS_NOTICE


def test_select_default_tts_and_synthesize_speech_job(client):
    token = register_user(client, "voice-default@example.com")
    persona = create_persona(client, token)

    selected = client.post(
        f"/api/personas/{persona['id']}/voice/default-tts",
        headers=auth(token),
        json=default_tts_payload(),
    )

    assert selected.status_code == 200
    selected_data = selected.json()
    assert selected_data["voice_status"] == "default_tts"
    assert selected_data["default_tts_notice"] == DEFAULT_TTS_NOTICE
    assert selected_data["selected_voice_model"]["status"] == "default_tts"
    assert selected_data["selected_voice_model"]["provider_type"] == "local"
    assert selected_data["selected_voice_model"]["provider_name"] == "mock_default_tts"
    assert selected_data["selected_voice_model"]["user_selected"] is True

    synthesized = client.post(
        f"/api/personas/{persona['id']}/voice/synthesize",
        headers=auth(token),
        json={"text": "小铭，慢慢来。"},
    )

    assert synthesized.status_code == 200
    synth_data = synthesized.json()
    assert synth_data["voice_status"] == "default_tts"
    assert synth_data["audio_url"].startswith("mock://tts/")
    assert synth_data["default_tts_notice"] == DEFAULT_TTS_NOTICE
    assert synth_data["provider"]["provider_name"] == "mock"
    assert synth_data["provider"]["capability"] == "tts"
    assert synth_data["job"]["job_type"] == "synthesize_speech"
    assert synth_data["job"]["status"] == "succeeded"

    jobs = client.get(f"/api/personas/{persona['id']}/jobs", headers=auth(token))
    assert jobs.status_code == 200
    assert any(
        item["id"] == synth_data["job"]["id"]
        and item["job_type"] == "synthesize_speech"
        and item["status"] == "succeeded"
        for item in jobs.json()["items"]
    )


def test_synthesize_speech_records_minimax_provider_metadata(client, monkeypatch):
    from app.services import voice as voice_service

    def fake_gateway(capability, payload):
        assert capability == "tts"
        return {
            "provider_type": "third_party",
            "provider_name": "minimax",
            "capability": "tts",
            "status": "succeeded",
            "input": payload,
            "output": {
                "audio_url": "https://api.minimaxi.com/audio/preview.mp3",
                "duration_ms": 1200,
                "voice_status": payload["voice_status"],
                "voice_model_id": payload["voice_model_id"],
                "default_tts_notice": payload["default_tts_notice"],
            },
        }

    monkeypatch.setattr(voice_service, "_run_gateway", fake_gateway)
    token = register_user(client, "voice-minimax-tts@example.com")
    persona = create_persona(client, token)

    response = client.post(
        f"/api/personas/{persona['id']}/voice/synthesize",
        headers=auth(token),
        json={"text": "小铭，慢慢来。"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["audio_url"] == "https://api.minimaxi.com/audio/preview.mp3"
    assert data["provider"]["provider_name"] == "minimax"
    assert data["job"]["provider_type"] == "third_party"
    assert data["job"]["provider_name"] == "minimax"


def test_synthesize_without_clone_falls_back_to_default_tts(client):
    token = register_user(client, "voice-fallback@example.com")
    persona = create_persona(client, token)

    synthesized = client.post(
        f"/api/personas/{persona['id']}/voice/synthesize",
        headers=auth(token),
        json={"text": "我们慢慢说。"},
    )

    assert synthesized.status_code == 200
    data = synthesized.json()
    assert data["voice_status"] == "default_tts"
    assert data["selected_voice_model"]["status"] == "default_tts"
    assert data["default_tts_notice"] == DEFAULT_TTS_NOTICE
    assert data["audio_url"].startswith("mock://tts/")


def test_voice_routes_reject_cross_user_access(client):
    owner_token = register_user(client, "voice-owner@example.com")
    other_token = register_user(client, "voice-other@example.com")
    persona = create_persona(client, owner_token)

    assert (
        client.get(f"/api/personas/{persona['id']}/voice", headers=auth(other_token)).status_code
        == 404
    )


def test_create_voice_sample_from_audio_material_creates_model_and_job(client):
    token = register_user(client, "voice-sample@example.com")
    persona = create_persona(client, token)
    material = upload_audio_material(client, token, persona["id"])

    response = client.post(
        f"/api/personas/{persona['id']}/voice/samples",
        headers=auth(token),
        json={"source_material_id": material["id"]},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["voice_status"] == "sample_ready"
    assert data["voice_model"]["status"] == "sample_ready"
    assert data["voice_model"]["reference_audio_asset_id"] == material["id"]
    assert data["voice_model"]["sample_audio_url"]
    assert data["voice_model"]["user_selected"] is False
    assert data["job"]["job_type"] == "extract_voice_sample"
    assert data["job"]["status"] == "succeeded"
    assert data["provider"]["capability"] == "extract_voice_sample"

    config = client.get(f"/api/personas/{persona['id']}/voice", headers=auth(token))
    assert config.status_code == 200
    assert [item["id"] for item in config.json()["voice_models"]] == [
        data["voice_model"]["id"]
    ]


def test_clone_voice_success_selects_cloned_voice_model(client):
    token = register_user(client, "voice-clone-success@example.com")
    persona = create_persona(client, token)
    material = upload_audio_material(client, token, persona["id"])
    sample = client.post(
        f"/api/personas/{persona['id']}/voice/samples",
        headers=auth(token),
        json={"source_material_id": material["id"]},
    ).json()["voice_model"]

    response = client.post(
        f"/api/personas/{persona['id']}/voice/clone",
        headers=auth(token),
        json={"voice_model_id": sample["id"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["voice_status"] == "cloned_ready"
    assert data["voice_model"]["id"] == sample["id"]
    assert data["voice_model"]["status"] == "cloned_ready"
    assert data["selected_voice_model"]["id"] == sample["id"]
    assert data["selected_voice_model"]["user_selected"] is True
    assert data["selected_voice_model"]["model_artifact_url"].startswith(
        "mock://voice-model/"
    )
    assert data["job"]["job_type"] == "clone_voice"
    assert data["job"]["status"] == "succeeded"
    assert data["provider"]["capability"] == "voice_clone"


def test_clone_voice_records_minimax_voice_id_and_provider_metadata(client, monkeypatch):
    from app.services import voice as voice_service

    def fake_gateway(capability, payload):
        if capability == "extract_voice_sample":
            return {
                "provider_type": "local",
                "provider_name": "mock",
                "capability": "extract_voice_sample",
                "status": "succeeded",
                "input": payload,
                "output": {
                    "sample_text": "外婆的清晰语音，来自 sample.mp3 的 00:00-00:08 片段。",
                    "sample_audio_url": payload["storage_url"],
                    "start_time": "00:00",
                    "end_time": "00:08",
                    "quality_score": 76,
                },
            }
        assert capability == "voice_clone"
        assert payload["storage_url"]
        assert payload["file_name"] == "sample.mp3"
        return {
            "provider_type": "third_party",
            "provider_name": "minimax",
            "capability": "voice_clone",
            "status": "succeeded",
            "input": payload,
            "output": {
                "clone_status": "succeeded",
                "model_artifact_url": "minimax://voice/PMV12345678",
                "preview_audio_url": "https://api.minimaxi.com/audio/clone.mp3",
                "quality_score": 82,
            },
        }

    monkeypatch.setattr(voice_service, "_run_gateway", fake_gateway)
    token = register_user(client, "voice-minimax-clone@example.com")
    persona = create_persona(client, token)
    material = upload_audio_material(client, token, persona["id"])
    sample = client.post(
        f"/api/personas/{persona['id']}/voice/samples",
        headers=auth(token),
        json={"source_material_id": material["id"]},
    ).json()["voice_model"]

    response = client.post(
        f"/api/personas/{persona['id']}/voice/clone",
        headers=auth(token),
        json={"voice_model_id": sample["id"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"]["provider_name"] == "minimax"
    assert data["selected_voice_model"]["provider_type"] == "third_party"
    assert data["selected_voice_model"]["provider_name"] == "minimax"
    assert data["selected_voice_model"]["model_artifact_url"] == "minimax://voice/PMV12345678"
    assert data["job"]["provider_type"] == "third_party"
    assert data["job"]["provider_name"] == "minimax"


def test_clone_voice_failure_falls_back_to_default_tts(client):
    token = register_user(client, "voice-clone-failure@example.com")
    persona = create_persona(client, token)
    material = upload_audio_material(client, token, persona["id"])
    sample = client.post(
        f"/api/personas/{persona['id']}/voice/samples",
        headers=auth(token),
        json={"source_material_id": material["id"]},
    ).json()["voice_model"]

    response = client.post(
        f"/api/personas/{persona['id']}/voice/clone",
        headers=auth(token),
        json={"voice_model_id": sample["id"], "simulate_failure": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["voice_status"] == "default_tts"
    assert data["voice_model"]["status"] == "clone_failed"
    assert data["selected_voice_model"]["status"] == "default_tts"
    assert data["default_tts_notice"] == DEFAULT_TTS_NOTICE
    assert data["job"]["job_type"] == "clone_voice"
    assert data["job"]["status"] == "failed"

    synthesized = client.post(
        f"/api/personas/{persona['id']}/voice/synthesize",
        headers=auth(token),
        json={"text": "小铭，慢慢来。"},
    )
    assert synthesized.status_code == 200
    assert synthesized.json()["voice_status"] == "default_tts"


def test_voice_samples_reject_non_audio_and_cross_user_materials(client):
    owner_token = register_user(client, "voice-sample-owner@example.com")
    other_token = register_user(client, "voice-sample-other@example.com")
    persona = create_persona(client, owner_token)
    manual = create_manual_material(client, owner_token, persona["id"])

    non_audio = client.post(
        f"/api/personas/{persona['id']}/voice/samples",
        headers=auth(owner_token),
        json={"source_material_id": manual["id"]},
    )
    assert non_audio.status_code == 400

    cross_user = client.post(
        f"/api/personas/{persona['id']}/voice/samples",
        headers=auth(other_token),
        json={"source_material_id": manual["id"]},
    )
    assert cross_user.status_code == 404
    assert (
        client.post(
            f"/api/personas/{persona['id']}/voice/default-tts",
            headers=auth(other_token),
            json=default_tts_payload(),
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/personas/{persona['id']}/voice/synthesize",
            headers=auth(other_token),
            json={"text": "hello"},
        ).status_code
        == 404
    )
