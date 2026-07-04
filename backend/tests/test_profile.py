from sqlalchemy import select

from app.models.ai_job import AIJob


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
) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/materials/manual",
        headers=auth(token),
        json={"manual_text": manual_text, "importance": "very_important"},
    )
    assert response.status_code == 201
    return response.json()


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


def test_profile_basic_facts_include_user_filled_age_from_persona_card(client):
    token = register_user(client, "m4-profile-age@example.com")
    persona = create_persona(client, token)

    response = client.get(f"/api/personas/{persona['id']}/profile", headers=auth(token))
    body = response.json()

    assert response.status_code == 200
    assert_basic_facts_include_age(body)


def test_confirmed_memory_generates_profile_and_changes_trust(client):
    token = register_user(client, "m4-profile@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"])
    memories = list_memories(client, token, persona["id"])

    before = client.get(f"/api/personas/{persona['id']}/profile", headers=auth(token)).json()
    confirmed = client.post(f"/api/memories/{memories[0]['id']}/confirm", headers=auth(token)).json()
    after = client.get(f"/api/personas/{persona['id']}/profile", headers=auth(token)).json()

    assert confirmed["status"] == "confirmed"
    assert after["trust_score"] > before["trust_score"]
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


def test_manual_profile_edits_survive_memory_audit_refresh(client):
    token = register_user(client, "m4-profile-manual-survives@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"])
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


def test_profile_regenerate_rebuilds_from_confirmed_and_corrected_memories(
    client,
    db_session,
):
    token = register_user(client, "m4-profile-regenerate@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"])
    memories = list_memories(client, token, persona["id"])
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
    assert "慢慢来" in body["profile_summary"]
    assert job_count(db_session, persona["id"], "update_profile") == 1


def test_profile_regenerate_stores_persona_engine_json_and_records_job(client, db_session):
    token = register_user(client, "m4-profile-engine@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"])
    memories = list_memories(client, token, persona["id"])
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
    assert memories[0]["content"] in body["profile_summary"]

    job = db_session.scalars(
        select(AIJob)
        .where(AIJob.persona_id == persona["id"], AIJob.job_type == "update_profile")
        .order_by(AIJob.created_at.desc())
    ).first()
    assert job is not None
    assert job.provider_name == "mock"
    assert job.output_json["persona_engine_status"] == "succeeded"
    assert job.output_json["persona_engine_json"]["persona_version"] == "persona_engine_v2_mock"


def test_recalculate_trust_returns_breakdown_and_records_job(client, db_session):
    token = register_user(client, "m4-profile-trust@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"])
    for memory in list_memories(client, token, persona["id"]):
        client.post(f"/api/memories/{memory['id']}/confirm", headers=auth(token))

    response = client.post(
        f"/api/personas/{persona['id']}/recalculate-trust",
        headers=auth(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert 0 <= body["trust_score"] <= 100
    assert 61 <= body["trust_score"] <= 80
    assert body["trust_level"] == "trusted"
    assert body["suggestions"]
    assert {component["name"] for component in body["components"]} == {
        "material_coverage",
        "memory_review_rate",
        "source_traceability",
        "expression_habit_completeness",
        "multimodal_completeness",
    }
    assert {component["name"]: component["weight"] for component in body["components"]} == {
        "material_coverage": 0.25,
        "memory_review_rate": 0.25,
        "source_traceability": 0.2,
        "expression_habit_completeness": 0.15,
        "multimodal_completeness": 0.15,
    }
    assert job_count(db_session, persona["id"], "calculate_trust_score") == 1


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


def test_disabled_rejected_deleted_memories_do_not_enter_generated_profile(client):
    token = register_user(client, "m4-profile-exclude@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"])
    create_manual_material(client, token, persona["id"], "我们一起过生日。外婆喜欢桂花糕。")
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
