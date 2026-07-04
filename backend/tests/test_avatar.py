AVATAR_FAILURE_NOTICE = (
    "这张照片暂时没有生成成功。你可以换一张更清晰的正脸照，或者先使用默认纪念形象继续对话。"
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


def upload_image_material(client, token: str, persona_id: str) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/materials/upload",
        headers=auth(token),
        files=[("files", ("portrait.jpg", b"image-bytes", "image/jpeg"))],
        data={"importance": "important", "user_description": "外婆的正脸照"},
    )
    assert response.status_code == 201
    return response.json()["items"][0]


def create_manual_material(client, token: str, persona_id: str) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/materials/manual",
        headers=auth(token),
        json={"manual_text": "不是图片资料", "importance": "normal"},
    )
    assert response.status_code == 201
    return response.json()


def upload_glb_avatar(client, token: str, persona_id: str, *, file_name: str = "waipo.glb") -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/avatar/upload",
        headers=auth(token),
        files={"file": (file_name, b"glb-model-bytes", "model/gltf-binary")},
    )
    assert response.status_code == 201
    return response.json()


def test_get_avatar_config_starts_with_no_avatar(client):
    token = register_user(client, "avatar-initial@example.com")
    persona = create_persona(client, token)

    response = client.get(f"/api/personas/{persona['id']}/avatar", headers=auth(token))

    assert response.status_code == 200
    data = response.json()
    assert data["avatar_status"] == "no_avatar"
    assert data["selected_avatar_model"] is None
    assert data["avatar_models"] == []
    assert data["failure_notice"] == AVATAR_FAILURE_NOTICE
    assert data["style_options"] == ["semi_realistic", "cartoon", "memorial"]


def test_select_default_avatar_creates_selected_glb_model(client):
    token = register_user(client, "avatar-default@example.com")
    persona = create_persona(client, token)

    response = client.post(
        f"/api/personas/{persona['id']}/avatar/default",
        headers=auth(token),
        json={"style": "memorial"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["avatar_status"] == "default_avatar"
    assert data["selected_avatar_model"]["status"] == "default_avatar"
    assert data["selected_avatar_model"]["style"] == "memorial"
    assert data["selected_avatar_model"]["format"] == "glb"
    assert data["selected_avatar_model"]["model_url"].startswith("mock://avatar/default/")
    assert data["selected_avatar_model"]["user_selected"] is True
    assert data["selected_avatar_model"]["animation_config_json"]["idle_breath"] is True
    assert data["selected_avatar_model"]["expression_config_json"]["smile"] is True
    assert data["selected_avatar_model"]["lip_sync_config_json"]["mode"] == "audio_envelope"


def test_upload_glb_avatar_creates_selected_model_and_serves_file(
    client, monkeypatch, tmp_path
):
    from app.services import avatar as avatar_service

    monkeypatch.setattr(
        avatar_service,
        "LOCAL_AVATAR_MODELS_ROOT",
        tmp_path / "avatar_models",
        raising=False,
    )
    token = register_user(client, "avatar-upload@example.com")
    persona = create_persona(client, token)

    data = upload_glb_avatar(client, token, persona["id"])

    selected = data["selected_avatar_model"]
    assert data["avatar_status"] == "uploaded_ready"
    assert selected["status"] == "uploaded_ready"
    assert selected["format"] == "glb"
    assert selected["provider_type"] == "user_upload"
    assert selected["provider_name"] == "glb_upload"
    assert selected["model_url"] == f"/api/avatar-models/{selected['id']}/file"
    assert selected["user_selected"] is True
    assert data["avatar_models"][0]["id"] == selected["id"]

    served = client.get(selected["model_url"], headers=auth(token))

    assert served.status_code == 200
    assert served.content == b"glb-model-bytes"
    assert served.headers["content-type"].startswith("model/gltf-binary")

    jobs = client.get(f"/api/personas/{persona['id']}/jobs", headers=auth(token))
    assert jobs.status_code == 200
    assert not any(item["job_type"] == "avatar_3d" for item in jobs.json()["items"])


def test_upload_glb_rejects_non_glb_files(client):
    token = register_user(client, "avatar-upload-reject@example.com")
    persona = create_persona(client, token)

    response = client.post(
        f"/api/personas/{persona['id']}/avatar/upload",
        headers=auth(token),
        files={"file": ("portrait.jpg", b"image-bytes", "image/jpeg")},
    )

    assert response.status_code == 400


def test_avatar_model_file_is_user_scoped(client, monkeypatch, tmp_path):
    from app.services import avatar as avatar_service

    monkeypatch.setattr(
        avatar_service,
        "LOCAL_AVATAR_MODELS_ROOT",
        tmp_path / "avatar_models",
        raising=False,
    )
    owner_token = register_user(client, "avatar-file-owner@example.com")
    other_token = register_user(client, "avatar-file-other@example.com")
    persona = create_persona(client, owner_token)
    data = upload_glb_avatar(client, owner_token, persona["id"])
    model_url = data["selected_avatar_model"]["model_url"]

    assert client.get(model_url, headers=auth(owner_token)).status_code == 200
    assert client.get(model_url, headers=auth(other_token)).status_code == 404


def test_generate_avatar_from_image_material_creates_model_and_job(client):
    token = register_user(client, "avatar-generate@example.com")
    persona = create_persona(client, token)
    material = upload_image_material(client, token, persona["id"])

    response = client.post(
        f"/api/personas/{persona['id']}/avatar/generate",
        headers=auth(token),
        json={"source_image_material_id": material["id"], "style": "semi_realistic"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["avatar_status"] == "generated_ready"
    assert data["avatar_model"]["status"] == "generated_ready"
    assert data["avatar_model"]["source_image_material_id"] == material["id"]
    assert data["avatar_model"]["style"] == "semi_realistic"
    assert data["avatar_model"]["format"] == "glb"
    assert data["avatar_model"]["model_url"].startswith("mock://avatar-model/")
    assert data["selected_avatar_model"]["id"] == data["avatar_model"]["id"]
    assert data["selected_avatar_model"]["user_selected"] is True
    assert data["provider"]["capability"] == "avatar_3d"
    assert data["job"]["job_type"] == "avatar_3d"
    assert data["job"]["status"] == "succeeded"

    jobs = client.get(f"/api/personas/{persona['id']}/jobs", headers=auth(token))
    assert jobs.status_code == 200
    assert any(
        item["id"] == data["job"]["id"]
        and item["job_type"] == "avatar_3d"
        and item["status"] == "succeeded"
        for item in jobs.json()["items"]
    )


def test_generate_avatar_failure_falls_back_to_default_avatar(client):
    token = register_user(client, "avatar-failure@example.com")
    persona = create_persona(client, token)
    material = upload_image_material(client, token, persona["id"])

    response = client.post(
        f"/api/personas/{persona['id']}/avatar/generate",
        headers=auth(token),
        json={
            "source_image_material_id": material["id"],
            "style": "cartoon",
            "simulate_failure": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["avatar_status"] == "default_avatar"
    assert data["failure_notice"] == AVATAR_FAILURE_NOTICE
    assert data["avatar_model"]["status"] == "generation_failed"
    assert data["avatar_model"]["source_image_material_id"] == material["id"]
    assert data["selected_avatar_model"]["status"] == "default_avatar"
    assert data["selected_avatar_model"]["user_selected"] is True
    assert data["job"]["job_type"] == "avatar_3d"
    assert data["job"]["status"] == "failed"


def test_avatar_routes_reject_cross_user_access(client):
    owner_token = register_user(client, "avatar-owner@example.com")
    other_token = register_user(client, "avatar-other@example.com")
    persona = create_persona(client, owner_token)

    assert (
        client.get(f"/api/personas/{persona['id']}/avatar", headers=auth(other_token)).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/personas/{persona['id']}/avatar/default",
            headers=auth(other_token),
            json={"style": "memorial"},
        ).status_code
        == 404
    )


def test_generate_avatar_rejects_non_image_and_cross_user_materials(client):
    owner_token = register_user(client, "avatar-material-owner@example.com")
    other_token = register_user(client, "avatar-material-other@example.com")
    persona = create_persona(client, owner_token)
    manual = create_manual_material(client, owner_token, persona["id"])

    non_image = client.post(
        f"/api/personas/{persona['id']}/avatar/generate",
        headers=auth(owner_token),
        json={"source_image_material_id": manual["id"], "style": "memorial"},
    )
    assert non_image.status_code == 400

    cross_user = client.post(
        f"/api/personas/{persona['id']}/avatar/generate",
        headers=auth(other_token),
        json={"source_image_material_id": manual["id"], "style": "memorial"},
    )
    assert cross_user.status_code == 404
