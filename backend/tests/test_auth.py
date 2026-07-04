def test_register_login_and_current_user(client):
    register = client.post(
        "/api/auth/register",
        json={
            "email": "demo@example.com",
            "password": "passw0rd",
            "display_name": "Demo",
        },
    )
    assert register.status_code == 201
    token = register.json()["access_token"]
    assert register.json()["token_type"] == "bearer"

    login = client.post(
        "/api/auth/login",
        json={"email": "demo@example.com", "password": "passw0rd"},
    )
    assert login.status_code == 200

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "demo@example.com"


def test_login_rejects_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "demo@example.com",
            "password": "passw0rd",
            "display_name": "Demo",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "demo@example.com", "password": "wrong-pass"},
    )

    assert response.status_code == 401


def test_demo_session_returns_token_and_seeded_persona(client):
    response = client.post("/api/auth/demo")

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["demo_persona_id"]
    assert body["user"]["plan_type"] == "guest_demo"

    auth = {"Authorization": f"Bearer {body['access_token']}"}
    personas = client.get("/api/personas", headers=auth)

    assert personas.status_code == 200
    items = personas.json()["items"]
    assert [item["name"] for item in items] == ["外婆"]
    assert items[0]["id"] == body["demo_persona_id"]
    assert items[0]["age"] == 72
    assert items[0]["user_nickname_by_persona"] == "小铭"


def test_demo_persona_has_materials_memories_profile_and_chat_citations(client):
    demo = client.post("/api/auth/demo")
    assert demo.status_code == 201
    demo_body = demo.json()
    persona_id = demo_body["demo_persona_id"]
    auth = {"Authorization": f"Bearer {demo_body['access_token']}"}

    materials = client.get(f"/api/personas/{persona_id}/materials", headers=auth)
    memories = client.get(f"/api/personas/{persona_id}/memories", headers=auth)
    profile = client.get(f"/api/personas/{persona_id}/profile", headers=auth)

    assert materials.status_code == 200
    assert len(materials.json()["items"]) >= 3
    assert memories.status_code == 200
    memory_items = memories.json()["items"]
    assert memory_items
    assert {memory["status"] for memory in memory_items} == {"confirmed"}
    assert profile.status_code == 200
    assert profile.json()["trust_score"] > 0

    conversation = client.post(
        f"/api/personas/{persona_id}/conversations",
        json={"title": "演示对话"},
        headers=auth,
    )
    assert conversation.status_code == 201
    reply = client.post(
        f"/api/conversations/{conversation.json()['id']}/messages",
        json={"content": "外婆，你以前喜欢做什么给我吃？"},
        headers=auth,
    )

    assert reply.status_code == 201
    reply_body = reply.json()
    assert "小铭" in reply_body["content"]
    assert reply_body["citations"]


def test_openapi_documents_bearer_token_auth(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schemes = response.json()["components"]["securitySchemes"]
    bearer_schemes = [
        scheme
        for scheme in schemes.values()
        if scheme.get("type") == "http" and scheme.get("scheme") == "bearer"
    ]
    oauth2_schemes = [
        scheme for scheme in schemes.values() if scheme.get("type") == "oauth2"
    ]

    assert bearer_schemes
    assert oauth2_schemes == []
