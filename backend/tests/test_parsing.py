from sqlalchemy import select

from app.models.memory_card import MemoryCard
from app.models.parsed_chunk import ParsedChunk
from app.models.ai_job import AIJob
from app.models.persona_profile import PersonaProfile
from app.models.source_material import SourceMaterial
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


def run_created_material_parse(db_session, material_body: dict) -> tuple[SourceMaterial, AIJob]:
    material = db_session.get(SourceMaterial, material_body["id"])
    assert material is not None
    job = db_session.get(AIJob, material_body["jobs"][0]["id"])
    assert job is not None
    assert material.parse_status == "pending"
    assert job.status == "pending"

    parsing.run_parse_job(db_session, material, job)
    db_session.commit()
    db_session.refresh(material)
    db_session.refresh(job)
    return material, job


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
    material_model, job = run_created_material_parse(db_session, material)
    assert material_model.parse_status == "succeeded"
    assert job.status == "succeeded"

    chunks = db_session.scalars(select(ParsedChunk)).all()
    memories = db_session.scalars(select(MemoryCard)).all()
    assert len(chunks) >= 1
    assert len(memories) >= 2
    assert all(memory.source_material_id == material["id"] for memory in memories)
    assert all(memory.source_type == "manual" for memory in memories)
    assert all(memory.source_quote for memory in memories)
    assert all(memory.source_location for memory in memories)
    assert {memory.status for memory in memories} == {"pending_review"}


def test_manual_material_parse_generates_structured_memory_document_and_trust(
    client,
    db_session,
):
    token = register_user(client, "m3-memory-document@example.com")
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
    _material_model, job = run_created_material_parse(db_session, material)
    profile = db_session.scalar(select(PersonaProfile).where(PersonaProfile.persona_id == persona["id"]))
    refreshed_persona = client.get(f"/api/personas/{persona['id']}", headers=auth(token))

    assert refreshed_persona.status_code == 200
    assert refreshed_persona.json()["trust_score"] > 0
    assert job is not None
    assert profile is not None
    assert job.output_json["profile_summary"]
    assert profile.profile_summary == job.output_json["profile_summary"]
    assert job.output_json["trust_score"] == refreshed_persona.json()["trust_score"]
    assert job.output_json["trust_level"] in {"initial", "usable", "trusted", "high_trust"}
    assert job.output_json["trust_rationale"]
    assert job.output_json["suggestions"]
    assert job.output_json["structured_memory_document_json"]["modules"]
    assert "## 资料来源" in job.output_json["structured_memory_md"]
    assert "## 待用户确认" in job.output_json["structured_memory_md"]


def test_parse_job_uses_strict_module_json_for_memory_cards(
    client,
    db_session,
    monkeypatch,
):
    seen_memory_payload: dict = {}

    def fake_run_gateway(capability: str, payload: dict):
        if capability == "text_parser":
            return {
                "provider_type": "local",
                "provider_name": "mock",
                "output": {
                    "chunks": [
                        {
                            "content": payload["text"],
                            "summary": "文本解析",
                            "source_location": "manual:body",
                        }
                    ]
                },
            }
        if capability == "memory_extraction":
            seen_memory_payload.update(payload)
            return {
                "provider_type": "third_party",
                "provider_name": "dashscope",
                "output": {
                    "structured_memory_json": {
                        "source_material_id": payload["source_material_id"],
                        "modules": {
                            "basic_fact": [
                                {
                                    "title": "年龄",
                                    "content": "外婆享年 72 岁。",
                                    "category": "basic_fact",
                                    "confidence_level": "high",
                                    "confidence_score": 90,
                                    "source_quote": "享年 72 岁",
                                    "source_location": payload["source_location"],
                                }
                            ],
                            "relationship": [
                                {
                                    "title": "称呼",
                                    "content": "外婆会叫用户小铭。",
                                    "category": "relationship",
                                    "confidence_level": "medium",
                                    "confidence_score": 78,
                                    "source_quote": "小铭",
                                    "source_location": payload["source_location"],
                                }
                            ],
                            "preference": [],
                            "habit": [],
                            "expression_style": [],
                            "shared_event": [],
                        },
                        "unclassified": [
                            {
                                "title": "缺少证据",
                                "content": "这条没有来源摘录，不能入库。",
                            }
                        ],
                        "warnings": ["跳过缺少来源摘录的候选记忆"],
                    }
                },
            }
        if capability == "memory_document_generation":
            return {
                "provider_type": "third_party",
                "provider_name": "dashscope",
                "output": {
                    "structured_memory_md": "## 资料来源\n- manual\n\n## 基础信息\n- 外婆享年 72 岁。\n\n## 人物关系\n- 外婆会叫用户小铭。\n\n## 兴趣偏好\n- 无\n\n## 生活习惯\n- 无\n\n## 表达习惯\n- 无\n\n## 共同经历\n- 无\n\n## 待用户确认\n- 无",
                    "profile_summary": "外婆享年 72 岁，会叫用户小铭。",
                    "trust_score": 61,
                    "trust_level": "trusted",
                    "trust_rationale": "来自严格模块解析。",
                    "suggestions": ["继续补充资料"],
                },
            }
        raise AssertionError(f"unexpected capability {capability}")

    monkeypatch.setattr(parsing, "_run_gateway", fake_run_gateway)
    token = register_user(client, "m3-strict-json@example.com")
    persona = create_persona(client, token)

    response = client.post(
        f"/api/personas/{persona['id']}/materials/manual",
        headers=auth(token),
        json={"manual_text": "外婆享年 72 岁，会叫我小铭。", "importance": "important"},
    )

    assert response.status_code == 201
    material = response.json()
    material_model, job = run_created_material_parse(db_session, material)
    memories = db_session.scalars(select(MemoryCard)).all()

    assert material_model.parse_status == "succeeded"
    assert job.output_json["structured_memory_json"]["modules"]["basic_fact"]
    assert job.output_json["structured_memory_json"]["warnings"]
    assert {memory.category for memory in memories} == {"basic_fact", "relationship"}
    assert all(memory.evidence_json["structured_memory_source"] == "memory_extraction" for memory in memories)
    assert seen_memory_payload["persona_card"]["name"] == "外婆"
    assert seen_memory_payload["source_material"]["id"] == material["id"]
    assert seen_memory_payload["parsed_chunk"]["content"] == "外婆享年 72 岁，会叫我小铭。"


def test_parse_job_fails_when_memory_extraction_lacks_strict_json(
    client,
    db_session,
    monkeypatch,
):
    def fake_run_gateway(capability: str, payload: dict):
        if capability == "text_parser":
            return {
                "provider_type": "local",
                "provider_name": "mock",
                "output": {
                    "chunks": [
                        {
                            "content": payload["text"],
                            "summary": "文本解析",
                            "source_location": "manual:body",
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
                            "title": "旧格式",
                            "content": "旧格式不再作为事实来源。",
                            "category": "preference",
                            "confidence_level": "medium",
                            "confidence_score": 70,
                            "source_quote": "旧格式",
                            "source_location": payload["source_location"],
                        }
                    ]
                },
            }
        raise AssertionError(f"unexpected capability {capability}")

    monkeypatch.setattr(parsing, "_run_gateway", fake_run_gateway)
    token = register_user(client, "m3-strict-json-failed@example.com")
    persona = create_persona(client, token)

    response = client.post(
        f"/api/personas/{persona['id']}/materials/manual",
        headers=auth(token),
        json={"manual_text": "外婆喜欢包馄饨。", "importance": "important"},
    )

    assert response.status_code == 201
    material = response.json()
    material_model, job = run_created_material_parse(db_session, material)
    memories = db_session.scalars(select(MemoryCard)).all()

    assert material_model.parse_status == "failed"
    assert job.status == "failed"
    assert "structured_memory_json" in job.error_message
    assert memories == []


def test_parse_job_renders_memory_document_from_cards_when_provider_json_fails(
    client,
    db_session,
    monkeypatch,
):
    def fake_run_gateway(capability: str, payload: dict):
        if capability == "text_parser":
            return {
                "provider_type": "local",
                "provider_name": "mock",
                "output": {
                    "chunks": [
                        {
                            "content": payload["text"],
                            "summary": "文本解析",
                            "source_location": "manual:body",
                        }
                    ]
                },
            }
        if capability == "memory_extraction":
            return {
                "provider_type": "third_party",
                "provider_name": "dashscope",
                "output": {
                    "structured_memory_json": {
                        "source_material_id": payload["source_material_id"],
                        "modules": {
                            "basic_fact": [],
                            "relationship": [
                                {
                                    "title": "称呼",
                                    "content": "外婆会叫用户小铭。",
                                    "category": "relationship",
                                    "confidence_level": "high",
                                    "confidence_score": 88,
                                    "source_quote": "小铭",
                                    "source_location": payload["source_location"],
                                }
                            ],
                            "preference": [],
                            "habit": [],
                            "expression_style": [],
                            "shared_event": [],
                        },
                        "unclassified": [],
                        "warnings": [],
                    }
                },
            }
        if capability == "memory_document_generation":
            raise RuntimeError(
                "MiniMax memory document response must be strict JSON after 3 repair attempts"
            )
        raise AssertionError(f"unexpected capability {capability}")

    monkeypatch.setattr(parsing, "_run_gateway", fake_run_gateway)
    token = register_user(client, "m3-memory-document-partial@example.com")
    persona = create_persona(client, token)

    response = client.post(
        f"/api/personas/{persona['id']}/materials/manual",
        headers=auth(token),
        json={"manual_text": "外婆会叫我小铭。", "importance": "important"},
    )

    assert response.status_code == 201
    material = response.json()
    material_model, job = run_created_material_parse(db_session, material)
    memories = db_session.scalars(select(MemoryCard)).all()
    profile = db_session.scalar(
        select(PersonaProfile).where(PersonaProfile.persona_id == persona["id"])
    )
    refreshed_persona = client.get(f"/api/personas/{persona['id']}", headers=auth(token))

    assert material_model.parse_status == "succeeded"
    assert job.status == "succeeded"
    assert job.error_message is None
    assert job.output_json["memory_card_ids"] == [memory.id for memory in memories]
    assert "memory_document_error" not in job.output_json
    assert "memory_document_warning" not in job.output_json
    assert job.output_json["memory_document_generation_status"] == "fallback"
    assert "MiniMax memory document response must be strict JSON" in job.output_json[
        "memory_document_provider_error"
    ]
    assert job.output_json["structured_memory_document_json"]["modules"]["relationship"][0][
        "content"
    ] == "外婆会叫用户小铭。"
    assert "## 人物关系" in job.output_json["structured_memory_md"]
    assert "外婆会叫用户小铭。" in job.output_json["structured_memory_md"]
    assert {memory.status for memory in memories} == {"pending_review"}
    assert profile is not None
    assert profile.profile_summary == job.output_json["profile_summary"]
    assert refreshed_persona.json()["trust_score"] == job.output_json["trust_score"]
    assert refreshed_persona.json()["trust_score"] > 0


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
    assert all(item["parse_status"] == "pending" for item in items)

    parsed_items = [run_created_material_parse(db_session, item) for item in items]
    assert all(material.parse_status == "succeeded" for material, _job in parsed_items)
    assert all(job.status == "succeeded" for _material, job in parsed_items)

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
                    "structured_memory_json": {
                        "source_material_id": payload["source_material_id"],
                        "modules": {
                            "basic_fact": [],
                            "relationship": [],
                            "preference": [
                                {
                                    "title": "真实抽取记忆",
                                    "content": "外婆喜欢包馄饨。",
                                    "category": "preference",
                                    "confidence_level": "high",
                                    "confidence_score": 90,
                                    "source_quote": "外婆喜欢包馄饨",
                                    "source_location": payload["source_location"],
                                }
                            ],
                            "habit": [],
                            "expression_style": [],
                            "shared_event": [],
                        },
                        "unclassified": [],
                        "warnings": [],
                    }
                },
            }
        if capability == "memory_document_generation":
            return {
                "provider_type": "third_party",
                "provider_name": "dashscope",
                "output": {
                    "structured_memory_md": "## 资料来源\n- manual\n\n## 基础信息\n- 无\n\n## 人物关系\n- 无\n\n## 兴趣偏好\n- 外婆喜欢包馄饨。\n\n## 生活习惯\n- 无\n\n## 表达习惯\n- 无\n\n## 共同经历\n- 无\n\n## 待用户确认\n- 真实抽取记忆",
                    "profile_summary": "外婆喜欢包馄饨。",
                    "trust_score": 64,
                    "trust_level": "trusted",
                    "trust_rationale": "来自第三方解析和记忆文档生成链路。",
                    "suggestions": ["继续补充多模态资料"],
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
    _material_model, job = run_created_material_parse(db_session, material)
    memory = db_session.scalar(select(MemoryCard))
    assert job.provider_type == "third_party"
    assert job.provider_name == "dashscope"
    assert memory.evidence_json["provider_name"] == "dashscope"
    assert job.output_json["structured_memory_md"]
    assert job.output_json["profile_summary"] == "外婆喜欢包馄饨。"
    assert job.output_json["trust_score"] > 0


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
    run_created_material_parse(db_session, response.json())
    memories = db_session.scalars(select(MemoryCard)).all()
    assert memories
    long_term_path = memory_markdown.memory_context_dir(persona["id"]) / "long_term_memory.md"
    assert not long_term_path.exists()

    confirmed = client.post(f"/api/memories/{memories[0].id}/confirm", headers=auth(token))
    assert confirmed.status_code == 200

    body = long_term_path.read_text(encoding="utf-8")
    assert memories[0].id in body
    assert memories[0].content in body
