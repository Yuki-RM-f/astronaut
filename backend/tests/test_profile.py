from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.ai_job import AIJob
from app.models.memory_card import MemoryCard
from app.models.persona import Persona
from app.models.persona_profile import PersonaProfile
from app.models.source_material import SourceMaterial
from app.services import parsing
from app.services.profile import generate_memory_document_trust, get_or_create_profile


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


def create_manual_material(
    client,
    token: str,
    persona_id: str,
    manual_text: str = "外婆喜欢包馄饨。她常说慢慢来。",
    db_session=None,
) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/materials/manual",
        headers=auth(token),
        json={"manual_text": manual_text, "importance": "very_important"},
    )
    assert response.status_code == 201
    body = response.json()
    if db_session is not None:
        material = db_session.get(SourceMaterial, body["id"])
        assert material is not None
        job = db_session.get(AIJob, body["jobs"][0]["id"])
        assert job is not None
        assert material.parse_status == "pending"
        assert job.status == "pending"
        parsing.run_parse_job(db_session, material, job)
        db_session.commit()
    return body


def list_memories(client, token: str, persona_id: str) -> list[dict]:
    response = client.get(f"/api/personas/{persona_id}/memories", headers=auth(token))
    assert response.status_code == 200
    return response.json()["items"]


def source_memory_ids(body: dict) -> set[str]:
    ids: set[str] = set()
    for values in body["source_memory_ids"].values():
        ids.update(values)
    return ids


def job_count(db_session, persona_id: str, job_type: str) -> int:
    jobs = db_session.scalars(
        select(AIJob).where(
            AIJob.persona_id == persona_id,
            AIJob.job_type == job_type,
            AIJob.status == "succeeded",
        )
    ).all()
    return len(jobs)


def assert_basic_facts_include_age(body: dict, age: int = 72):
    assert {
        "field": "age",
        "value": age,
        "content": f"年龄/享年：{age}",
        "source": "persona_card",
    } in body["basic_facts"]


def test_memory_document_modules_are_rendered_from_active_memory_cards_only(
    client,
    db_session,
):
    token = register_user(client, "profile-card-source@example.com")
    persona_body = create_persona(client, token)
    persona = db_session.get(Persona, persona_body["id"])
    assert persona is not None

    succeeded_material = SourceMaterial(
        user_id=persona.user_id,
        persona_id=persona.id,
        file_type="manual",
        manual_text="外婆喜欢包馄饨，也常说慢慢来。",
        importance="normal",
        parse_status="succeeded",
    )
    failed_material = SourceMaterial(
        user_id=persona.user_id,
        persona_id=persona.id,
        file_type="manual",
        manual_text="失败资料不应进入结构化文档来源。",
        importance="normal",
        parse_status="failed",
    )
    db_session.add_all([succeeded_material, failed_material])
    db_session.flush()

    card = MemoryCard(
        persona_id=persona.id,
        title="外婆喜欢包馄饨",
        content="外婆喜欢包馄饨。",
        category="preference",
        confidence_level="high",
        confidence_score=92,
        source_material_id=succeeded_material.id,
        source_type="manual",
        source_quote="外婆喜欢包馄饨",
        source_location="manual:body",
        evidence_json={},
        status="pending_review",
        is_important=False,
        created_by="system",
    )
    db_session.add(card)
    db_session.flush()

    def fake_runner(capability: str, payload: dict):
        assert capability == "memory_document_generation"
        return {
            "provider_type": "third_party",
            "provider_name": "minimax",
            "output": {
                "profile_summary": "外婆的档案摘要来自模型。",
                "structured_memory_document_json": {
                    "sources": [
                        {
                            "id": failed_material.id,
                            "file_type": "manual",
                            "label": "失败资料",
                            "parse_status": "failed",
                        }
                    ],
                    "modules": {
                        "basic_fact": [
                            {
                                "id": "rogue-parsed-chunk",
                                "title": "模型额外总结",
                                "content": "这条没有对应 MemoryCard。",
                                "category": "basic_fact",
                                "confidence_level": "medium",
                                "confidence_score": 70,
                                "source_quote": "没有对应 MemoryCard",
                                "source_location": "parsed_chunk:1",
                                "status": "pending_review",
                                "is_important": False,
                            }
                        ],
                        "relationship": [],
                        "preference": [],
                        "habit": [],
                        "expression_style": [],
                        "shared_event": [],
                    },
                    "unclassified": [],
                    "warnings": [],
                },
                "trust_score": 80,
                "trust_level": "trusted",
                "trust_rationale": "模型返回的可信度仍可使用。",
                "suggestions": ["继续补充资料"],
            },
        }

    _report, _payload, output, _provider_type, _provider_name = generate_memory_document_trust(
        db_session,
        persona,
        runner=fake_runner,
    )

    document_json = output["structured_memory_document_json"]
    module_items = [
        item
        for items in document_json["modules"].values()
        for item in items
    ]
    assert [item["id"] for item in module_items] == [card.id]
    assert document_json["sources"] == [
        {
            "id": succeeded_material.id,
            "file_type": "manual",
            "label": "外婆喜欢包馄饨，也常说慢慢来。",
            "parse_status": "succeeded",
        }
    ]
    assert "rogue-parsed-chunk" not in output["structured_memory_md"]
    assert "这条没有对应 MemoryCard" not in output["structured_memory_md"]
    assert "外婆喜欢包馄饨" in output["structured_memory_md"]


class RacingProfileSession:
    def __init__(self, existing_profile: PersonaProfile):
        self.existing_profile = existing_profile
        self.scalar_calls = 0
        self.added_profiles: list[PersonaProfile] = []

    def scalar(self, _statement):
        self.scalar_calls += 1
        if self.scalar_calls == 1:
            return None
        return self.existing_profile

    def add(self, profile: PersonaProfile):
        self.added_profiles.append(profile)

    def flush(self):
        raise IntegrityError("insert persona profile", {}, Exception("duplicate key"))

    def begin_nested(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False


def test_get_or_create_profile_recovers_from_concurrent_insert():
    persona = SimpleNamespace(id="persona-race")
    existing_profile = PersonaProfile(
        persona_id=persona.id,
        basic_facts=[],
        relationships=[],
        preferences=[],
        habits=[],
        expression_style=[],
        shared_events=[],
        values_json=[],
        emotional_patterns=[],
        profile_summary=None,
        source_memory_ids={},
    )
    db = RacingProfileSession(existing_profile)

    profile = get_or_create_profile(db, persona)

    assert profile is existing_profile
    assert db.scalar_calls == 2
    assert len(db.added_profiles) == 1


def test_profile_basic_facts_include_user_filled_age_from_persona_card(client):
    token = register_user(client, "m4-profile-age@example.com")
    persona = create_persona(client, token)

    response = client.get(f"/api/personas/{persona['id']}/profile", headers=auth(token))
    body = response.json()

    assert response.status_code == 200
    assert_basic_facts_include_age(body)


def test_confirmed_memory_generates_profile_without_recalculating_trust(client, db_session):
    token = register_user(client, "m4-profile@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"], db_session=db_session)
    memories = list_memories(client, token, persona["id"])

    before = client.get(f"/api/personas/{persona['id']}/profile", headers=auth(token)).json()
    confirmed = client.post(f"/api/memories/{memories[0]['id']}/confirm", headers=auth(token)).json()
    after = client.get(f"/api/personas/{persona['id']}/profile", headers=auth(token)).json()

    assert before["trust_score"] > 0
    assert confirmed["status"] == "confirmed"
    assert after["trust_score"] == before["trust_score"]
    assert after["source_memory_ids"]
    assert after["profile_summary"]
    assert memories[0]["id"] in source_memory_ids(after)


def test_patch_profile_edits_every_dimension_and_prompt_summary(client):
    token = register_user(client, "m4-profile-patch@example.com")
    persona = create_persona(client, token)
    payload = {
        "basic_facts": [{"content": "外婆住在老房子。"}],
        "relationships": [{"content": "外婆很疼小铭。"}],
        "preferences": [{"content": "外婆喜欢包馄饨。"}],
        "habits": [{"content": "外婆习惯早起。"}],
        "expression_style": [{"content": "外婆说话很慢。"}],
        "shared_events": [{"content": "一起过生日。"}],
        "values_json": [{"content": "重视家人。"}],
        "emotional_patterns": [{"content": "先安慰再鼓励。"}],
        "profile_summary": "外婆温柔、慢慢说，常鼓励小铭。",
    }

    response = client.patch(
        f"/api/personas/{persona['id']}/profile",
        headers=auth(token),
        json=payload,
    )
    body = response.json()

    assert response.status_code == 200
    for field, value in payload.items():
        assert body[field] == value

    persona_after = client.get(f"/api/personas/{persona['id']}", headers=auth(token))
    assert persona_after.status_code == 200
    assert (
        persona_after.json()["prompt_context"]["profile_summary"]
        == "外婆温柔、慢慢说，常鼓励小铭。"
    )


def test_patch_profile_rejects_explicit_null_dimension(client):
    token = register_user(client, "m4-profile-null@example.com")
    persona = create_persona(client, token)

    response = client.patch(
        f"/api/personas/{persona['id']}/profile",
        headers=auth(token),
        json={"preferences": None},
    )

    assert response.status_code == 422


def test_manual_profile_edits_survive_memory_audit_refresh(client, db_session):
    token = register_user(client, "m4-profile-manual-survives@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"], db_session=db_session)
    memories = list_memories(client, token, persona["id"])
    for memory in memories:
        confirmed = client.post(f"/api/memories/{memory['id']}/confirm", headers=auth(token))
        assert confirmed.status_code == 200

    expression_memory = next(
        memory for memory in memories if memory["category"] == "expression_style"
    )
    manual_preferences = [{"content": "用户手动确认：外婆最喜欢桂花糕。"}]
    manual_summary = "用户手动整理的外婆档案摘要，后续自动刷新不能覆盖。"
    patched = client.patch(
        f"/api/personas/{persona['id']}/profile",
        headers=auth(token),
        json={
            "preferences": manual_preferences,
            "profile_summary": manual_summary,
        },
    )
    assert patched.status_code == 200

    disabled = client.post(
        f"/api/memories/{expression_memory['id']}/disable",
        headers=auth(token),
    )
    assert disabled.status_code == 200

    refreshed = client.get(f"/api/personas/{persona['id']}/profile", headers=auth(token))
    body = refreshed.json()

    assert refreshed.status_code == 200
    assert body["preferences"] == manual_preferences
    assert body["profile_summary"] == manual_summary


def test_upload_generated_profile_summary_overwrites_manual_summary(client, db_session):
    token = register_user(client, "m4-profile-summary-overwrite@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"], "first uploaded memory", db_session)

    patched = client.patch(
        f"/api/personas/{persona['id']}/profile",
        headers=auth(token),
        json={"profile_summary": "temporary manual summary"},
    )
    assert patched.status_code == 200
    assert patched.json()["profile_summary"] == "temporary manual summary"

    create_manual_material(client, token, persona["id"], "second uploaded memory", db_session)

    refreshed = client.get(f"/api/personas/{persona['id']}/profile", headers=auth(token))
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["profile_summary"]
    assert body["profile_summary"] != "temporary manual summary"


def test_profile_regenerate_rebuilds_from_confirmed_and_corrected_memories(
    client,
    db_session,
):
    token = register_user(client, "m4-profile-regenerate@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"], db_session=db_session)
    memories = list_memories(client, token, persona["id"])
    before = client.get(f"/api/personas/{persona['id']}/profile", headers=auth(token))
    assert before.status_code == 200
    before_summary = before.json()["profile_summary"]
    client.post(f"/api/memories/{memories[0]['id']}/confirm", headers=auth(token))
    corrected = client.patch(
        f"/api/memories/{memories[1]['id']}",
        headers=auth(token),
        json={"content": "外婆常说慢慢来，别着急。"},
    )
    assert corrected.status_code == 200

    response = client.post(
        f"/api/personas/{persona['id']}/profile/regenerate",
        headers=auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert memories[0]["id"] in source_memory_ids(body)
    assert memories[1]["id"] in source_memory_ids(body)
    assert body["profile_summary"] == before_summary
    assert job_count(db_session, persona["id"], "update_profile") == 1


def test_profile_regenerate_stores_persona_engine_json_and_records_job(client, db_session):
    token = register_user(client, "m4-profile-engine@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"], db_session=db_session)
    memories = list_memories(client, token, persona["id"])
    before = client.get(f"/api/personas/{persona['id']}/profile", headers=auth(token))
    assert before.status_code == 200
    before_summary = before.json()["profile_summary"]
    client.post(f"/api/memories/{memories[0]['id']}/confirm", headers=auth(token))

    response = client.post(
        f"/api/personas/{persona['id']}/profile/regenerate",
        headers=auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert body["persona_engine_json"]["persona_version"] == "persona_engine_v2_mock"
    assert body["persona_engine_json"]["overall_confidence"] >= 0
    assert body["persona_engine_generated_at"] is not None
    assert body["profile_summary"] == before_summary

    job = db_session.scalars(
        select(AIJob)
        .where(AIJob.persona_id == persona["id"], AIJob.job_type == "update_profile")
        .order_by(AIJob.created_at.desc())
    ).first()
    assert job is not None
    assert job.provider_name == "mock"
    assert job.output_json["persona_engine_status"] == "succeeded"
    assert job.output_json["persona_engine_json"]["persona_version"] == "persona_engine_v2_mock"


def test_recalculate_trust_reruns_memory_document_generation_and_records_job(client, db_session):
    token = register_user(client, "m4-profile-trust@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"], db_session=db_session)
    for memory in list_memories(client, token, persona["id"]):
        client.post(f"/api/memories/{memory['id']}/confirm", headers=auth(token))

    response = client.post(
        f"/api/personas/{persona['id']}/recalculate-trust",
        headers=auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert 0 < body["trust_score"] <= 100
    assert body["trust_level"] in {"initial", "usable", "trusted", "high_trust"}
    assert body["suggestions"]
    assert {component["name"] for component in body["components"]} == {
        "memory_document_generation"
    }
    job = db_session.scalars(
        select(AIJob)
        .where(AIJob.persona_id == persona["id"], AIJob.job_type == "calculate_trust_score")
        .order_by(AIJob.created_at.desc())
    ).first()
    assert job is not None
    assert "## 资料来源" in job.output_json["structured_memory_md"]
    assert job.output_json["trust_score"] == body["trust_score"]


def test_profile_get_displays_persona_trust_score_when_job_output_differs(client, db_session):
    token = register_user(client, "m4-profile-single-trust-field@example.com")
    persona = create_persona(client, token)
    stored_persona = db_session.get(Persona, persona["id"])
    assert stored_persona is not None
    stored_persona.trust_score = 37
    db_session.add(
        AIJob(
            user_id=stored_persona.user_id,
            persona_id=stored_persona.id,
            job_type="parse_material",
            provider_type="mock",
            provider_name="mock",
            status="succeeded",
            input_json={},
            output_json={
                "profile_summary": "job summary",
                "structured_memory_md": "## 资料来源\n- old",
                "trust_score": 88,
                "trust_level": "high_trust",
                "trust_rationale": "old job output",
                "suggestions": ["old suggestion"],
            },
        )
    )
    db_session.commit()

    response = client.get(f"/api/personas/{persona['id']}/profile", headers=auth(token))
    body = response.json()

    assert response.status_code == 200
    assert body["trust_score"] == 37
    assert body["trust_level"] == "usable"


def test_profile_routes_are_user_scoped(client):
    owner_token = register_user(client, "m4-profile-owner@example.com")
    other_token = register_user(client, "m4-profile-other@example.com")
    persona = create_persona(client, owner_token)

    assert (
        client.get(f"/api/personas/{persona['id']}/profile", headers=auth(other_token)).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/personas/{persona['id']}/profile",
            headers=auth(other_token),
            json={"profile_summary": "越权"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/personas/{persona['id']}/profile/regenerate",
            headers=auth(other_token),
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/personas/{persona['id']}/recalculate-trust",
            headers=auth(other_token),
        ).status_code
        == 404
    )


def test_disabled_rejected_deleted_memories_do_not_enter_generated_profile(client, db_session):
    token = register_user(client, "m4-profile-exclude@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"], db_session=db_session)
    create_manual_material(
        client,
        token,
        persona["id"],
        "我们一起过生日。外婆喜欢桂花糕。",
        db_session,
    )
    memories = list_memories(client, token, persona["id"])
    for memory in memories:
        client.post(f"/api/memories/{memory['id']}/confirm", headers=auth(token))

    disabled_id = memories[0]["id"]
    rejected_id = memories[1]["id"]
    deleted_id = memories[2]["id"]
    kept_id = memories[3]["id"]

    client.post(f"/api/memories/{disabled_id}/disable", headers=auth(token))
    client.post(f"/api/memories/{rejected_id}/reject", headers=auth(token))
    client.delete(f"/api/memories/{deleted_id}", headers=auth(token))

    response = client.post(
        f"/api/personas/{persona['id']}/profile/regenerate",
        headers=auth(token),
    )
    body = response.json()
    ids = source_memory_ids(body)

    assert response.status_code == 200
    assert kept_id in ids
    assert disabled_id not in ids
    assert rejected_id not in ids
    assert deleted_id not in ids
