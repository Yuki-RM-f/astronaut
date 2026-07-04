def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_user(client, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "passw0rd", "display_name": "Demo"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def persona_payload(name: str = "外婆") -> dict[str, str]:
    return {
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
        "emotional_style": "先安慰，再鼓励",
        "forbidden_expressions": "不要说我真的回来了",
    }


def create_persona(client, token: str, name: str = "外婆") -> dict:
    response = client.post(
        "/api/personas",
        headers=auth(token),
        json=persona_payload(name),
    )
    assert response.status_code == 201
    return response.json()


def create_manual_material(client, token: str, persona_id: str) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/materials/manual",
        headers=auth(token),
        json={"manual_text": "这是一段故事来源。", "importance": "important"},
    )
    assert response.status_code == 201
    return response.json()


def create_memory(
    client,
    token: str,
    persona_id: str,
    material_id: str,
    content: str,
    *,
    title: str = "手动记忆",
    category: str = "shared_event",
    source_location: str = "manual:story-test",
) -> dict:
    response = client.post(
        f"/api/personas/{persona_id}/memories",
        headers=auth(token),
        json={
            "title": title,
            "content": content,
            "category": category,
            "confidence_level": "high",
            "confidence_score": 90,
            "source_material_id": material_id,
            "source_quote": content,
            "source_location": source_location,
        },
    )
    assert response.status_code == 201
    return response.json()


def confirm_memory(client, token: str, memory_id: str) -> dict:
    response = client.post(f"/api/memories/{memory_id}/confirm", headers=auth(token))
    assert response.status_code == 200
    return response.json()


def test_generate_story_uses_reviewed_memories_and_creates_audio_jobs(client):
    token = register_user(client, "story-generate@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    reviewed = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆每年生日都会包馄饨给小铭吃。",
        title="生日馄饨",
    )
    confirm_memory(client, token, reviewed["id"])
    pending = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆藏着一个没有确认的秘密菜。",
        title="待审核秘密",
    )

    response = client.post(
        f"/api/personas/{persona['id']}/stories",
        headers=auth(token),
        json={"theme": "共同经历"},
    )

    assert response.status_code == 201
    story = response.json()
    assert story["persona_id"] == persona["id"]
    assert story["theme"] == "共同经历"
    assert story["is_favorite"] is False
    assert story["audio_url"].startswith("mock://tts/")
    assert "我" in story["content"]
    assert "小铭" in story["content"]
    assert "馄饨" in story["content"]
    assert "秘密菜" not in story["content"]
    assert story["source_memory_ids"] == [reviewed["id"]]
    assert story["source_memories"][0]["memory_card_id"] == reviewed["id"]
    assert story["source_memories"][0]["quote"] == "外婆每年生日都会包馄饨给小铭吃。"
    assert story["metadata_json"]["provider"]["capability"] == "story_generation"
    assert story["metadata_json"]["generate_story_job_id"]
    assert story["metadata_json"]["synthesize_speech_job_id"]

    listed = client.get(f"/api/personas/{persona['id']}/stories", headers=auth(token))
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [story["id"]]

    jobs = client.get(f"/api/personas/{persona['id']}/jobs", headers=auth(token))
    assert jobs.status_code == 200
    job_types = {item["job_type"]: item["status"] for item in jobs.json()["items"]}
    assert job_types["generate_story"] == "succeeded"
    assert job_types["synthesize_speech"] == "succeeded"
    assert pending["id"] not in story["source_memory_ids"]


def test_generate_story_requires_confirmed_or_corrected_memory(client):
    token = register_user(client, "story-no-reviewed@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "这条记忆尚未审核。",
    )

    response = client.post(
        f"/api/personas/{persona['id']}/stories",
        headers=auth(token),
        json={"theme": "温柔安慰"},
    )

    assert response.status_code == 400


def test_favorite_story_and_story_routes_are_user_scoped(client):
    owner_token = register_user(client, "story-owner@example.com")
    other_token = register_user(client, "story-other@example.com")
    persona = create_persona(client, owner_token)
    material = create_manual_material(client, owner_token, persona["id"])
    reviewed = create_memory(
        client,
        owner_token,
        persona["id"],
        material["id"],
        "外婆常在春节给小铭准备热茶。",
        title="春节热茶",
    )
    confirm_memory(client, owner_token, reviewed["id"])
    story = client.post(
        f"/api/personas/{persona['id']}/stories",
        headers=auth(owner_token),
        json={"theme": "节日问候"},
    ).json()

    favorite = client.post(
        f"/api/stories/{story['id']}/favorite",
        headers=auth(owner_token),
        json={"is_favorite": True},
    )

    assert favorite.status_code == 200
    assert favorite.json()["is_favorite"] is True

    assert (
        client.get(f"/api/personas/{persona['id']}/stories", headers=auth(other_token)).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/personas/{persona['id']}/stories",
            headers=auth(other_token),
            json={"theme": "节日问候"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/stories/{story['id']}/favorite",
            headers=auth(other_token),
            json={"is_favorite": False},
        ).status_code
        == 404
    )


def test_export_story_returns_text_and_audio_metadata(client):
    token = register_user(client, "story-export@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    reviewed = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆在生日那天给小铭煮了一碗热馄饨。",
        title="生日热馄饨",
    )
    confirm_memory(client, token, reviewed["id"])
    story = client.post(
        f"/api/personas/{persona['id']}/stories",
        headers=auth(token),
        json={"theme": "生日"},
    ).json()

    response = client.get(
        f"/api/personas/{persona['id']}/export/story/{story['id']}",
        headers=auth(token),
    )

    assert response.status_code == 200
    exported = response.json()
    assert exported["story_id"] == story["id"]
    assert exported["persona_id"] == persona["id"]
    assert exported["theme"] == "生日"
    assert exported["text_filename"] == f"story-{story['id']}.txt"
    assert exported["audio_filename"] == f"story-{story['id']}.wav"
    assert exported["audio_url"] == story["audio_url"]
    assert "mock TTS" in exported["audio_export_notice"]
    assert story["title"] in exported["export_text"]
    assert story["content"] in exported["export_text"]
    assert "来源记忆" in exported["export_text"]
    assert "生日热馄饨" in exported["export_text"]
    assert exported["source_memory_ids"] == [reviewed["id"]]
    assert exported["source_memories"][0]["memory_card_id"] == reviewed["id"]


def test_export_story_audio_returns_watermarked_wav_file(client):
    token = register_user(client, "story-audio-export@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    reviewed = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆在旅行前总会提醒小铭带好水杯。",
        title="旅行水杯",
    )
    confirm_memory(client, token, reviewed["id"])
    story = client.post(
        f"/api/personas/{persona['id']}/stories",
        headers=auth(token),
        json={"theme": "旅行"},
    ).json()

    response = client.get(
        f"/api/personas/{persona['id']}/export/story/{story['id']}/audio",
        headers=auth(token),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.headers["content-disposition"] == (
        f'attachment; filename="story-{story["id"]}.wav"'
    )
    assert "AI simulation mock TTS audio" in response.headers["x-ai-simulation-notice"]
    assert response.content.startswith(b"RIFF")
    assert b"WAVE" in response.content[:16]
    assert b"AI simulation mock TTS audio" in response.content
    assert b"not TA real voice" in response.content


def test_export_story_is_scoped_to_owner_and_persona(client):
    owner_token = register_user(client, "story-export-owner@example.com")
    other_token = register_user(client, "story-export-other@example.com")
    persona = create_persona(client, owner_token)
    other_persona = create_persona(client, owner_token, "爷爷")
    material = create_manual_material(client, owner_token, persona["id"])
    reviewed = create_memory(
        client,
        owner_token,
        persona["id"],
        material["id"],
        "外婆常在旅行前帮小铭收拾水杯。",
        title="旅行水杯",
    )
    confirm_memory(client, owner_token, reviewed["id"])
    story = client.post(
        f"/api/personas/{persona['id']}/stories",
        headers=auth(owner_token),
        json={"theme": "旅行"},
    ).json()

    assert (
        client.get(
            f"/api/personas/{persona['id']}/export/story/{story['id']}",
            headers=auth(other_token),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/personas/{other_persona['id']}/export/story/{story['id']}",
            headers=auth(owner_token),
        ).status_code
        == 404
    )
