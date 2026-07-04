from __future__ import annotations

from test_chat import (
    auth,
    confirm_memory,
    create_conversation,
    create_manual_material,
    create_memory,
    create_persona,
    register_user,
    send_message,
)


def _setup(client):
    token = register_user(client, "audit-test@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"])
    return token, persona


# ── audit log writing ──────────────────────────────────────────────────────

def test_audit_log_written_on_memory_creation(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包馄饨给小铭吃。", title="测试记忆",
    )

    response = client.get(
        f"/api/personas/{persona['id']}/audit/logs?event_type=memory.created",
        headers=auth(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert data["items"][0]["event_type"] == "memory.created"
    assert data["items"][0]["target_id"] == memory["id"]


def test_audit_log_written_on_memory_confirm(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包馄饨给小铭吃。",
    )
    confirm_memory(client, token, memory["id"])

    response = client.get(
        f"/api/personas/{persona['id']}/audit/logs?event_type=memory.confirmed",
        headers=auth(token),
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_audit_log_written_on_memory_correction_in_chat(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包饺子给小铭吃。",
    )
    confirm_memory(client, token, memory["id"])
    conversation = create_conversation(client, token, persona["id"])
    reply = send_message(client, token, conversation["id"], "你喜欢做什么给我吃？")

    client.post(
        f"/api/messages/{reply['id']}/correct-memory",
        headers=auth(token),
        json={"memory_id": memory["id"], "content": "外婆喜欢包馄饨给小铭吃。"},
    )

    response = client.get(
        f"/api/personas/{persona['id']}/audit/logs?event_type=memory.corrected_in_chat",
        headers=auth(token),
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_audit_log_written_on_memory_deletion(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包馄饨给小铭吃。",
    )
    memory_id = memory["id"]

    client.delete(f"/api/memories/{memory_id}", headers=auth(token))

    response = client.get(
        f"/api/personas/{persona['id']}/audit/logs?event_type=memory.deleted",
        headers=auth(token),
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1


# ── audit summary ─────────────────────────────────────────────────────────

def test_audit_summary_returns_stats(client):
    token, persona = _setup(client)

    response = client.get(
        f"/api/personas/{persona['id']}/audit/summary",
        headers=auth(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_events" in data
    assert "by_severity" in data
    assert "by_event_type" in data
    assert "open_conflicts" in data


# ── conflict detection ────────────────────────────────────────────────────

def test_conflict_detection_on_contradictory_memories(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])

    create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包馄饨给小铭吃。", title="喜欢馄饨", category="preference",
    )
    create_memory(
        client, token, persona["id"], material["id"],
        "外婆不喜欢吃馄饨。", title="不喜欢馄饨", category="preference",
    )

    conflicts = client.get(
        f"/api/personas/{persona['id']}/audit/conflicts",
        headers=auth(token),
    )
    assert conflicts.status_code == 200
    assert len(conflicts.json()["items"]) >= 1


def test_resolve_conflict(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])

    create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包馄饨给小铭吃。", title="喜欢馄饨", category="preference",
    )
    create_memory(
        client, token, persona["id"], material["id"],
        "外婆不喜欢吃馄饨。", title="不喜欢馄饨", category="preference",
    )

    conflicts = client.get(
        f"/api/personas/{persona['id']}/audit/conflicts",
        headers=auth(token),
    ).json()
    conflict_id = conflicts["items"][0]["id"]

    resolve = client.post(
        f"/api/personas/{persona['id']}/audit/conflicts/{conflict_id}/resolve",
        headers=auth(token),
        json={"resolution": "dismissed"},
    )
    assert resolve.status_code == 200
    assert resolve.json()["resolution_status"] == "dismissed"


# ── dashboard ──────────────────────────────────────────────────────────────

def test_audit_dashboard_returns_health_score(client):
    token, persona = _setup(client)

    response = client.get(
        f"/api/personas/{persona['id']}/audit/dashboard",
        headers=auth(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert "memory_health_score" in data
    assert "review_queue_size" in data
    assert "open_conflict_count" in data
    assert "source_coverage" in data
    assert 0 <= data["memory_health_score"] <= 100


# ── memory change history ─────────────────────────────────────────────────

def test_memory_change_history(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包馄饨给小铭吃。",
    )
    confirm_memory(client, token, memory["id"])

    response = client.get(
        f"/api/memories/{memory['id']}/history",
        headers=auth(token),
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 2  # created + confirmed


# ── audit report ───────────────────────────────────────────────────────────

def test_audit_report_generation(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包馄饨给小铭吃。",
    )
    confirm_memory(client, token, memory["id"])

    response = client.get(
        f"/api/personas/{persona['id']}/audit/report",
        headers=auth(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert "report_generated_at" in data
    assert "timeline" in data
    assert "source_coverage" in data


# ── retrieval tracking ────────────────────────────────────────────────────

def test_memory_retrieval_is_audited(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包馄饨给小铭吃。",
    )
    confirm_memory(client, token, memory["id"])
    conversation = create_conversation(client, token, persona["id"])
    send_message(client, token, conversation["id"], "你以前喜欢做什么给我吃？")

    response = client.get(
        f"/api/personas/{persona['id']}/audit/logs?event_type=memory.retrieved",
        headers=auth(token),
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1
    assert response.json()["items"][0]["severity"] == "debug"


# ── cross-user rejection ──────────────────────────────────────────────────

def test_audit_rejects_cross_user_access(client):
    owner_token, owner_persona = _setup(client)
    other_token = register_user(client, "audit-other@example.com")

    response = client.get(
        f"/api/personas/{owner_persona['id']}/audit/summary",
        headers=auth(other_token),
    )
    assert response.status_code == 404


# ── audit event filtering ─────────────────────────────────────────────────

def test_audit_logs_are_filterable(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])
    create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包馄饨给小铭吃。",
    )

    all_logs = client.get(
        f"/api/personas/{persona['id']}/audit/logs",
        headers=auth(token),
    ).json()

    filtered = client.get(
        f"/api/personas/{persona['id']}/audit/logs?severity=info",
        headers=auth(token),
    ).json()
    assert filtered["total"] <= all_logs["total"]

    filtered_by_type = client.get(
        f"/api/personas/{persona['id']}/audit/logs?event_type=memory.created",
        headers=auth(token),
    ).json()
    assert filtered_by_type["total"] >= 1
    assert all(
        item["event_type"] == "memory.created"
        for item in filtered_by_type["items"]
    )


# ── semantic search ───────────────────────────────────────────────────────

def test_semantic_search_returns_results(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])
    create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包馄饨给小铭吃。", title="包馄饨",
    )
    create_memory(
        client, token, persona["id"], material["id"],
        "外婆每周三都去买菜。", title="买菜",
    )

    response = client.post(
        f"/api/personas/{persona['id']}/audit/search",
        headers=auth(token),
        json={"query": "馄饨", "top_k": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "馄饨"
    assert len(data["results"]) >= 1
    result = data["results"][0]
    assert "relevance_score" in result
    assert "馄饨" in result["content"]


def test_semantic_search_no_results(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])
    create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包馄饨给小铭吃。", title="包馄饨",
    )

    response = client.post(
        f"/api/personas/{persona['id']}/audit/search",
        headers=auth(token),
        json={"query": "星际穿越", "top_k": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_found"] == 0


def test_semantic_search_audited(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])
    create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包馄饨给小铭吃。",
    )

    client.post(
        f"/api/personas/{persona['id']}/audit/search",
        headers=auth(token),
        json={"query": "馄饨"},
    )

    response = client.get(
        f"/api/personas/{persona['id']}/audit/logs?event_type=memory.searched",
        headers=auth(token),
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1
