from sqlalchemy import select

from app.models.ai_job import AIJob
from app.models.memory_card import MemoryCard
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


def create_manual_material(client, token: str, persona_id: str, db_session=None) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/materials/manual",
        headers=auth(token),
        json={
            "manual_text": "外婆喜欢包馄饨。她常说慢慢来。",
            "importance": "very_important",
        },
    )
    assert response.status_code == 201
    body = response.json()
    if db_session is not None:
        material = db_session.get(SourceMaterial, body["id"])
        job = db_session.get(AIJob, body["jobs"][0]["id"])
        assert material is not None
        assert job is not None
        parsing.run_parse_job(db_session, material, job)
        db_session.commit()
    return body


def list_memories(client, token: str, persona_id: str, query: str = "") -> list[dict]:
    response = client.get(
        f"/api/personas/{persona_id}/memories{query}",
        headers=auth(token),
    )
    assert response.status_code == 200
    return response.json()["items"]


def test_memory_list_detail_and_filters_are_user_scoped(client, db_session):
    owner_token = register_user(client, "memory-owner@example.com")
    other_token = register_user(client, "memory-other@example.com")
    persona = create_persona(client, owner_token)
    create_manual_material(client, owner_token, persona["id"], db_session)

    items = list_memories(client, owner_token, persona["id"])
    assert len(items) >= 2
    memory = items[0]
    assert memory["source_material_id"]
    assert memory["source_quote"]
    assert memory["source_location"]
    assert memory["is_important"] is False

    detail = client.get(f"/api/memories/{memory['id']}", headers=auth(owner_token))
    assert detail.status_code == 200
    assert detail.json()["id"] == memory["id"]

    assert (
        client.get(
            f"/api/personas/{persona['id']}/memories",
            headers=auth(other_token),
        ).status_code
        == 404
    )
    assert (
        client.get(f"/api/memories/{memory['id']}", headers=auth(other_token)).status_code
        == 404
    )

    by_status = list_memories(client, owner_token, persona["id"], "?status=pending_review")
    assert by_status
    assert {item["status"] for item in by_status} == {"pending_review"}

    by_category = list_memories(
        client,
        owner_token,
        persona["id"],
        f"?category={memory['category']}",
    )
    assert by_category
    assert {item["category"] for item in by_category} == {memory["category"]}

    by_confidence = list_memories(
        client,
        owner_token,
        persona["id"],
        f"?confidence_level={memory['confidence_level']}",
    )
    assert by_confidence
    assert {item["confidence_level"] for item in by_confidence} == {
        memory["confidence_level"]
    }


def test_memory_importance_star_can_be_toggled_and_is_user_scoped(client, db_session):
    owner_token = register_user(client, "memory-important-owner@example.com")
    other_token = register_user(client, "memory-important-other@example.com")
    persona = create_persona(client, owner_token)
    create_manual_material(client, owner_token, persona["id"], db_session)
    memory = list_memories(client, owner_token, persona["id"])[0]

    marked = client.patch(
        f"/api/memories/{memory['id']}",
        headers=auth(owner_token),
        json={"is_important": True},
    )

    assert marked.status_code == 200
    assert marked.json()["is_important"] is True
    stored = db_session.scalar(select(MemoryCard).where(MemoryCard.id == memory["id"]))
    assert stored is not None
    assert stored.is_important is True

    assert (
        client.patch(
            f"/api/memories/{memory['id']}",
            headers=auth(other_token),
            json={"is_important": False},
        ).status_code
        == 404
    )

    unmarked = client.patch(
        f"/api/memories/{memory['id']}",
        headers=auth(owner_token),
        json={"is_important": False},
    )
    assert unmarked.status_code == 200
    assert unmarked.json()["is_important"] is False


def test_confirm_edit_disable_reject_and_delete_memory(client, db_session):
    token = register_user(client, "memory-audit@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"], db_session)
    memory = list_memories(client, token, persona["id"])[0]
    original_source = {
        "source_material_id": memory["source_material_id"],
        "parsed_chunk_id": memory["parsed_chunk_id"],
        "source_type": memory["source_type"],
        "source_quote": memory["source_quote"],
        "source_location": memory["source_location"],
        "evidence_json": memory["evidence_json"],
    }

    confirmed = client.post(f"/api/memories/{memory['id']}/confirm", headers=auth(token))
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"

    corrected = client.patch(
        f"/api/memories/{memory['id']}",
        headers=auth(token),
        json={"title": "修正后的偏好", "content": "外婆喜欢包馄饨，不是饺子。"},
    )
    assert corrected.status_code == 200
    body = corrected.json()
    assert body["title"] == "修正后的偏好"
    assert body["content"] == "外婆喜欢包馄饨，不是饺子。"
    assert body["status"] == "corrected"
    assert body["user_correction"] == "外婆喜欢包馄饨，不是饺子。"
    for field, value in original_source.items():
        assert body[field] == value

    disabled = client.post(f"/api/memories/{memory['id']}/disable", headers=auth(token))
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"

    rejected = client.post(f"/api/memories/{memory['id']}/reject", headers=auth(token))
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    deleted = client.delete(f"/api/memories/{memory['id']}", headers=auth(token))
    assert deleted.status_code == 204
    assert client.get(f"/api/memories/{memory['id']}", headers=auth(token)).status_code == 404
    assert memory["id"] not in {
        item["id"] for item in list_memories(client, token, persona["id"])
    }


def test_confirm_memory_refreshes_profile_without_recalculating_trust(client, db_session):
    token = register_user(client, "memory-profile-refresh@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"], db_session)
    memory = list_memories(client, token, persona["id"])[0]

    before = client.get(f"/api/personas/{persona['id']}", headers=auth(token))
    assert before.status_code == 200
    assert before.json()["trust_score"] > 0

    confirmed = client.post(f"/api/memories/{memory['id']}/confirm", headers=auth(token))
    assert confirmed.status_code == 200

    after = client.get(f"/api/personas/{persona['id']}", headers=auth(token))
    assert after.status_code == 200
    assert after.json()["trust_score"] == before.json()["trust_score"]


def test_manual_memory_requires_source_fields(client):
    token = register_user(client, "memory-source-required@example.com")
    persona = create_persona(client, token)

    response = client.post(
        f"/api/personas/{persona['id']}/memories",
        headers=auth(token),
        json={"title": "No source", "content": "Missing source", "category": "unknown"},
    )

    assert response.status_code == 422


def test_manual_memory_enforces_prd_enums_and_source_ownership(client):
    token = register_user(client, "memory-create@example.com")
    other_token = register_user(client, "memory-create-other@example.com")
    persona = create_persona(client, token)
    other_persona = create_persona(client, other_token)
    material = create_manual_material(client, token, persona["id"])
    other_material = create_manual_material(client, other_token, other_persona["id"])

    valid_payload = {
        "title": "手动补充记忆",
        "content": "外婆喜欢在周末包馄饨。",
        "category": "preference",
        "confidence_level": "high",
        "confidence_score": 90,
        "source_material_id": material["id"],
        "source_quote": "外婆喜欢在周末包馄饨。",
        "source_location": "manual:body#supplement",
    }

    created = client.post(
        f"/api/personas/{persona['id']}/memories",
        headers=auth(token),
        json=valid_payload,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "pending_review"
    assert body["created_by"] == "user"
    assert body["source_type"] == "manual"

    for field, value in [
        ("category", "not_a_category"),
        ("confidence_level", "certain"),
        ("status", "approved"),
    ]:
        payload = {**valid_payload, field: value}
        response = client.post(
            f"/api/personas/{persona['id']}/memories",
            headers=auth(token),
            json=payload,
        )
        assert response.status_code == 422

    wrong_source = client.post(
        f"/api/personas/{persona['id']}/memories",
        headers=auth(token),
        json={**valid_payload, "source_material_id": other_material["id"]},
    )
    assert wrong_source.status_code == 404


def test_manual_memory_create_confirm_and_content_update_refresh_long_term_markdown(
    client,
    db_session,
):
    token = register_user(client, "memory-markdown-refresh@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    payload = {
        "title": "manual markdown memory",
        "content": "original memory content",
        "category": "preference",
        "confidence_level": "high",
        "confidence_score": 90,
        "source_material_id": material["id"],
        "source_quote": "original memory content",
        "source_location": "manual:body#markdown",
    }

    created = client.post(
        f"/api/personas/{persona['id']}/memories",
        headers=auth(token),
        json=payload,
    )

    assert created.status_code == 201
    memory_id = created.json()["id"]
    memory = db_session.scalar(select(MemoryCard).where(MemoryCard.id == memory_id))
    long_term_path = memory_markdown.memory_context_dir(persona["id"]) / "long_term_memory.md"
    assert memory is not None
    assert not long_term_path.exists() or memory_id not in long_term_path.read_text(encoding="utf-8")

    confirmed = client.post(f"/api/memories/{memory_id}/confirm", headers=auth(token))
    assert confirmed.status_code == 200
    body = long_term_path.read_text(encoding="utf-8")
    assert memory_id in body
    assert "original memory content" in body

    corrected = client.patch(
        f"/api/memories/{memory_id}",
        headers=auth(token),
        json={"content": "corrected memory content"},
    )

    assert corrected.status_code == 200
    db_session.refresh(memory)
    body = long_term_path.read_text(encoding="utf-8")
    assert memory_id in body
    assert "corrected memory content" in body
    assert "- content: original memory content" not in body
