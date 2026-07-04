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
    response = client.post("/api/personas", headers=auth(token), json=persona_payload(name))
    assert response.status_code == 201
    return response.json()


def create_manual_material(client, token: str, persona_id: str) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/materials/manual",
        headers=auth(token),
        json={"manual_text": "外婆喜欢包馄饨，也常说慢慢来。", "importance": "important"},
    )
    assert response.status_code == 201
    return response.json()


def list_memories(client, token: str, persona_id: str) -> list[dict]:
    response = client.get(f"/api/personas/{persona_id}/memories", headers=auth(token))
    assert response.status_code == 200
    return response.json()["items"]


def confirm_memory(client, token: str, memory_id: str) -> dict:
    response = client.post(f"/api/memories/{memory_id}/confirm", headers=auth(token))
    assert response.status_code == 200
    return response.json()


def create_conversation(client, token: str, persona_id: str) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/conversations",
        headers=auth(token),
        json={"title": "想念外婆"},
    )
    assert response.status_code == 201
    return response.json()


def send_message(client, token: str, conversation_id: str, content: str) -> dict:
    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers=auth(token),
        json={"content": content},
    )
    assert response.status_code == 201
    return response.json()


def assert_profile_export_includes_age(body: dict, age: int = 72):
    assert body["persona"]["age"] == age
    assert {
        "field": "age",
        "value": age,
        "content": f"年龄/享年：{age}",
        "source": "persona_card",
    } in body["profile"]["basic_facts"]


def test_export_profile_returns_watermarked_profile_snapshot(client):
    token = register_user(client, "export-profile@example.com")
    other_token = register_user(client, "export-profile-other@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"])
    for memory in list_memories(client, token, persona["id"]):
        confirm_memory(client, token, memory["id"])

    response = client.get(
        f"/api/personas/{persona['id']}/export/profile",
        headers=auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert body["export_type"] == "profile"
    assert "AI 模拟" in body["watermark"]
    assert body["filename"] == f"persona-{persona['id']}-profile.json"
    assert body["persona"]["id"] == persona["id"]
    assert body["profile"]["persona_id"] == persona["id"]
    assert body["profile"]["profile_summary"]
    assert body["profile"]["trust_score"] >= 0
    assert_profile_export_includes_age(body)

    blocked = client.get(
        f"/api/personas/{persona['id']}/export/profile",
        headers=auth(other_token),
    )
    assert blocked.status_code == 404


def test_export_memories_returns_active_source_backed_memories_only(client):
    token = register_user(client, "export-memories@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"])
    create_manual_material(client, token, persona["id"])
    memories = list_memories(client, token, persona["id"])
    confirm_memory(client, token, memories[0]["id"])
    deleted_id = memories[1]["id"]
    assert client.delete(f"/api/memories/{deleted_id}", headers=auth(token)).status_code == 204

    response = client.get(
        f"/api/personas/{persona['id']}/export/memories",
        headers=auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert body["export_type"] == "memories"
    assert "AI 模拟" in body["watermark"]
    assert body["filename"] == f"persona-{persona['id']}-memories.json"
    ids = [item["id"] for item in body["items"]]
    assert memories[0]["id"] in ids
    assert deleted_id not in ids
    assert body["items"][0]["source_material_id"]
    assert body["items"][0]["source_quote"]


def test_export_conversation_returns_ordered_messages_with_citations(client):
    token = register_user(client, "export-conversation@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"])
    memory = list_memories(client, token, persona["id"])[0]
    confirm_memory(client, token, memory["id"])
    conversation = create_conversation(client, token, persona["id"])
    reply = send_message(client, token, conversation["id"], "你喜欢做什么给我吃？")

    response = client.get(
        f"/api/conversations/{conversation['id']}/export",
        headers=auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert body["export_type"] == "conversation"
    assert "AI 模拟" in body["watermark"]
    assert body["filename"] == f"conversation-{conversation['id']}.json"
    assert body["conversation"]["id"] == conversation["id"]
    assert [message["role"] for message in body["messages"]] == ["user", "persona"]
    assert body["messages"][1]["id"] == reply["id"]
    assert body["messages"][1]["citations"][0]["memory_card_id"] == memory["id"]


def test_export_conversation_rejects_cross_user_access(client):
    owner_token = register_user(client, "export-conversation-owner@example.com")
    other_token = register_user(client, "export-conversation-other@example.com")
    persona = create_persona(client, owner_token)
    conversation = create_conversation(client, owner_token, persona["id"])

    response = client.get(
        f"/api/conversations/{conversation['id']}/export",
        headers=auth(other_token),
    )

    assert response.status_code == 404
