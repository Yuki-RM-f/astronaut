import pytest

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


def create_manual_material(client, token: str, persona_id: str) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/materials/manual",
        headers=auth(token),
        json={"manual_text": "外婆喜欢包馄饨。", "importance": "very_important"},
    )
    assert response.status_code == 201
    return response.json()


def set_job_status(db_session, job_id: str, status: str) -> AIJob:
    job = db_session.get(AIJob, job_id)
    assert job is not None
    job.status = status
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_jobs_are_user_scoped_and_retry_cancel_statuses(client):
    owner_token = register_user(client, "owner@example.com")
    other_token = register_user(client, "other@example.com")
    persona = create_persona(client, owner_token)
    material = create_manual_material(client, owner_token, persona["id"])
    job_id = material["jobs"][0]["id"]

    assert client.get(f"/api/jobs/{job_id}", headers=auth(other_token)).status_code == 404
    retry = client.post(f"/api/jobs/{job_id}/retry", headers=auth(owner_token))
    assert retry.status_code == 200
    assert retry.json()["status"] == "retrying"
    assert retry.json()["retry_count"] == 1
    cancel = client.post(f"/api/jobs/{job_id}/cancel", headers=auth(owner_token))
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "canceled"


def test_retry_rejects_running_job(client, db_session):
    token = register_user(client, "retry-running@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    job_id = material["jobs"][0]["id"]
    set_job_status(db_session, job_id, "running")

    response = client.post(f"/api/jobs/{job_id}/retry", headers=auth(token))

    assert response.status_code == 409
    assert "running" in response.json()["detail"]
    job = db_session.get(AIJob, job_id)
    assert job.status == "running"
    assert job.retry_count == 0


@pytest.mark.parametrize("job_status", ["succeeded", "failed", "canceled"])
def test_cancel_rejects_terminal_or_already_canceled_jobs(client, db_session, job_status):
    token = register_user(client, f"cancel-{job_status}@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    job_id = material["jobs"][0]["id"]
    set_job_status(db_session, job_id, job_status)

    response = client.post(f"/api/jobs/{job_id}/cancel", headers=auth(token))

    assert response.status_code == 409
    assert job_status in response.json()["detail"]
    job = db_session.get(AIJob, job_id)
    assert job.status == job_status


def test_persona_jobs_list_is_user_scoped(client):
    owner_token = register_user(client, "job-list-owner@example.com")
    other_token = register_user(client, "job-list-other@example.com")
    persona = create_persona(client, owner_token)
    material = create_manual_material(client, owner_token, persona["id"])

    listed = client.get(f"/api/personas/{persona['id']}/jobs", headers=auth(owner_token))
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [material["jobs"][0]["id"]]

    assert client.get(f"/api/personas/{persona['id']}/jobs", headers=auth(other_token)).status_code == 404


def test_job_detail_returns_source_material_id(client):
    token = register_user(client, "job-detail@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    job_id = material["jobs"][0]["id"]

    response = client.get(f"/api/jobs/{job_id}", headers=auth(token))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == job_id
    assert body["persona_id"] == persona["id"]
    assert body["source_material_id"] == material["id"]
    assert body["job_type"] == "parse_text"
    assert body["status"] == "pending"
