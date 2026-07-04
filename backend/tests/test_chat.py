from sqlalchemy import select

from app.models.conversation import Conversation, Message, MessageCitation
from app.models.memory_card import MemoryCard
from app.models.persona import Persona
from app.services import chat as chat_service
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


def create_manual_material(
    client,
    token: str,
    persona_id: str,
    manual_text: str = "这是一段来源占位。",
) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/materials/manual",
        headers=auth(token),
        json={"manual_text": manual_text, "importance": "important"},
    )
    assert response.status_code == 201
    return response.json()


def upload_audio_material(
    client,
    token: str,
    persona_id: str,
    user_description: str = "你以前喜欢做什么给我吃？",
) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/materials/upload",
        headers=auth(token),
        files=[("files", ("question.mp3", b"voice-question", "audio/mpeg"))],
        data={"importance": "important", "user_description": user_description},
    )
    assert response.status_code == 201
    return response.json()["items"][0]


def create_manual_source_material(client, token: str, persona_id: str) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/materials/manual",
        headers=auth(token),
        json={"manual_text": "这不是音频。", "importance": "normal"},
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
    title: str = "手动记忆",
    category: str = "preference",
    source_location: str = "manual:chat-test",
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
            "source_location": source_location,
        },
    )
    assert response.status_code == 201
    return response.json()


def confirm_memory(client, token: str, memory_id: str) -> dict:
    response = client.post(f"/api/memories/{memory_id}/confirm", headers=auth(token))
    assert response.status_code == 200
    return response.json()


def create_conversation(client, token: str, persona_id: str, title: str = "想念外婆") -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/conversations",
        headers=auth(token),
        json={"title": title},
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


def test_create_and_list_conversations_are_user_scoped(client):
    owner_token = register_user(client, "chat-owner@example.com")
    other_token = register_user(client, "chat-other@example.com")
    persona = create_persona(client, owner_token)

    created = create_conversation(client, owner_token, persona["id"])
    assert created["title"] == "想念外婆"
    assert created["persona_id"] == persona["id"]

    listed = client.get(
        f"/api/personas/{persona['id']}/conversations",
        headers=auth(owner_token),
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [created["id"]]

    blocked = client.get(
        f"/api/personas/{persona['id']}/conversations",
        headers=auth(other_token),
    )
    assert blocked.status_code == 404


def test_delete_conversation_soft_deletes_messages_and_citations(client, db_session):
    token = register_user(client, "chat-delete@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢包馄饨给小铭吃。",
    )
    confirm_memory(client, token, memory["id"])
    conversation = create_conversation(client, token, persona["id"])
    reply = send_message(client, token, conversation["id"], "你以前喜欢做什么给我吃？")

    messages = client.get(
        f"/api/conversations/{conversation['id']}/messages",
        headers=auth(token),
    )
    assert messages.status_code == 200
    user_message_id = messages.json()["items"][0]["id"]
    persona_message_id = reply["id"]
    citation_id = reply["citations"][0]["id"]

    deleted = client.delete(f"/api/conversations/{conversation['id']}", headers=auth(token))

    assert deleted.status_code == 204
    listed = client.get(
        f"/api/personas/{persona['id']}/conversations",
        headers=auth(token),
    )
    assert listed.status_code == 200
    assert listed.json()["items"] == []
    assert (
        client.get(
            f"/api/conversations/{conversation['id']}/messages",
            headers=auth(token),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/conversations/{conversation['id']}/export",
            headers=auth(token),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/messages/{persona_message_id}/citations",
            headers=auth(token),
        ).status_code
        == 404
    )

    db_session.expire_all()
    for model, row_id in [
        (Conversation, conversation["id"]),
        (Message, user_message_id),
        (Message, persona_message_id),
        (MessageCitation, citation_id),
    ]:
        row = db_session.get(model, row_id)
        assert row is not None
        assert row.deleted_at is not None, model.__name__


def test_send_text_message_creates_first_person_reply_and_citations(client):
    token = register_user(client, "chat-send@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢包馄饨给小铭吃。",
    )
    confirm_memory(client, token, memory["id"])
    conversation = create_conversation(client, token, persona["id"])

    reply = send_message(client, token, conversation["id"], "你以前喜欢做什么给我吃？")

    assert reply["role"] == "persona"
    assert "我" in reply["content"]
    assert "小铭" in reply["content"]
    assert "馄饨" in reply["content"]
    assert "AI 助手" not in reply["content"]
    assert "语言模型" not in reply["content"]
    assert "我真的回来了" not in reply["content"]
    assert reply["metadata_json"]["provider"] == "mock"
    assert reply["metadata_json"]["capability"] == "chat_llm"
    assert reply["metadata_json"]["memory_context"]["source"] == "memory_markdown"
    assert reply["metadata_json"]["retrieval"][0]["source"] == "memory_markdown"
    assert reply["citations"]
    assert reply["citations"][0]["memory_card_id"] == memory["id"]
    assert reply["citations"][0]["quote"] == "外婆喜欢包馄饨给小铭吃。"

    messages = client.get(
        f"/api/conversations/{conversation['id']}/messages",
        headers=auth(token),
    )
    assert messages.status_code == 200
    assert [item["role"] for item in messages.json()["items"]] == ["user", "persona"]


def test_send_text_message_sanitizes_real_llm_reply(client, monkeypatch):
    class FakeGateway:
        async def run(self, capability, payload):
            assert capability == "chat_llm"
            return {
                "provider_type": "third_party",
                "provider_name": "minimax",
                "capability": capability,
                "status": "succeeded",
                "input": payload,
                "output": {
                    "reply_text": "SECRET Child, I remember making wontons.",
                    "used_memory_ids": payload["used_memory_ids"],
                },
            }

    monkeypatch.setattr(chat_service, "ProviderGateway", lambda: FakeGateway())
    token = register_user(client, "chat-real-llm-sanitize@example.com")
    payload = persona_payload()
    payload["forbidden_expressions"] = 'Do not say "SECRET"'
    created = client.post("/api/personas", headers=auth(token), json=payload)
    assert created.status_code == 201
    persona = created.json()
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "Grandma liked making wontons.",
    )
    confirm_memory(client, token, memory["id"])
    conversation = create_conversation(client, token, persona["id"])

    reply = send_message(client, token, conversation["id"], "What did you like cooking?")

    assert reply["metadata_json"]["provider"] == "minimax"
    assert "SECRET" not in reply["content"]
    assert "Child, I remember making wontons." in reply["content"]


def test_send_text_message_strips_model_thinking_from_real_llm_reply(
    client,
    db_session,
    monkeypatch,
):
    class FakeGateway:
        async def run(self, capability, payload):
            assert capability == "chat_llm"
            return {
                "provider_type": "third_party",
                "provider_name": "minimax",
                "capability": capability,
                "status": "succeeded",
                "input": payload,
                "output": {
                    "reply_text": (
                        "<think>The user is greeting me as 孙子, so I should analyze "
                        "the role privately.</think>\n\n小铭，爷爷听见你了，今天慢慢说。"
                    ),
                    "used_memory_ids": payload["used_memory_ids"],
                },
            }

    monkeypatch.setattr(chat_service, "ProviderGateway", lambda: FakeGateway())
    token = register_user(client, "chat-real-llm-thinking@example.com")
    persona = create_persona(client, token, name="爷爷")
    conversation = create_conversation(client, token, persona["id"])

    reply = send_message(client, token, conversation["id"], "你好")

    assert reply["metadata_json"]["provider"] == "minimax"
    assert "<think>" not in reply["content"]
    assert "The user is greeting me" not in reply["content"]
    assert "小铭，爷爷听见你了，今天慢慢说。" in reply["content"]

    db_session.expire_all()
    saved = db_session.get(Message, reply["id"])
    assert saved is not None
    assert "<think>" not in saved.content
    assert "The user is greeting me" not in saved.content


def test_list_messages_strips_model_thinking_from_existing_persona_message(
    client,
    db_session,
):
    token = register_user(client, "chat-list-thinking@example.com")
    persona = create_persona(client, token)
    conversation = create_conversation(client, token, persona["id"])
    leaked_message = Message(
        conversation_id=conversation["id"],
        role="persona",
        content="<think>private model reasoning</think>\n\n小铭，今天慢慢来。",
        metadata_json={"provider": "minimax", "capability": "chat_llm"},
    )
    db_session.add(leaked_message)
    db_session.commit()

    response = client.get(
        f"/api/conversations/{conversation['id']}/messages",
        headers=auth(token),
    )

    assert response.status_code == 200
    content = response.json()["items"][0]["content"]
    assert "<think>" not in content
    assert "private model reasoning" not in content
    assert content == "小铭，今天慢慢来。"


def test_corrected_memory_outranks_confirmed_memory(client):
    token = register_user(client, "chat-corrected-priority@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    old_memory = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢包饺子给小铭吃。",
    )
    confirm_memory(client, token, old_memory["id"])
    corrected_source = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢包馄饨给小铭吃。",
    )
    corrected = client.patch(
        f"/api/memories/{corrected_source['id']}",
        headers=auth(token),
        json={"content": "外婆喜欢包馄饨给小铭吃。"},
    )
    assert corrected.status_code == 200
    assert corrected.json()["status"] == "corrected"
    conversation = create_conversation(client, token, persona["id"])

    reply = send_message(client, token, conversation["id"], "你喜欢做什么给我吃？")

    assert "馄饨" in reply["content"]
    assert "饺子" not in reply["content"]
    assert reply["citations"][0]["memory_card_id"] == corrected_source["id"]


def test_inactive_and_deleted_memories_are_not_cited(client):
    token = register_user(client, "chat-inactive@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    rejected = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢做红烧鱼。",
    )
    disabled = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢做糖醋鱼。",
    )
    deleted = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢做清蒸鱼。",
    )
    assert client.post(f"/api/memories/{rejected['id']}/reject", headers=auth(token)).status_code == 200
    assert client.post(f"/api/memories/{disabled['id']}/disable", headers=auth(token)).status_code == 200
    assert client.delete(f"/api/memories/{deleted['id']}", headers=auth(token)).status_code == 204
    conversation = create_conversation(client, token, persona["id"])

    reply = send_message(client, token, conversation["id"], "你喜欢做什么鱼？")

    assert "记不太清" in reply["content"]
    assert reply["citations"] == []


def test_low_evidence_question_gently_admits_uncertainty(client):
    token = register_user(client, "chat-low-evidence@example.com")
    persona = create_persona(client, token)
    conversation = create_conversation(client, token, persona["id"])

    reply = send_message(client, token, conversation["id"], "你最喜欢哪座山？")

    assert "小铭" in reply["content"]
    assert "记不太清" in reply["content"]
    assert reply["citations"] == []


def test_citations_endpoint_and_correct_memory_affect_next_reply(client):
    token = register_user(client, "chat-correct-memory@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢包饺子给小铭吃。",
    )
    confirm_memory(client, token, memory["id"])
    conversation = create_conversation(client, token, persona["id"])
    first_reply = send_message(client, token, conversation["id"], "你喜欢做什么给我吃？")
    assert "饺子" in first_reply["content"]

    citations = client.get(
        f"/api/messages/{first_reply['id']}/citations",
        headers=auth(token),
    )
    assert citations.status_code == 200
    assert citations.json()["items"][0]["memory_card_id"] == memory["id"]

    correction = client.post(
        f"/api/messages/{first_reply['id']}/correct-memory",
        headers=auth(token),
        json={"memory_id": memory["id"], "content": "外婆喜欢包馄饨给小铭吃。"},
    )
    assert correction.status_code == 200
    assert correction.json()["memory"]["status"] == "corrected"
    assert correction.json()["memory"]["user_correction"] == "外婆喜欢包馄饨给小铭吃。"

    second_reply = send_message(client, token, conversation["id"], "你喜欢做什么给我吃？")
    assert "馄饨" in second_reply["content"]
    assert "饺子" not in second_reply["content"]
    assert second_reply["citations"][0]["memory_card_id"] == memory["id"]


def test_chat_routes_reject_cross_user_access(client):
    owner_token = register_user(client, "chat-scope-owner@example.com")
    other_token = register_user(client, "chat-scope-other@example.com")
    persona = create_persona(client, owner_token)
    material = create_manual_material(client, owner_token, persona["id"])
    memory = create_memory(
        client,
        owner_token,
        persona["id"],
        material["id"],
        "外婆喜欢包馄饨。",
    )
    confirm_memory(client, owner_token, memory["id"])
    conversation = create_conversation(client, owner_token, persona["id"])
    reply = send_message(client, owner_token, conversation["id"], "你喜欢什么？")

    assert (
        client.get(
            f"/api/personas/{persona['id']}/conversations",
            headers=auth(other_token),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/conversations/{conversation['id']}/messages",
            headers=auth(other_token),
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/conversations/{conversation['id']}/messages",
            headers=auth(other_token),
            json={"content": "hello"},
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/messages/{reply['id']}/citations",
            headers=auth(other_token),
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/messages/{reply['id']}/correct-memory",
            headers=auth(other_token),
            json={"memory_id": memory["id"], "content": "外婆喜欢包馄饨。"},
        ).status_code
        == 404
    )


def test_send_voice_message_runs_asr_chat_tts_and_keeps_citations(client):
    token = register_user(client, "chat-voice@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢包馄饨给小铭吃。",
    )
    confirm_memory(client, token, memory["id"])
    audio = upload_audio_material(client, token, persona["id"])
    conversation = create_conversation(client, token, persona["id"])

    reply = client.post(
        f"/api/conversations/{conversation['id']}/voice-message",
        headers=auth(token),
        json={"source_material_id": audio["id"]},
    )

    assert reply.status_code == 201
    body = reply.json()
    assert body["role"] == "persona"
    assert body["audio_url"].startswith("mock://tts/")
    assert "馄饨" in body["content"]
    assert body["citations"][0]["memory_card_id"] == memory["id"]
    assert body["metadata_json"]["voice"]["source_material_id"] == audio["id"]
    assert body["metadata_json"]["voice"]["asr_job_id"]
    assert body["metadata_json"]["voice"]["synthesize_job_id"]
    assert body["metadata_json"]["voice"]["voice_status"] == "default_tts"

    jobs = client.get(f"/api/personas/{persona['id']}/jobs", headers=auth(token))
    assert jobs.status_code == 200
    job_types = {item["job_type"]: item["status"] for item in jobs.json()["items"]}
    assert job_types["asr_audio"] == "succeeded"
    assert job_types["synthesize_speech"] == "succeeded"


def test_voice_message_rejects_non_audio_source_material(client):
    token = register_user(client, "chat-voice-non-audio@example.com")
    persona = create_persona(client, token)
    material = create_manual_source_material(client, token, persona["id"])
    conversation = create_conversation(client, token, persona["id"])

    response = client.post(
        f"/api/conversations/{conversation['id']}/voice-message",
        headers=auth(token),
        json={"source_material_id": material["id"]},
    )

    assert response.status_code == 400


def test_send_text_message_passes_markdown_context_to_gateway_and_cites_selected_ids(
    client,
    monkeypatch,
):
    captured: dict[str, dict] = {}

    class FakeGateway:
        async def run(self, capability, payload):
            assert capability == "chat_llm"
            captured["payload"] = payload
            assert "retrieved_memories" not in payload
            return {
                "provider_type": "third_party",
                "provider_name": "minimax",
                "capability": capability,
                "status": "succeeded",
                "input": payload,
                "output": {
                    "reply_text": "小铭，我记得外婆喜欢包馄饨给你吃。",
                    "used_memory_ids": payload["selected_memory_ids"],
                },
            }

    monkeypatch.setattr(chat_service, "ProviderGateway", lambda: FakeGateway())
    monkeypatch.setattr(memory_markdown, "ProviderGateway", lambda: FakeGateway())
    token = register_user(client, "chat-markdown-payload@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢包馄饨给小铭吃。",
    )
    confirm_memory(client, token, memory["id"])
    conversation = create_conversation(client, token, persona["id"])

    reply = send_message(client, token, conversation["id"], "你以前喜欢做什么给我吃？")

    payload = captured["payload"]
    assert "long_term_memory_md" in payload
    assert "short_term_memory_md" in payload
    assert memory["id"] in payload["long_term_memory_md"]
    assert "你以前喜欢做什么给我吃？" not in payload["short_term_memory_md"]
    assert payload["selected_memory_ids"] == [memory["id"]]
    assert payload["used_memory_ids"] == [memory["id"]]
    assert reply["citations"][0]["memory_card_id"] == memory["id"]
    assert reply["metadata_json"]["memory_context"]["source"] == "memory_markdown"


def test_long_memory_markdown_compression_selected_ids_drive_citations(
    client,
    monkeypatch,
):
    calls: list[str] = []
    selected_id: str | None = None

    class FakeGateway:
        async def run(self, capability, payload):
            calls.append(capability)
            if capability == "memory_context_compression":
                return {
                    "provider_type": "third_party",
                    "provider_name": "minimax",
                    "capability": capability,
                    "status": "succeeded",
                    "input": payload,
                    "output": {
                        "compressed_md": f"# 压缩长期记忆\n- memory_card_id: {selected_id}\n- content: 外婆喜欢包馄饨。",
                        "selected_memory_ids": [selected_id],
                    },
                }
            assert capability == "chat_llm"
            return {
                "provider_type": "third_party",
                "provider_name": "minimax",
                "capability": capability,
                "status": "succeeded",
                "input": payload,
                "output": {
                    "reply_text": "小铭，我记得这件事。",
                    "used_memory_ids": payload["selected_memory_ids"],
                },
            }

    monkeypatch.setattr(memory_markdown, "MAX_LONG_TERM_MEMORY_CHARS", 120)
    monkeypatch.setattr(chat_service, "ProviderGateway", lambda: FakeGateway())
    monkeypatch.setattr(memory_markdown, "ProviderGateway", lambda: FakeGateway())
    token = register_user(client, "chat-md-compress@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    first = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢包馄饨。" * 20,
        title="馄饨记忆",
    )
    second = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢散步。" * 20,
        title="散步记忆",
    )
    selected_id = first["id"]
    confirm_memory(client, token, first["id"])
    confirm_memory(client, token, second["id"])
    conversation = create_conversation(client, token, persona["id"])

    reply = send_message(client, token, conversation["id"], "你记得什么？")

    assert calls == ["memory_context_compression", "chat_llm"]
    assert [item["memory_card_id"] for item in reply["citations"]] == [first["id"]]
    assert reply["metadata_json"]["memory_context"]["long_term_compressed"] is True
    assert reply["metadata_json"]["retrieval"] == [
        {"memory_card_id": first["id"], "source": "memory_markdown"}
    ]


def test_memory_markdown_compression_failure_falls_back_without_blocking_chat(
    client,
    monkeypatch,
):
    class FakeGateway:
        async def run(self, capability, payload):
            if capability == "memory_context_compression":
                raise RuntimeError("compression unavailable")
            assert capability == "chat_llm"
            return {
                "provider_type": "local",
                "provider_name": "mock",
                "capability": capability,
                "status": "succeeded",
                "input": payload,
                "output": {
                    "reply_text": "小铭，我先按能保留的记忆慢慢说。",
                    "used_memory_ids": payload["selected_memory_ids"],
                },
            }

    monkeypatch.setattr(memory_markdown, "MAX_LONG_TERM_MEMORY_CHARS", 120)
    monkeypatch.setattr(chat_service, "ProviderGateway", lambda: FakeGateway())
    monkeypatch.setattr(memory_markdown, "ProviderGateway", lambda: FakeGateway())
    token = register_user(client, "chat-md-compress-fallback@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢包馄饨。" * 20,
        title="馄饨记忆",
    )
    confirm_memory(client, token, memory["id"])
    conversation = create_conversation(client, token, persona["id"])

    reply = send_message(client, token, conversation["id"], "你记得什么？")

    assert reply["role"] == "persona"
    assert reply["metadata_json"]["memory_context"]["compression_failed"] is True
    assert reply["metadata_json"]["memory_context"]["long_term_compressed"] is True
    assert reply["citations"][0]["memory_card_id"] == memory["id"]
