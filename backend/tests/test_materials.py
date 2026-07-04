from pathlib import Path

from sqlalchemy import select

from app.api.routes import materials as materials_route
from app.models.ai_job import AIJob
from app.models.memory_card import MemoryCard
from app.models.source_material import SourceMaterial
from app.services import parsing


def disable_background_parse(monkeypatch):
    scheduled: list[str] = []
    monkeypatch.setattr(
        materials_route,
        "run_material_parse_job_by_id",
        lambda job_id: scheduled.append(job_id),
        raising=False,
    )
    return scheduled


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_user(client, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "passw0rd", "display_name": "Demo"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def persona_payload() -> dict[str, str]:
    return {
        "name": "外婆",
        "persona_type": "deceased_relative",
        "status": "deceased",
        "relationship_to_user": "外婆",
        "user_nickname_by_persona": "小铭",
        "age": 72,
        "gender": "female",
        "language": "zh-CN",
        "short_bio": "她很温柔，喜欢做饭。",
        "speaking_style": "温柔、慢慢说",
        "emotional_style": "安慰、鼓励",
        "forbidden_expressions": "不要说我真的回来了",
    }


def create_persona(client, token: str) -> dict:
    response = client.post("/api/personas", headers=auth(token), json=persona_payload())
    assert response.status_code == 201
    return response.json()


def create_manual_material(client, token: str, persona_id: str) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/materials/manual",
        headers=auth(token),
        json={"manual_text": "外婆喜欢包馄饨。", "importance": "very_important"},
    )
    assert response.status_code == 201
    return response.json()


def test_upload_text_image_audio_video_creates_materials_and_pending_jobs(client, monkeypatch):
    scheduled = disable_background_parse(monkeypatch)
    token = register_user(client, "materials@example.com")
    persona = create_persona(client, token)
    files = [
        ("files", ("note.txt", b"hello", "text/plain")),
        ("files", ("photo.jpg", b"jpg", "image/jpeg")),
        ("files", ("voice.mp3", b"mp3", "audio/mpeg")),
        ("files", ("clip.mp4", b"mp4", "video/mp4")),
    ]

    response = client.post(
        f"/api/personas/{persona['id']}/materials/upload",
        headers=auth(token),
        files=files,
        data={"importance": "important", "user_description": "demo batch"},
    )

    assert response.status_code == 201
    items = response.json()["items"]
    assert [item["file_type"] for item in items] == ["text", "image", "audio", "video"]
    assert all(item["parse_status"] == "pending" for item in items)
    assert all(item["jobs"] for item in items)
    assert [item["jobs"][0]["job_type"] for item in items] == [
        "parse_text",
        "ocr_image",
        "asr_audio",
        "extract_video_audio",
    ]
    assert all(item["jobs"][0]["status"] == "pending" for item in items)
    assert scheduled == [item["jobs"][0]["id"] for item in items]
    assert all(item["user_description"] == "demo batch" for item in items)
    assert all(item["storage_url"].startswith("storage/materials/") for item in items)


def test_manual_material_creates_pending_parse_job_and_background_runner_generates_cards(
    client,
    db_session,
    monkeypatch,
):
    scheduled = disable_background_parse(monkeypatch)
    token = register_user(client, "manual@example.com")
    persona = create_persona(client, token)

    response = client.post(
        f"/api/personas/{persona['id']}/materials/manual",
        headers=auth(token),
        json={"manual_text": "外婆喜欢包馄饨。", "importance": "very_important"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["file_type"] == "manual"
    assert body["manual_text"] == "外婆喜欢包馄饨。"
    assert body["importance"] == "very_important"
    assert body["parse_status"] == "pending"
    assert body["jobs"][0]["job_type"] == "parse_text"
    assert body["jobs"][0]["status"] == "pending"
    assert scheduled == [body["jobs"][0]["id"]]
    assert db_session.scalars(select(MemoryCard)).all() == []

    material_model = db_session.get(SourceMaterial, body["id"])
    job_model = db_session.get(AIJob, body["jobs"][0]["id"])
    parsing.run_parse_job(db_session, material_model, job_model)
    db_session.commit()

    db_session.refresh(material_model)
    db_session.refresh(job_model)
    memories = db_session.scalars(select(MemoryCard)).all()
    assert material_model.parse_status == "succeeded"
    assert job_model.status == "succeeded"
    assert memories


def test_material_list_detail_parse_and_delete_are_user_scoped(client, monkeypatch):
    scheduled = disable_background_parse(monkeypatch)
    owner_token = register_user(client, "material-owner@example.com")
    other_token = register_user(client, "material-other@example.com")
    persona = create_persona(client, owner_token)
    material = create_manual_material(client, owner_token, persona["id"])

    listed = client.get(
        f"/api/personas/{persona['id']}/materials",
        headers=auth(owner_token),
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [material["id"]]

    detail = client.get(f"/api/materials/{material['id']}", headers=auth(owner_token))
    assert detail.status_code == 200
    assert detail.json()["id"] == material["id"]

    assert (
        client.get(f"/api/materials/{material['id']}", headers=auth(other_token)).status_code
        == 404
    )
    assert (
        client.post(f"/api/materials/{material['id']}/parse", headers=auth(other_token)).status_code
        == 404
    )
    assert (
        client.delete(f"/api/materials/{material['id']}", headers=auth(other_token)).status_code
        == 404
    )

    parse = client.post(f"/api/materials/{material['id']}/parse", headers=auth(owner_token))
    assert parse.status_code == 201
    assert parse.json()["job_type"] == "parse_text"
    assert parse.json()["source_material_id"] == material["id"]
    assert parse.json()["status"] == "pending"
    assert scheduled[-1] == parse.json()["id"]

    deleted = client.delete(f"/api/materials/{material['id']}", headers=auth(owner_token))
    assert deleted.status_code == 204
    assert client.get(f"/api/materials/{material['id']}", headers=auth(owner_token)).status_code == 404
    assert (
        client.get(f"/api/personas/{persona['id']}/materials", headers=auth(owner_token))
        .json()["items"]
        == []
    )


def test_delete_uploaded_material_removes_local_storage_file(client, monkeypatch):
    disable_background_parse(monkeypatch)
    token = register_user(client, "material-file-delete@example.com")
    persona = create_persona(client, token)

    uploaded = client.post(
        f"/api/personas/{persona['id']}/materials/upload",
        headers=auth(token),
        files=[("files", ("delete-me.txt", b"delete me", "text/plain"))],
    )
    assert uploaded.status_code == 201
    material = uploaded.json()["items"][0]
    storage_path = Path(material["storage_url"])
    assert storage_path.exists()

    deleted = client.delete(f"/api/materials/{material['id']}", headers=auth(token))

    assert deleted.status_code == 204
    assert not storage_path.exists()


def test_upload_rejects_unsupported_file_type(client):
    token = register_user(client, "unsupported-material@example.com")
    persona = create_persona(client, token)

    response = client.post(
        f"/api/personas/{persona['id']}/materials/upload",
        headers=auth(token),
        files=[("files", ("archive.zip", b"zip", "application/zip"))],
    )

    assert response.status_code == 400
