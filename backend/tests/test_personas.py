from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.ai_job import AIJob
from app.models.conversation import Conversation, Message, MessageCitation
from app.models.memory_card import MemoryCard
from app.models.memory_story import MemoryStory
from app.models.parsed_chunk import ParsedChunk
from app.models.persona import Persona
from app.models.persona_profile import PersonaProfile
from app.models.source_material import SourceMaterial
from app.models.user import User
from app.models.voice_avatar import AvatarModel, VoiceModel
from app.services import memory_markdown
from app.services import avatar as avatar_service


PATCH_REQUIRED_FIELDS = [
    "name",
    "persona_type",
    "relationship_to_user",
    "user_nickname_by_persona",
    "gender",
    "language",
    "status",
    "short_bio",
    "speaking_style",
    "emotional_style",
    "forbidden_expressions",
]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_user(client, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "passw0rd", "display_name": "Demo"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def persona_payload(persona_type: str = "deceased_relative") -> dict[str, str]:
    return {
        "name": "外婆",
        "persona_type": persona_type,
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


def create_persona(client, token: str, persona_type: str = "deceased_relative"):
    response = client.post(
        "/api/personas",
        headers=auth(token),
        json=persona_payload(persona_type=persona_type),
    )
    assert response.status_code == 201
    return response.json()


def assert_required_fields_unchanged(client, token: str, persona: dict):
    response = client.get(f"/api/personas/{persona['id']}", headers=auth(token))
    assert response.status_code == 200
    current = response.json()
    for field in PATCH_REQUIRED_FIELDS:
        assert current[field] == persona[field]


@pytest.mark.parametrize(
    "field",
    [
        "gender",
        "age",
        "status",
        "short_bio",
        "speaking_style",
        "emotional_style",
        "forbidden_expressions",
    ],
)
def test_create_persona_rejects_omitted_required_profile_fields(client, field):
    token = register_user(client, "required-omitted@example.com")
    payload = persona_payload()
    payload.pop(field)

    response = client.post("/api/personas", headers=auth(token), json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "field",
    [
        "gender",
        "age",
        "language",
        "status",
        "short_bio",
        "speaking_style",
        "emotional_style",
        "forbidden_expressions",
    ],
)
def test_create_persona_rejects_null_required_profile_fields(client, field):
    token = register_user(client, "required-null@example.com")
    payload = persona_payload()
    payload[field] = None

    response = client.post("/api/personas", headers=auth(token), json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "field",
    [
        "name",
        "relationship_to_user",
        "user_nickname_by_persona",
        "language",
        "short_bio",
        "speaking_style",
        "emotional_style",
        "forbidden_expressions",
    ],
)
def test_create_persona_rejects_blank_required_prompt_strings(client, field):
    token = register_user(client, "required-blank@example.com")
    payload = persona_payload()
    payload[field] = "   "

    response = client.post("/api/personas", headers=auth(token), json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field", "value"),
    [("gender", "robot"), ("status", "archived")],
)
def test_create_persona_rejects_unsupported_gender_and_status(client, field, value):
    token = register_user(client, "enum@example.com")
    payload = persona_payload()
    payload[field] = value

    response = client.post("/api/personas", headers=auth(token), json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize("age", [-1, 0, 151])
def test_create_persona_rejects_out_of_range_age(client, age):
    token = register_user(client, "age-range@example.com")
    payload = persona_payload()
    payload["age"] = age

    response = client.post("/api/personas", headers=auth(token), json=payload)

    assert response.status_code == 422


def test_create_persona_defaults_language_to_chinese_when_omitted(client):
    token = register_user(client, "default-language@example.com")
    payload = persona_payload()
    payload.pop("language")

    response = client.post("/api/personas", headers=auth(token), json=payload)

    assert response.status_code == 201
    assert response.json()["language"] == "zh-CN"


def test_create_persona_rejects_non_chinese_language(client):
    token = register_user(client, "non-chinese-language@example.com")
    payload = persona_payload()
    payload["language"] = "en-US"

    response = client.post("/api/personas", headers=auth(token), json=payload)

    assert response.status_code == 422


def test_update_persona_rejects_non_chinese_language_and_preserves_existing_value(client):
    token = register_user(client, "patch-non-chinese-language@example.com")
    persona = create_persona(client, token)

    response = client.patch(
        f"/api/personas/{persona['id']}",
        headers=auth(token),
        json={"language": "en-US"},
    )

    assert response.status_code == 422
    assert_required_fields_unchanged(client, token, persona)


@pytest.mark.parametrize("field", PATCH_REQUIRED_FIELDS)
def test_update_persona_rejects_null_required_fields_and_preserves_existing_values(
    client, field
):
    token = register_user(client, "patch-null@example.com")
    persona = create_persona(client, token)

    response = client.patch(
        f"/api/personas/{persona['id']}",
        headers=auth(token),
        json={field: None},
    )

    assert response.status_code == 422
    assert_required_fields_unchanged(client, token, persona)


@pytest.mark.parametrize("field", PATCH_REQUIRED_FIELDS)
def test_update_persona_rejects_blank_required_fields_and_preserves_existing_values(
    client, field
):
    token = register_user(client, "patch-blank@example.com")
    persona = create_persona(client, token)

    response = client.patch(
        f"/api/personas/{persona['id']}",
        headers=auth(token),
        json={field: "   "},
    )

    assert response.status_code == 422
    assert_required_fields_unchanged(client, token, persona)


def test_create_list_detail_update_and_delete_persona(client):
    token = register_user(client, "owner@example.com")
    created = create_persona(client, token, persona_type="deceased_relative")
    assert created["name"] == "外婆"
    assert created["age"] == 72
    assert created["relationship_to_user"] == "外婆"
    assert created["user_nickname_by_persona"] == "小铭"
    assert created["stats"]["materials_count"] == 0
    assert created["prompt_context"]["persona_name"] == "外婆"

    listed = client.get("/api/personas", headers=auth(token))
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [created["id"]]

    detail = client.get(f"/api/personas/{created['id']}", headers=auth(token))
    assert detail.status_code == 200
    assert detail.json()["id"] == created["id"]

    patched = client.patch(
        f"/api/personas/{created['id']}",
        headers=auth(token),
        json={
            "relationship_to_user": "奶奶",
            "user_nickname_by_persona": "小明",
            "age": 73,
        },
    )
    assert patched.status_code == 200
    assert patched.json()["relationship_to_user"] == "奶奶"
    assert patched.json()["age"] == 73
    assert patched.json()["prompt_context"]["user_nickname_by_persona"] == "小明"

    deleted = client.delete(f"/api/personas/{created['id']}", headers=auth(token))
    assert deleted.status_code == 204
    assert client.get(f"/api/personas/{created['id']}", headers=auth(token)).status_code == 404
    assert client.get("/api/personas", headers=auth(token)).json()["items"] == []


def test_delete_persona_soft_deletes_prd_related_records(
    client, db_session, monkeypatch, tmp_path
):
    token = register_user(client, "cascade-delete@example.com")
    created = create_persona(client, token)
    user = db_session.scalar(select(User).where(User.email == "cascade-delete@example.com"))
    assert user is not None

    material = SourceMaterial(
        user_id=user.id,
        persona_id=created["id"],
        file_name="memory.txt",
        file_type="text",
        mime_type="text/plain",
        file_size=32,
        storage_url="storage/materials/demo/memory.txt",
        parse_status="succeeded",
    )
    db_session.add(material)
    db_session.flush()

    chunk = ParsedChunk(
        persona_id=created["id"],
        source_material_id=material.id,
        chunk_type="text",
        content="外婆会在生日包馄饨。",
        summary="生日馄饨",
        source_location="line:1",
    )
    profile = PersonaProfile(
        persona_id=created["id"],
        basic_facts={"name": "外婆"},
        relationships={"user": "小铭"},
        preferences={"food": "馄饨"},
        habits={"pace": "慢慢说"},
        expression_style={"tone": "温柔"},
        shared_events={"birthday": "馄饨"},
        values_json={"family": "陪伴"},
        emotional_patterns={"comfort": "先安慰"},
        profile_summary="外婆说话温柔。",
        source_memory_ids=[],
    )
    conversation = Conversation(
        user_id=user.id,
        persona_id=created["id"],
        title="和外婆的对话",
    )
    voice_model = VoiceModel(
        persona_id=created["id"],
        provider_type="local",
        provider_name="mock_default_tts",
        status="default_tts",
        user_selected=True,
    )
    avatar_model = AvatarModel(
        persona_id=created["id"],
        provider_type="local",
        provider_name="mock_default_avatar",
        status="default_avatar",
        style="memorial",
        user_selected=True,
    )
    job = AIJob(
        user_id=user.id,
        persona_id=created["id"],
        source_material_id=material.id,
        job_type="parse_text",
        provider_type="local",
        provider_name="mock",
        status="succeeded",
    )
    db_session.add_all([chunk, profile, conversation, voice_model, avatar_model, job])
    db_session.flush()

    memory = MemoryCard(
        persona_id=created["id"],
        title="生日馄饨",
        content="外婆会在生日包馄饨。",
        category="shared_event",
        confidence_level="high",
        confidence_score=90,
        source_material_id=material.id,
        parsed_chunk_id=chunk.id,
        source_type="text",
        source_quote="外婆会在生日包馄饨。",
        source_location="line:1",
        evidence_json={"provider": "mock"},
        status="confirmed",
    )
    story = MemoryStory(
        persona_id=created["id"],
        theme="生日",
        title="生日里的馄饨",
        content="小铭，我记得生日那天的馄饨。",
        audio_url="mock://tts/story.wav",
        source_memory_ids=[],
        source_memories=[],
        is_favorite=True,
    )
    db_session.add_all([memory, story])
    db_session.flush()

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content="你记得生日吗？",
    )
    persona_message = Message(
        conversation_id=conversation.id,
        role="persona",
        content="小铭，我记得生日馄饨。",
    )
    db_session.add_all([user_message, persona_message])
    db_session.flush()

    citation = MessageCitation(
        message_id=persona_message.id,
        memory_card_id=memory.id,
        source_material_id=material.id,
        parsed_chunk_id=chunk.id,
        quote="外婆会在生日包馄饨。",
        source_location="line:1",
    )
    db_session.add(citation)
    db_session.commit()
    storage_path = Path(material.storage_url)
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(b"local persona material")
    assert storage_path.exists()
    monkeypatch.setattr(memory_markdown, "MEMORY_CONTEXT_ROOT", tmp_path / "memory_context")
    context_dir = memory_markdown.memory_context_dir(created["id"])
    context_dir.mkdir(parents=True, exist_ok=True)
    (context_dir / memory_markdown.LONG_TERM_MEMORY_FILE).write_text(
        "# 长期记忆\n",
        encoding="utf-8",
    )
    assert context_dir.exists()

    monkeypatch.setattr(
        avatar_service,
        "LOCAL_AVATAR_MODELS_ROOT",
        tmp_path / "avatar_models",
        raising=False,
    )
    avatar_upload = client.post(
        f"/api/personas/{created['id']}/avatar/upload",
        headers=auth(token),
        files={"file": ("waipo.glb", b"glb-model-bytes", "model/gltf-binary")},
    )
    assert avatar_upload.status_code == 201
    uploaded_avatar_id = avatar_upload.json()["selected_avatar_model"]["id"]
    uploaded_avatar_path = next(
        (tmp_path / "avatar_models").rglob(f"{uploaded_avatar_id}-*.glb")
    )
    assert uploaded_avatar_path.exists()

    response = client.delete(f"/api/personas/{created['id']}", headers=auth(token))

    assert response.status_code == 204
    assert not storage_path.exists()
    assert not uploaded_avatar_path.exists()
    assert not context_dir.exists()
    assert client.get(f"/api/jobs/{job.id}", headers=auth(token)).status_code == 404
    db_session.expire_all()
    for model, row_id in [
        (Persona, created["id"]),
        (SourceMaterial, material.id),
        (ParsedChunk, chunk.id),
        (MemoryCard, memory.id),
        (PersonaProfile, profile.id),
        (Conversation, conversation.id),
        (Message, user_message.id),
        (Message, persona_message.id),
        (MessageCitation, citation.id),
        (VoiceModel, voice_model.id),
        (AvatarModel, avatar_model.id),
        (AIJob, job.id),
        (MemoryStory, story.id),
    ]:
        row = db_session.get(model, row_id)
        assert row is not None
        assert getattr(row, "deleted_at", None) is not None, model.__name__


def test_supported_persona_types_and_rejects_reserved_expert_role(client):
    token = register_user(client, "types@example.com")
    for persona_type in [
        "deceased_relative",
        "living_relative",
        "public_figure",
        "fictional_character",
    ]:
        assert create_persona(client, token, persona_type=persona_type)["persona_type"] == persona_type

    response = client.post(
        "/api/personas",
        headers=auth(token),
        json=persona_payload(persona_type="expert_role"),
    )
    assert response.status_code == 422


def test_persona_access_is_user_scoped(client):
    owner_token = register_user(client, "scoped-owner@example.com")
    other_token = register_user(client, "other@example.com")
    persona = create_persona(client, owner_token)

    assert client.get(f"/api/personas/{persona['id']}", headers=auth(other_token)).status_code == 404
    assert (
        client.patch(
            f"/api/personas/{persona['id']}",
            headers=auth(other_token),
            json={"name": "x"},
        ).status_code
        == 404
    )
    assert client.delete(f"/api/personas/{persona['id']}", headers=auth(other_token)).status_code == 404
