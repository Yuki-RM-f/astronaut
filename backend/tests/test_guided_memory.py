from __future__ import annotations


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_user(client, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "passw0rd", "display_name": "Demo"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def persona_payload(name: str = "外婆") -> dict:
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
    response = client.post("/api/personas", headers=auth(token), json=persona_payload(name))
    assert response.status_code == 201
    return response.json()


def create_material(client, token: str, persona_id: str) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/materials/manual",
        headers=auth(token),
        json={"manual_text": "手动资料来源。", "importance": "important"},
    )
    assert response.status_code == 201
    return response.json()


def create_memory(
    client,
    token: str,
    persona_id: str,
    material_id: str,
    content: str,
    *,
    title: str = "线索记忆",
    category: str = "shared_event",
) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/memories",
        headers=auth(token),
        json={
            "title": title,
            "content": content,
            "category": category,
            "confidence_level": "high",
            "confidence_score": 90,
            "source_material_id": material_id,
            "source_quote": content,
            "source_location": "manual:guided-memory-test",
        },
    )
    assert response.status_code == 201
    return response.json()


def confirm_memory(client, token: str, memory_id: str) -> dict:
    response = client.post(f"/api/memories/{memory_id}/confirm", headers=auth(token))
    assert response.status_code == 200
    return response.json()


def test_regrets_candidates_use_only_reviewed_active_owned_memories(client):
    token = register_user(client, "guided-regrets@example.com")
    other_token = register_user(client, "guided-regrets-other@example.com")
    persona = create_persona(client, token)
    material = create_material(client, token, persona["id"])

    reviewed = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆一直遗憾没来得及和小铭好好道别。",
        title="没来得及道别",
    )
    confirm_memory(client, token, reviewed["id"])
    pending = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆还有一段遗憾没有审核。",
        title="未审核遗憾",
    )
    rejected = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆后悔没有说谢谢。",
        title="已拒绝遗憾",
    )
    assert client.post(f"/api/memories/{rejected['id']}/reject", headers=auth(token)).status_code == 200
    disabled = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆有一段被停用的心结。",
        title="已停用遗憾",
    )
    assert client.post(f"/api/memories/{disabled['id']}/disable", headers=auth(token)).status_code == 200
    deleted = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆删除了一段遗憾。",
        title="已删除遗憾",
    )
    assert client.delete(f"/api/memories/{deleted['id']}", headers=auth(token)).status_code == 204

    other_persona = create_persona(client, other_token, name="奶奶")
    other_material = create_material(client, other_token, other_persona["id"])
    other_memory = create_memory(
        client,
        other_token,
        other_persona["id"],
        other_material["id"],
        "奶奶遗憾没来得及道别。",
    )
    confirm_memory(client, other_token, other_memory["id"])

    response = client.post(
        f"/api/personas/{persona['id']}/guided-memory-candidates",
        headers=auth(token),
        json={"kind": "regrets"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "regrets"
    assert body["empty_reason"] is None
    assert [item["memory_card_id"] for item in body["items"]] == [reviewed["id"]]
    assert "道别" in body["items"][0]["summary"]
    assert "manual:guided-memory-test" == body["items"][0]["source_location"]
    assert pending["id"] not in str(body)
    assert rejected["id"] not in str(body)
    assert disabled["id"] not in str(body)
    assert deleted["id"] not in str(body)
    assert other_memory["id"] not in str(body)


def test_wishes_candidates_and_empty_reason(client):
    token = register_user(client, "guided-wishes@example.com")
    persona = create_persona(client, token)
    material = create_material(client, token, persona["id"])
    wish = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆一直希望小铭替她把院子里的花园继续种下去。",
        title="继续种花园",
        category="value",
    )
    confirm_memory(client, token, wish["id"])

    found = client.post(
        f"/api/personas/{persona['id']}/guided-memory-candidates",
        headers=auth(token),
        json={"kind": "wishes"},
    )
    assert found.status_code == 200
    found_body = found.json()
    assert found_body["kind"] == "wishes"
    assert found_body["items"][0]["memory_card_id"] == wish["id"]
    assert "花园" in found_body["items"][0]["suggested_user_message"]

    empty_persona = create_persona(client, token, name="爷爷")
    empty = client.post(
        f"/api/personas/{empty_persona['id']}/guided-memory-candidates",
        headers=auth(token),
        json={"kind": "wishes"},
    )
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert "已审核记忆" in empty.json()["empty_reason"]


def test_selected_guided_candidate_is_added_to_wishes_message_context_and_citations(client):
    token = register_user(client, "guided-send@example.com")
    persona = create_persona(client, token)
    material = create_material(client, token, persona["id"])
    memory = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆希望小铭以后还能继续照顾那片花园。",
        title="继续照顾花园",
    )
    confirm_memory(client, token, memory["id"])
    conversation = client.post(
        f"/api/personas/{persona['id']}/conversations",
        headers=auth(token),
        json={"title": "心愿延续系统", "context_kind": "wishes"},
    )
    assert conversation.status_code == 201

    reply = client.post(
        f"/api/conversations/{conversation.json()['id']}/messages",
        headers=auth(token),
        json={
            "content": "我想继续照顾那片花园。",
            "guided_memory_ids": [memory["id"]],
        },
    )

    assert reply.status_code == 201
    body = reply.json()
    assert body["metadata_json"]["conversation_kind"] == "wishes"
    assert body["metadata_json"]["memory_context"]["selected_memory_ids"] == [memory["id"]]
    assert body["metadata_json"]["retrieval"] == [
        {"memory_card_id": memory["id"], "source": "guided_candidate"}
    ]
    assert [citation["memory_card_id"] for citation in body["citations"]] == [memory["id"]]
