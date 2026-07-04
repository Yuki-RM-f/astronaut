import pytest


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
        "language",
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
        json={"relationship_to_user": "奶奶", "user_nickname_by_persona": "小明"},
    )
    assert patched.status_code == 200
    assert patched.json()["relationship_to_user"] == "奶奶"
    assert patched.json()["prompt_context"]["user_nickname_by_persona"] == "小明"

    deleted = client.delete(f"/api/personas/{created['id']}", headers=auth(token))
    assert deleted.status_code == 204
    assert client.get(f"/api/personas/{created['id']}", headers=auth(token)).status_code == 404
    assert client.get("/api/personas", headers=auth(token)).json()["items"] == []


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
