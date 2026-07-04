from sqlalchemy import select

from app.models.memory_card import MemoryCard
from app.models.parsed_chunk import ParsedChunk
from app.models.ai_job import AIJob
from app.services import memory_markdown
from app.services import parsing


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


def test_parse_job_records_third_party_provider_from_gateway(
    client,
    db_session,
    monkeypatch,
):
    def fake_run_gateway(capability: str, payload: dict):
        if capability == "text_parser":
            return {
                "provider_type": "third_party",
                "provider_name": "dashscope",
                "output": {
                    "chunks": [
                        {
                            "content": payload["text"],
                            "summary": "真实文本解析",
                            "source_location": "text:body",
                        }
                    ]
                },
            }
        if capability == "memory_extraction":
            return {
                "provider_type": "third_party",
                "provider_name": "dashscope",
                "output": {
                    "memories": [
                        {
                            "title": "真实抽取记忆",
                            "content": "外婆喜欢包馄饨。",
                            "category": "preference",
                            "confidence_level": "high",
                            "confidence_score": 90,
                            "source_quote": "外婆喜欢包馄饨",
                            "source_location": payload["source_location"],
                        }
                    ]
                },
            }
        raise AssertionError(f"unexpected capability {capability}")

    monkeypatch.setattr(parsing, "_run_gateway", fake_run_gateway)
    token = register_user(client, "m3-third-party@example.com")
    persona = create_persona(client, token)

    response = client.post(
        f"/api/personas/{persona['id']}/materials/manual",
        headers=auth(token),
        json={"manual_text": "外婆喜欢包馄饨。", "importance": "important"},
    )

    assert response.status_code == 201
    material = response.json()
    job = db_session.scalar(select(AIJob).where(AIJob.id == material["jobs"][0]["id"]))
    memory = db_session.scalar(select(MemoryCard))
    assert job.provider_type == "third_party"
    assert job.provider_name == "dashscope"
    assert memory.evidence_json["provider_name"] == "dashscope"


def test_parse_job_does_not_put_pending_memories_in_long_term_markdown_until_confirmed(
    client,
    db_session,
):
    token = register_user(client, "m3-markdown-parse@example.com")
    persona = create_persona(client, token)

    response = client.post(
        f"/api/personas/{persona['id']}/materials/manual",
        headers=auth(token),
        json={"manual_text": "外婆喜欢包馄饨。", "importance": "important"},
    )

    assert response.status_code == 201
    memories = db_session.scalars(select(MemoryCard)).all()
    assert memories
    long_term_path = memory_markdown.memory_context_dir(persona["id"]) / "long_term_memory.md"
    assert not long_term_path.exists()

    confirmed = client.post(f"/api/memories/{memories[0].id}/confirm", headers=auth(token))
    assert confirmed.status_code == 200

    body = long_term_path.read_text(encoding="utf-8")
    assert memories[0].id in body
    assert memories[0].content in body
