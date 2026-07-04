from sqlalchemy import select

from app.models.memory_card import MemoryCard
from app.models.parsed_chunk import ParsedChunk


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


def test_manual_material_generates_source_backed_memory_cards(client, db_session):
    token = register_user(client, "m3-manual@example.com")
    persona = create_persona(client, token)

    response = client.post(
        f"/api/personas/{persona['id']}/materials/manual",
        headers=auth(token),
        json={
            "manual_text": "外婆喜欢包馄饨。她常说慢慢来。",
            "importance": "very_important",
        },
    )

    assert response.status_code == 201
    material = response.json()
    assert material["parse_status"] == "succeeded"
    assert material["jobs"][0]["status"] == "succeeded"

    chunks = db_session.scalars(select(ParsedChunk)).all()
    memories = db_session.scalars(select(MemoryCard)).all()
    assert len(chunks) >= 1
    assert len(memories) >= 2
    assert all(memory.source_material_id == material["id"] for memory in memories)
    assert all(memory.source_type == "manual" for memory in memories)
    assert all(memory.source_quote for memory in memories)
    assert all(memory.source_location for memory in memories)
    assert {memory.status for memory in memories} == {"pending_review"}


def test_upload_demo_files_generate_type_specific_chunks_and_jobs(client, db_session):
    token = register_user(client, "m3-upload@example.com")
    persona = create_persona(client, token)
    files = [
        ("files", ("note.txt", "外婆喜欢包馄饨。".encode("utf-8"), "text/plain")),
        ("files", ("birthday.jpg", b"jpg", "image/jpeg")),
        ("files", ("voice.mp3", b"mp3", "audio/mpeg")),
        ("files", ("kitchen.mp4", b"mp4", "video/mp4")),
    ]

    response = client.post(
        f"/api/personas/{persona['id']}/materials/upload",
        headers=auth(token),
        files=files,
        data={"importance": "important", "user_description": "家庭 demo 资料"},
    )

    assert response.status_code == 201
    items = response.json()["items"]
    assert [item["file_type"] for item in items] == ["text", "image", "audio", "video"]
    assert all(item["parse_status"] == "succeeded" for item in items)
    assert all(item["jobs"][0]["status"] == "succeeded" for item in items)

    chunks = db_session.scalars(select(ParsedChunk)).all()
    memories = db_session.scalars(select(MemoryCard)).all()
    assert {chunk.chunk_type for chunk in chunks} >= {"text", "image", "audio", "video"}
    assert len(memories) >= 4
    assert all(memory.source_material_id for memory in memories)
    assert all(memory.source_type in {"text", "image", "audio", "video"} for memory in memories)
    assert all(memory.source_quote for memory in memories)
    assert all(memory.source_location for memory in memories)
