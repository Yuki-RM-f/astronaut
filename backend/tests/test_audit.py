from __future__ import annotations

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.memory_conflict import MemoryConflict

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


def audit_events(client, token: str, persona_id: str, event_type: str | None = None):
    params = {"event_type": event_type} if event_type else None
    response = client.get(
        f"/api/personas/{persona_id}/audit/logs",
        headers=auth(token),
        params=params,
    )
    assert response.status_code == 200
    return response.json()["items"]


def test_memory_lifecycle_writes_audit_events_and_filters(client):
    token = register_user(client, "audit-lifecycle@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])

    memory = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢在厨房教我包馄饨。",
        title="厨房里的馄饨",
    )
    confirmed = confirm_memory(client, token, memory["id"])
    edited = client.patch(
        f"/api/memories/{memory['id']}",
        headers=auth(token),
        json={"content": "外婆喜欢在厨房慢慢教我包馄饨。"},
    )
    rejected = client.post(f"/api/memories/{memory['id']}/reject", headers=auth(token))
    disabled = client.post(f"/api/memories/{memory['id']}/disable", headers=auth(token))
    deleted = client.delete(f"/api/memories/{memory['id']}", headers=auth(token))

    assert confirmed["status"] == "confirmed"
    assert edited.status_code == 200
    assert rejected.status_code == 200
    assert disabled.status_code == 200
    assert deleted.status_code == 204

    created_events = [
        item
        for item in audit_events(client, token, persona["id"], "memory.created")
        if item["target_id"] == memory["id"]
    ]
    assert len(created_events) == 1
    assert created_events[0]["severity"] == "info"
    assert created_events[0]["changed_fields"]

    all_event_types = {item["event_type"] for item in audit_events(client, token, persona["id"])}
    assert {
        "memory.created",
        "memory.confirmed",
        "memory.updated",
        "memory.rejected",
        "memory.disabled",
        "memory.deleted",
    }.issubset(all_event_types)


def test_audit_summary_dashboard_report_and_memory_history(client):
    token = register_user(client, "audit-summary@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆总说慢慢来，先把话说清楚。",
        title="慢慢来",
        category="expression_style",
    )
    confirm_memory(client, token, memory["id"])

    summary = client.get(
        f"/api/personas/{persona['id']}/audit/summary",
        headers=auth(token),
    )
    dashboard = client.get(
        f"/api/personas/{persona['id']}/audit/dashboard",
        headers=auth(token),
    )
    report = client.get(
        f"/api/personas/{persona['id']}/audit/report",
        headers=auth(token),
    )
    history = client.get(f"/api/memories/{memory['id']}/history", headers=auth(token))

    assert summary.status_code == 200
    assert summary.json()["total_events"] >= 2
    assert summary.json()["by_event_type"]["memory.created"] >= 1
    assert dashboard.status_code == 200
    assert 0 <= dashboard.json()["health_score"] <= 100
    assert "recent_events" in dashboard.json()
    assert report.status_code == 200
    assert report.json()["persona_id"] == persona["id"]
    assert history.status_code == 200
    assert {item["event_type"] for item in history.json()["events"]} == {
        "memory.created",
        "memory.confirmed",
    }


def test_semantic_search_returns_ranked_results_and_writes_search_audit(client):
    token = register_user(client, "audit-search@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢用虾仁和青菜包馄饨给小铭吃。",
        title="虾仁馄饨",
    )
    confirm_memory(client, token, memory["id"])

    response = client.post(
        f"/api/personas/{persona['id']}/audit/search",
        headers=auth(token),
        json={"query": "馄饨", "top_k": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "馄饨"
    assert body["items"]
    assert body["items"][0]["memory"]["id"] == memory["id"]
    assert body["items"][0]["relevance_score"] > 0
    assert body["items"][0]["source_excerpt"]
    assert audit_events(client, token, persona["id"], "memory.searched")


def test_semantic_search_can_match_long_term_memory_context_location(client):
    token = register_user(client, "audit-search-context@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆给小铭准备了一碗热汤。",
        title="热汤",
        source_location="manual:生日线索",
    )
    confirm_memory(client, token, memory["id"])

    response = client.post(
        f"/api/personas/{persona['id']}/audit/search",
        headers=auth(token),
        json={"query": "生日线索", "top_k": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"]
    assert body["items"][0]["memory"]["id"] == memory["id"]
    assert body["items"][0]["memory"]["source_location"] == "manual:生日线索"


def test_semantic_search_does_not_return_short_term_context_as_result(client):
    token = register_user(client, "audit-search-short-term-only@example.com")
    persona = create_persona(client, token)
    conversation = create_conversation(client, token, persona["id"])
    send_message(client, token, conversation["id"], "这是一段只在短期对话里的生日线索。")

    response = client.post(
        f"/api/personas/{persona['id']}/audit/search",
        headers=auth(token),
        json={"query": "生日线索", "top_k": 5},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_conflict_detection_and_resolution_are_user_scoped(client, db_session):
    owner_token = register_user(client, "audit-conflict-owner@example.com")
    other_token = register_user(client, "audit-conflict-other@example.com")
    persona = create_persona(client, owner_token)
    material = create_manual_material(client, owner_token, persona["id"])
    first = create_memory(
        client,
        owner_token,
        persona["id"],
        material["id"],
        "外婆喜欢吃馄饨。",
        title="喜欢馄饨",
    )
    confirm_memory(client, owner_token, first["id"])
    second = create_memory(
        client,
        owner_token,
        persona["id"],
        material["id"],
        "外婆不喜欢吃馄饨。",
        title="不喜欢馄饨",
    )
    confirm_memory(client, owner_token, second["id"])

    conflicts = client.get(
        f"/api/personas/{persona['id']}/audit/conflicts",
        headers=auth(owner_token),
    )
    assert conflicts.status_code == 200
    assert conflicts.json()["items"]
    conflict = conflicts.json()["items"][0]
    assert conflict["resolution_status"] == "open"

    blocked = client.post(
        f"/api/personas/{persona['id']}/audit/conflicts/{conflict['id']}/resolve",
        headers=auth(other_token),
        json={"resolution_status": "dismissed"},
    )
    assert blocked.status_code == 404

    resolved = client.post(
        f"/api/personas/{persona['id']}/audit/conflicts/{conflict['id']}/resolve",
        headers=auth(owner_token),
        json={"resolution_status": "resolved_by_user"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["resolution_status"] == "resolved_by_user"
    assert resolved.json()["resolved_by"] is not None
    assert resolved.json()["resolved_at"] is not None

    db_session.expire_all()
    saved = db_session.scalar(select(MemoryConflict).where(MemoryConflict.id == conflict["id"]))
    assert saved is not None
    assert saved.resolution_status == "resolved_by_user"


def test_chat_retrieval_and_correction_write_audit_events(client):
    token = register_user(client, "audit-chat@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    memory = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆喜欢包馄饨给小铭吃。",
        title="馄饨",
    )
    confirm_memory(client, token, memory["id"])
    conversation = create_conversation(client, token, persona["id"])
    reply = send_message(client, token, conversation["id"], "外婆喜欢做什么给我吃？")
    assert reply["citations"]

    correction = client.post(
        f"/api/messages/{reply['id']}/correct-memory",
        headers=auth(token),
        json={"memory_id": memory["id"], "content": "外婆喜欢包虾仁馄饨给小铭吃。"},
    )
    assert correction.status_code == 200

    event_types = {item["event_type"] for item in audit_events(client, token, persona["id"])}
    assert "memory.retrieved" in event_types
    assert "memory.corrected_in_chat" in event_types


def test_audit_routes_return_404_for_cross_user_access(client, db_session):
    owner_token = register_user(client, "audit-scope-owner@example.com")
    other_token = register_user(client, "audit-scope-other@example.com")
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

    for method, path, body in [
        ("get", f"/api/personas/{persona['id']}/audit/logs", None),
        ("get", f"/api/personas/{persona['id']}/audit/summary", None),
        ("get", f"/api/personas/{persona['id']}/audit/report", None),
        ("get", f"/api/personas/{persona['id']}/audit/dashboard", None),
        ("get", f"/api/personas/{persona['id']}/audit/conflicts", None),
        ("post", f"/api/personas/{persona['id']}/audit/search", {"query": "馄饨"}),
        ("get", f"/api/memories/{memory['id']}/history", None),
    ]:
        if method == "get":
            response = client.get(path, headers=auth(other_token))
        else:
            response = client.post(path, headers=auth(other_token), json=body)
        assert response.status_code == 404

    # No synthetic system user should be written into the FK-backed audit table.
    assert not db_session.scalars(select(AuditLog).where(AuditLog.user_id == "system")).all()
