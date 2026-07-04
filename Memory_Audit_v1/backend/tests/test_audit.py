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
    """Create user, persona, material. Returns (token, persona)."""
    token = register_user(client, "audit-test@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"])
    return token, persona


# ── audit log writing ────────────────────────────────────────────────────

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


# ── audit summary ────────────────────────────────────────────────────────

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
    assert "unacknowledged_drifts" in data


# ── snapshots ─────────────────────────────────────────────────────────────

def test_create_and_list_snapshots(client):
    token, persona = _setup(client)

    create_resp = client.post(
        f"/api/personas/{persona['id']}/audit/snapshots",
        headers=auth(token),
        json={"snapshot_type": "manual", "label": "测试快照"},
    )
    assert create_resp.status_code == 201
    snapshot = create_resp.json()
    assert snapshot["snapshot_type"] == "manual"
    assert snapshot["label"] == "测试快照"

    list_resp = client.get(
        f"/api/personas/{persona['id']}/audit/snapshots",
        headers=auth(token),
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) >= 1


def test_compare_snapshots(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])
    create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包馄饨给小铭吃。",
    )

    s1 = client.post(
        f"/api/personas/{persona['id']}/audit/snapshots",
        headers=auth(token),
        json={"snapshot_type": "manual", "label": "V1"},
    ).json()
    s2 = client.post(
        f"/api/personas/{persona['id']}/audit/snapshots",
        headers=auth(token),
        json={"snapshot_type": "manual", "label": "V2"},
    ).json()

    compare_resp = client.get(
        f"/api/personas/{persona['id']}/audit/snapshots/compare",
        headers=auth(token),
        params={"snapshot_id_a": s1["id"], "snapshot_id_b": s2["id"]},
    )
    assert compare_resp.status_code == 200
    data = compare_resp.json()
    assert "trust_score_delta" in data
    assert "persona_changes" in data


# ── rollback ──────────────────────────────────────────────────────────────

def test_rollback_requires_confirmed(client):
    token, persona = _setup(client)

    s = client.post(
        f"/api/personas/{persona['id']}/audit/snapshots",
        headers=auth(token),
        json={"snapshot_type": "manual", "label": "测试快照"},
    ).json()

    resp = client.post(
        f"/api/personas/{persona['id']}/audit/rollback",
        headers=auth(token),
        json={"snapshot_id": s["id"], "confirmed": False},
    )
    assert resp.status_code == 400


def test_rollback_restores_state(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包馄饨给小铭吃。",
    )
    confirm_memory(client, token, memory["id"])

    # Take snapshot
    s = client.post(
        f"/api/personas/{persona['id']}/audit/snapshots",
        headers=auth(token),
        json={"snapshot_type": "manual", "label": "V1"},
    ).json()
    snapshot_memory_count = s["memory_count"]

    # Create more memories after snapshot
    material2 = create_manual_material(client, token, persona["id"])
    create_memory(
        client, token, persona["id"], material2["id"],
        "外婆喜欢讲故事。", title="新记忆",
    )

    # Verify more memories exist
    list_resp = client.get(
        f"/api/personas/{persona['id']}/memories",
        headers=auth(token),
    )
    assert len(list_resp.json()["items"]) > snapshot_memory_count

    # Rollback
    rollback = client.post(
        f"/api/personas/{persona['id']}/audit/rollback",
        headers=auth(token),
        json={"snapshot_id": s["id"], "confirmed": True},
    )
    assert rollback.status_code == 200
    assert rollback.json()["success"] is True

    # After rollback, memory count should be back to snapshot count
    after_list = client.get(
        f"/api/personas/{persona['id']}/memories",
        headers=auth(token),
    )
    assert len(after_list.json()["items"]) == snapshot_memory_count


# ── conflict detection ────────────────────────────────────────────────────

def test_conflict_detection_on_contradictory_memories(client):
    token, persona = _setup(client)
    material = create_manual_material(client, token, persona["id"])

    mem_a = create_memory(
        client, token, persona["id"], material["id"],
        "外婆喜欢包馄饨给小铭吃。", title="喜欢馄饨", category="preference",
    )
    mem_b = create_memory(
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


# ── drift detection ───────────────────────────────────────────────────────

def test_drift_detection_on_memory_count_change(client):
    token, persona = _setup(client)

    s1 = client.post(
        f"/api/personas/{persona['id']}/audit/snapshots",
        headers=auth(token),
        json={"snapshot_type": "auto_periodic", "label": "Before"},
    ).json()

    # Add many memories to trigger drift
    material = create_manual_material(client, token, persona["id"])
    for i in range(3):
        create_memory(
            client, token, persona["id"], material["id"],
            f"记忆内容 {i}", title=f"记忆{i}",
        )

    s2 = client.post(
        f"/api/personas/{persona['id']}/audit/snapshots",
        headers=auth(token),
        json={"snapshot_type": "auto_periodic", "label": "After"},
    ).json()

    drifts = client.get(
        f"/api/personas/{persona['id']}/audit/drifts?unacknowledged_only=true",
        headers=auth(token),
    )
    assert drifts.status_code == 200
    drift_items = drifts.json()["items"]
    # memory_count should have drifted (0 → 3 is a large relative change)
    assert any(d["dimension"] == "memory_count" for d in drift_items)


def test_acknowledge_drift(client):
    token, persona = _setup(client)

    s1 = client.post(
        f"/api/personas/{persona['id']}/audit/snapshots",
        headers=auth(token),
        json={"snapshot_type": "auto_periodic"},
    ).json()

    material = create_manual_material(client, token, persona["id"])
    for i in range(3):
        create_memory(
            client, token, persona["id"], material["id"],
            f"记忆内容 {i}", title=f"记忆{i}",
        )

    client.post(
        f"/api/personas/{persona['id']}/audit/snapshots",
        headers=auth(token),
        json={"snapshot_type": "auto_periodic"},
    )

    drifts = client.get(
        f"/api/personas/{persona['id']}/audit/drifts",
        headers=auth(token),
    ).json()
    drift_id = drifts["items"][0]["id"]

    ack = client.post(
        f"/api/personas/{persona['id']}/audit/drifts/{drift_id}/acknowledge",
        headers=auth(token),
    )
    assert ack.status_code == 200
    assert ack.json()["acknowledged_at"] is not None


# ── dashboard ─────────────────────────────────────────────────────────────

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


# ── audit report ──────────────────────────────────────────────────────────

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
    assert "trust_trend" in data
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
    # Verify debug events are returned in query
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
