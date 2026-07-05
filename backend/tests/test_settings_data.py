from pathlib import Path

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
from app.services import avatar as avatar_service
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


def create_persona(client, token: str, name: str) -> dict:
    response = client.post(
        "/api/personas",
        headers=auth(token),
        json={
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
        },
    )
    assert response.status_code == 201
    return response.json()


def seed_persona_tree(db_session, user_id: str, persona_id: str, suffix: str) -> list[tuple[type, str]]:
    material = SourceMaterial(
        user_id=user_id,
        persona_id=persona_id,
        file_name=f"memory-{suffix}.txt",
        file_type="text",
        mime_type="text/plain",
        file_size=32,
        storage_url=f"storage/materials/{suffix}/memory.txt",
        parse_status="succeeded",
    )
    db_session.add(material)
    db_session.flush()
    storage_path = Path(material.storage_url)
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(f"{suffix} local material".encode("utf-8"))

    chunk = ParsedChunk(
        persona_id=persona_id,
        source_material_id=material.id,
        chunk_type="text",
        content=f"{suffix} 生日馄饨。",
        summary="生日馄饨",
        source_location="line:1",
    )
    profile = PersonaProfile(
        persona_id=persona_id,
        basic_facts={"name": suffix},
        relationships={"user": "小铭"},
        preferences={"food": "馄饨"},
        habits={"pace": "慢慢说"},
        expression_style={"tone": "温柔"},
        shared_events={"birthday": "馄饨"},
        values_json={"family": "陪伴"},
        emotional_patterns={"comfort": "先安慰"},
        profile_summary="说话温柔。",
        source_memory_ids=[],
    )
    conversation = Conversation(
        user_id=user_id,
        persona_id=persona_id,
        title=f"{suffix} 对话",
    )
    voice_model = VoiceModel(
        persona_id=persona_id,
        provider_type="local",
        provider_name="mock_default_tts",
        status="default_tts",
        user_selected=True,
    )
    avatar_model = AvatarModel(
        persona_id=persona_id,
        provider_type="local",
        provider_name="mock_default_avatar",
        status="default_avatar",
        style="memorial",
        user_selected=True,
    )
    job = AIJob(
        user_id=user_id,
        persona_id=persona_id,
        source_material_id=material.id,
        job_type="parse_text",
        provider_type="local",
        provider_name="mock",
        status="succeeded",
    )
    db_session.add_all([chunk, profile, conversation, voice_model, avatar_model, job])
    db_session.flush()

    memory = MemoryCard(
        persona_id=persona_id,
        title=f"{suffix} 生日",
        content=f"{suffix} 会在生日包馄饨。",
        category="shared_event",
        confidence_level="high",
        confidence_score=90,
        source_material_id=material.id,
        parsed_chunk_id=chunk.id,
        source_type="text",
        source_quote=f"{suffix} 会在生日包馄饨。",
        source_location="line:1",
        evidence_json={"provider": "mock"},
        status="confirmed",
    )
    story = MemoryStory(
        persona_id=persona_id,
        theme="生日",
        title=f"{suffix} 的生日故事",
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
        quote=f"{suffix} 会在生日包馄饨。",
        source_location="line:1",
    )
    db_session.add(citation)
    db_session.commit()

    return [
        (Persona, persona_id),
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
    ]


def test_clear_current_account_data_soft_deletes_owned_domain_records(
    client, db_session, monkeypatch, tmp_path
):
    owner_token = register_user(client, "clear-owner@example.com")
    other_token = register_user(client, "clear-other@example.com")
    owned_persona = create_persona(client, owner_token, "外婆")
    other_persona = create_persona(client, other_token, "奶奶")
    owner = db_session.scalar(select(User).where(User.email == "clear-owner@example.com"))
    other = db_session.scalar(select(User).where(User.email == "clear-other@example.com"))
    assert owner is not None
    assert other is not None

    owned_rows = seed_persona_tree(db_session, owner.id, owned_persona["id"], "owner")
    other_rows = seed_persona_tree(db_session, other.id, other_persona["id"], "other")
    owned_job_id = next(row_id for model, row_id in owned_rows if model is AIJob)
    other_job_id = next(row_id for model, row_id in other_rows if model is AIJob)
    owned_material_id = next(row_id for model, row_id in owned_rows if model is SourceMaterial)
    other_material_id = next(row_id for model, row_id in other_rows if model is SourceMaterial)
    owned_storage_path = Path(db_session.get(SourceMaterial, owned_material_id).storage_url)
    other_storage_path = Path(db_session.get(SourceMaterial, other_material_id).storage_url)
    assert owned_storage_path.exists()
    assert other_storage_path.exists()
    monkeypatch.setattr(memory_markdown, "MEMORY_CONTEXT_ROOT", tmp_path / "memory_context")
    owned_context_dir = memory_markdown.memory_context_dir(owned_persona["id"])
    other_context_dir = memory_markdown.memory_context_dir(other_persona["id"])
    owned_context_dir.mkdir(parents=True, exist_ok=True)
    other_context_dir.mkdir(parents=True, exist_ok=True)
    (owned_context_dir / memory_markdown.LONG_TERM_MEMORY_FILE).write_text(
        "# owner\n",
        encoding="utf-8",
    )
    (other_context_dir / memory_markdown.LONG_TERM_MEMORY_FILE).write_text(
        "# other\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        avatar_service,
        "LOCAL_AVATAR_MODELS_ROOT",
        tmp_path / "avatar_models",
        raising=False,
    )
    owned_avatar_upload = client.post(
        f"/api/personas/{owned_persona['id']}/avatar/upload",
        headers=auth(owner_token),
        files={"file": ("owner.glb", b"owner-glb", "model/gltf-binary")},
    )
    assert owned_avatar_upload.status_code == 201
    owned_avatar_id = owned_avatar_upload.json()["selected_avatar_model"]["id"]
    owned_avatar_path = next((tmp_path / "avatar_models").rglob(f"{owned_avatar_id}-*.glb"))
    other_avatar_upload = client.post(
        f"/api/personas/{other_persona['id']}/avatar/upload",
        headers=auth(other_token),
        files={"file": ("other.glb", b"other-glb", "model/gltf-binary")},
    )
    assert other_avatar_upload.status_code == 201
    other_avatar_id = other_avatar_upload.json()["selected_avatar_model"]["id"]
    other_avatar_path = next((tmp_path / "avatar_models").rglob(f"{other_avatar_id}-*.glb"))
    assert owned_avatar_path.exists()
    assert other_avatar_path.exists()

    response = client.delete("/api/settings/data", headers=auth(owner_token))

    assert response.status_code == 204
    assert not owned_storage_path.exists()
    assert not owned_avatar_path.exists()
    assert other_storage_path.exists()
    assert other_avatar_path.exists()
    assert not owned_context_dir.exists()
    assert other_context_dir.exists()
    assert client.get("/api/auth/me", headers=auth(owner_token)).status_code == 200
    owner_items = client.get("/api/personas", headers=auth(owner_token)).json()["items"]
    assert [item["name"] for item in owner_items] == ["郑木生", "外婆"]
    assert owned_persona["id"] not in [item["id"] for item in owner_items]
    assert client.get(f"/api/jobs/{owned_job_id}", headers=auth(owner_token)).status_code == 404
    other_items = client.get("/api/personas", headers=auth(other_token)).json()["items"]
    assert other_persona["id"] in [item["id"] for item in other_items]
    assert {"外婆", "郑木生", "奶奶"}.issubset({item["name"] for item in other_items})
    assert client.get(f"/api/jobs/{other_job_id}", headers=auth(other_token)).status_code == 200

    db_session.expire_all()
    for model, row_id in owned_rows:
        row = db_session.get(model, row_id)
        assert row is not None
        assert getattr(row, "deleted_at", None) is not None, model.__name__
    for model, row_id in other_rows:
        row = db_session.get(model, row_id)
        assert row is not None
        assert getattr(row, "deleted_at", None) is None, model.__name__
