from pathlib import Path

from app.services import memory_markdown


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
        "emotional_style": "安慰、鼓励",
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
        json={
            "manual_text": "外婆喜欢包馄饨。她常说慢慢来。",
            "importance": "very_important",
        },
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
    title: str,
    status: str = "pending_review",
    source_location: str = "manual:body#memory",
) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/memories",
        headers=auth(token),
        json={
            "title": title,
            "content": content,
            "category": "preference",
            "confidence_level": "high",
            "confidence_score": 90,
            "source_material_id": material_id,
            "source_quote": content,
            "source_location": source_location,
            "status": status,
        },
    )
    assert response.status_code == 201
    return response.json()


def long_term_path(persona_id: str) -> Path:
    return memory_markdown.memory_context_dir(persona_id) / "long_term_memory.md"


def short_term_path(persona_id: str) -> Path:
    return memory_markdown.memory_context_dir(persona_id) / "short_term_memory.md"


def short_term_kind_path(persona_id: str, kind: str) -> Path:
    return memory_markdown.memory_context_dir(persona_id) / f"short_term_memory_{kind}.md"


def test_long_term_markdown_includes_only_confirmed_and_corrected_active_memories(client):
    token = register_user(client, "memory-md-long@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    confirmed = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢包馄饨给小铭吃。",
        title="馄饨偏好",
    )
    pending = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "这条待审核记忆不能进入长期上下文。",
        title="待审核记忆",
    )
    rejected = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "这条拒绝记忆不能进入长期上下文。",
        title="拒绝记忆",
    )
    disabled = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "这条禁用记忆不能进入长期上下文。",
        title="禁用记忆",
    )
    deleted = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "这条删除记忆不能进入长期上下文。",
        title="删除记忆",
    )

    assert client.post(f"/api/memories/{confirmed['id']}/confirm", headers=auth(token)).status_code == 200
    assert client.post(f"/api/memories/{rejected['id']}/reject", headers=auth(token)).status_code == 200
    assert client.post(f"/api/memories/{disabled['id']}/disable", headers=auth(token)).status_code == 200
    assert client.delete(f"/api/memories/{deleted['id']}", headers=auth(token)).status_code == 204

    body = long_term_path(persona["id"]).read_text(encoding="utf-8")

    assert confirmed["id"] in body
    assert "馄饨偏好" in body
    assert "外婆喜欢包馄饨给小铭吃。" in body
    assert "manual:body#memory" in body
    assert pending["id"] not in body
    assert rejected["id"] not in body
    assert disabled["id"] not in body
    assert deleted["id"] not in body


def test_long_term_markdown_marks_and_prioritizes_important_memories(client):
    token = register_user(client, "memory-md-important@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    important = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "important memory content",
        title="important memory",
    )
    marked = client.patch(
        f"/api/memories/{important['id']}",
        headers=auth(token),
        json={"is_important": True},
    )
    assert marked.status_code == 200
    assert client.post(f"/api/memories/{important['id']}/confirm", headers=auth(token)).status_code == 200

    ordinary = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "ordinary memory content",
        title="ordinary memory",
    )
    assert client.post(f"/api/memories/{ordinary['id']}/confirm", headers=auth(token)).status_code == 200

    body = long_term_path(persona["id"]).read_text(encoding="utf-8")

    assert "- important: true" in body
    assert body.index(important["id"]) < body.index(ordinary["id"])


def test_long_term_markdown_refreshes_after_edit_correction_and_delete(client):
    token = register_user(client, "memory-md-refresh@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢包饺子给小铭吃。",
        title="旧偏好",
    )

    assert client.post(f"/api/memories/{memory['id']}/confirm", headers=auth(token)).status_code == 200
    edited = client.patch(
        f"/api/memories/{memory['id']}",
        headers=auth(token),
        json={"title": "修正后的偏好", "content": "外婆喜欢包馄饨给小铭吃。"},
    )
    assert edited.status_code == 200

    body = long_term_path(persona["id"]).read_text(encoding="utf-8")
    assert memory["id"] in body
    assert "修正后的偏好" in body
    assert "外婆喜欢包馄饨给小铭吃。" in body
    assert "- content: 外婆喜欢包饺子给小铭吃。" not in body

    deleted = client.delete(f"/api/memories/{memory['id']}", headers=auth(token))
    assert deleted.status_code == 204

    body = long_term_path(persona["id"]).read_text(encoding="utf-8")
    assert memory["id"] not in body
    assert "外婆喜欢包馄饨给小铭吃。" not in body


def test_short_term_markdown_aggregates_messages_across_persona_conversations(client):
    token = register_user(client, "memory-md-short@example.com")
    persona = create_persona(client, token)
    first_conversation = client.post(
        f"/api/personas/{persona['id']}/conversations",
        headers=auth(token),
        json={"title": "第一次"},
    )
    assert first_conversation.status_code == 201
    second_conversation = client.post(
        f"/api/personas/{persona['id']}/conversations",
        headers=auth(token),
        json={"title": "第二次"},
    )
    assert second_conversation.status_code == 201

    first_reply = client.post(
        f"/api/conversations/{first_conversation.json()['id']}/messages",
        headers=auth(token),
        json={"content": "今天我想你了。"},
    )
    assert first_reply.status_code == 201
    second_reply = client.post(
        f"/api/conversations/{second_conversation.json()['id']}/messages",
        headers=auth(token),
        json={"content": "你还记得我昨天说想你吗？"},
    )
    assert second_reply.status_code == 201

    body = short_term_path(persona["id"]).read_text(encoding="utf-8")
    assert "## 压缩摘要" in body
    assert "## 最近消息" in body
    assert "今天我想你了。" in body
    assert "你还记得我昨天说想你吗？" in body


def test_short_term_markdown_can_scope_to_guided_conversation_kind(client):
    token = register_user(client, "memory-md-short-kind@example.com")
    persona = create_persona(client, token)
    chat_conversation = client.post(
        f"/api/personas/{persona['id']}/conversations",
        headers=auth(token),
        json={"title": "普通对话", "kind": "chat"},
    )
    assert chat_conversation.status_code == 201
    regrets_conversation = client.post(
        f"/api/personas/{persona['id']}/conversations",
        headers=auth(token),
        json={"title": "遗憾对话室", "kind": "regrets"},
    )
    assert regrets_conversation.status_code == 201

    chat_reply = client.post(
        f"/api/conversations/{chat_conversation.json()['id']}/messages",
        headers=auth(token),
        json={"content": "浏览器烟测消息"},
    )
    assert chat_reply.status_code == 201
    regrets_reply = client.post(
        f"/api/conversations/{regrets_conversation.json()['id']}/messages",
        headers=auth(token),
        json={"content": "有些以前没说的话想慢慢说。"},
    )
    assert regrets_reply.status_code == 201

    chat_body = short_term_path(persona["id"]).read_text(encoding="utf-8")
    regrets_body = short_term_kind_path(persona["id"], "regrets").read_text(encoding="utf-8")

    assert "浏览器烟测消息" in chat_body
    assert "有些以前没说的话想慢慢说。" not in chat_body
    assert "有些以前没说的话想慢慢说。" in regrets_body
    assert "浏览器烟测消息" not in regrets_body
