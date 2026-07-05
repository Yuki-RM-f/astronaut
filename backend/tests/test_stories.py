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


def test_generate_story_payload_uses_memory_markdown_and_filters_model_sources(
    client,
    monkeypatch,
):
    from app.services import stories as story_service

    captured: dict[str, dict] = {}

    class FakeGateway:
        async def run(self, capability, payload):
            if capability == "story_generation":
                captured["payload"] = payload
                return {
                    "provider_name": "fake_story",
                    "capability": capability,
                    "status": "succeeded",
                    "input": payload,
                    "output": {
                        "title": "生日馄饨",
                        "content": "<think>private reasoning</think>小铭，我还记得生日那天那碗馄饨。",
                        "source_memory_ids": [
                            payload["retrieved_memories"][0]["id"],
                            "pending-memory-id",
                        ],
                        "source_memories": [
                            {
                                "memory_card_id": payload["retrieved_memories"][0]["id"],
                                "title": "生日馄饨",
                                "quote": "外婆在生日那天给小铭包馄饨。",
                                "source_location": "manual:story-test",
                            },
                            {
                                "memory_card_id": "pending-memory-id",
                                "title": "未审核秘密",
                                "quote": "不应被引用",
                                "source_location": "manual:pending",
                            },
                        ],
                    },
                }
            return {
                "provider_name": "fake_tts",
                "capability": capability,
                "status": "succeeded",
                "input": payload,
                "output": {"audio_url": "mock://tts/story-clean"},
            }

    monkeypatch.setattr(story_service, "ProviderGateway", lambda: FakeGateway())

    token = register_user(client, "story-markdown-payload@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    reviewed = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆在生日那天给小铭包馄饨。",
        title="生日馄饨",
    )
    confirm_memory(client, token, reviewed["id"])
    pending = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "这条待审核记忆不能进故事。",
        title="未审核秘密",
    )

    response = client.post(
        f"/api/personas/{persona['id']}/stories",
        headers=auth(token),
        json={"theme": "生日 馄饨"},
    )

    assert response.status_code == 201
    story = response.json()
    assert "<think>" not in story["content"]
    assert "private reasoning" not in story["content"]
    assert story["source_memory_ids"] == [reviewed["id"]]
    assert pending["id"] not in story["source_memory_ids"]
    assert reviewed["id"] in captured["payload"]["long_term_memory_md"]
    assert "short_term_memory_md" in captured["payload"]
    assert captured["payload"]["story_theme"] == "生日 馄饨"
    assert captured["payload"]["source_memory_ids"] == [reviewed["id"]]


def test_generate_story_falls_back_when_model_thinking_leaves_empty_content(
    client,
    monkeypatch,
):
    from app.services import stories as story_service

    class FakeGateway:
        async def run(self, capability, payload):
            if capability == "story_generation":
                return {
                    "provider_name": "fake_story",
                    "capability": capability,
                    "status": "succeeded",
                    "input": payload,
                    "output": {
                        "title": "生日",
                        "content": "<think>only hidden reasoning",
                        "source_memory_ids": [payload["retrieved_memories"][0]["id"]],
                        "source_memories": [],
                    },
                }
            return {
                "provider_name": "fake_tts",
                "capability": capability,
                "status": "succeeded",
                "input": payload,
                "output": {"audio_url": "mock://tts/story-fallback"},
            }

    monkeypatch.setattr(story_service, "ProviderGateway", lambda: FakeGateway())

    token = register_user(client, "story-empty-thinking@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    reviewed = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆生日那天给小铭煮了热汤。",
        title="生日热汤",
    )
    confirm_memory(client, token, reviewed["id"])

    response = client.post(
        f"/api/personas/{persona['id']}/stories",
        headers=auth(token),
        json={"theme": "生日"},
    )

    assert response.status_code == 201
    story = response.json()
    assert "<think>" not in story["content"]
    assert "only hidden reasoning" not in story["content"]
    assert "小铭" in story["content"]
    assert "热汤" in story["content"]
    assert story["source_memory_ids"] == [reviewed["id"]]


def test_seed_stories_generates_three_default_stories_idempotently(client, monkeypatch):
    from app.services import stories as story_service

    class FakeGateway:
        async def run(self, capability, payload):
            if capability == "story_generation":
                source_id = payload["source_memory_ids"][0]
                return {
                    "provider_name": "fake_story",
                    "capability": capability,
                    "status": "succeeded",
                    "input": payload,
                    "output": {
                        "title": f"{payload['story_theme']}的回忆",
                        "content": f"小铭，我还记得{payload['story_theme']}这件事。",
                        "source_memory_ids": [source_id],
                        "source_memories": [],
                    },
                }
            return {
                "provider_name": "fake_tts",
                "capability": capability,
                "status": "succeeded",
                "input": payload,
                "output": {"audio_url": f"mock://tts/{payload['job_id']}"},
            }

    monkeypatch.setattr(story_service, "ProviderGateway", lambda: FakeGateway())

    token = register_user(client, "story-seed-defaults@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    memories = [
        create_memory(
            client,
            token,
            persona["id"],
            material["id"],
            "外婆在码头边牵着小铭看船。",
            title="码头看船",
            source_location="image:码头.png",
        ),
        create_memory(
            client,
            token,
            persona["id"],
            material["id"],
            "外婆在生日时给小铭煮热汤。",
            title="生日热汤",
            source_location="manual:birthday",
        ),
        create_memory(
            client,
            token,
            persona["id"],
            material["id"],
            "外婆鼓励小铭遇事慢慢来。",
            title="慢慢来",
            source_location="manual:comfort",
        ),
    ]
    for memory in memories:
        confirm_memory(client, token, memory["id"])

    response = client.post(
        f"/api/personas/{persona['id']}/stories/seed",
        headers=auth(token),
    )

    assert response.status_code == 200
    stories = response.json()["items"]
    default_stories = [
        story
        for story in stories
        if story["metadata_json"].get("story_kind") == "default_memory_story"
    ]
    assert len(default_stories) == 3
    seed_ids = [story["metadata_json"]["seed_memory_id"] for story in default_stories]
    assert sorted(seed_ids) == sorted(memory["id"] for memory in memories)
    assert sorted(story["metadata_json"]["seed_index"] for story in default_stories) == [
        1,
        2,
        3,
    ]
    for story in default_stories:
        seed_memory_id = story["metadata_json"]["seed_memory_id"]
        assert story["source_memory_ids"][0] == seed_memory_id
        assert story["source_memories"][0]["source_location"]

    repeated = client.post(
        f"/api/personas/{persona['id']}/stories/seed",
        headers=auth(token),
    )

    assert repeated.status_code == 200
    assert [story["id"] for story in repeated.json()["items"]] == [
        story["id"] for story in stories
    ]


def test_seed_stories_uses_only_active_reviewed_memories_and_manual_story_does_not_count(
    client,
    monkeypatch,
):
    from app.services import stories as story_service

    class FakeGateway:
        async def run(self, capability, payload):
            if capability == "story_generation":
                source_id = payload["source_memory_ids"][0]
                return {
                    "provider_name": "fake_story",
                    "capability": capability,
                    "status": "succeeded",
                    "input": payload,
                    "output": {
                        "title": payload["story_theme"],
                        "content": f"小铭，我记得{payload['story_theme']}。",
                        "source_memory_ids": [source_id],
                        "source_memories": [],
                    },
                }
            return {
                "provider_name": "fake_tts",
                "capability": capability,
                "status": "succeeded",
                "input": payload,
                "output": {"audio_url": f"mock://tts/{payload['job_id']}"},
            }

    monkeypatch.setattr(story_service, "ProviderGateway", lambda: FakeGateway())

    token = register_user(client, "story-seed-filter@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    active = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "外婆给小铭包馄饨。",
        title="馄饨",
        source_location="manual:active",
    )
    confirm_memory(client, token, active["id"])
    pending = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "待审核记忆不能默认讲述。",
        title="待审核",
    )
    rejected = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "已拒绝记忆不能默认讲述。",
        title="已拒绝",
    )
    disabled = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "已停用记忆不能默认讲述。",
        title="已停用",
    )
    deleted = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "已删除记忆不能默认讲述。",
        title="已删除",
    )
    assert client.post(f"/api/memories/{rejected['id']}/reject", headers=auth(token)).status_code == 200
    assert client.post(f"/api/memories/{disabled['id']}/disable", headers=auth(token)).status_code == 200
    confirm_memory(client, token, deleted["id"])
    assert client.delete(f"/api/memories/{deleted['id']}", headers=auth(token)).status_code == 204

    manual = client.post(
        f"/api/personas/{persona['id']}/stories",
        headers=auth(token),
        json={"theme": "用户关键词"},
    )
    assert manual.status_code == 201

    response = client.post(
        f"/api/personas/{persona['id']}/stories/seed",
        headers=auth(token),
    )

    assert response.status_code == 200
    default_stories = [
        story
        for story in response.json()["items"]
        if story["metadata_json"].get("story_kind") == "default_memory_story"
    ]
    assert len(default_stories) == 1
    assert default_stories[0]["metadata_json"]["seed_memory_id"] == active["id"]
    assert default_stories[0]["source_memory_ids"] == [active["id"]]
    excluded_ids = {pending["id"], rejected["id"], disabled["id"], deleted["id"]}
    assert excluded_ids.isdisjoint(default_stories[0]["source_memory_ids"])
    manual_story = next(
        story for story in response.json()["items"] if story["id"] == manual.json()["id"]
    )
    assert manual_story["metadata_json"].get("story_kind") != "default_memory_story"


def test_seed_stories_without_reviewed_memories_returns_empty_list(client):
    token = register_user(client, "story-seed-empty@example.com")
    persona = create_persona(client, token)

    response = client.post(
        f"/api/personas/{persona['id']}/stories/seed",
        headers=auth(token),
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


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


def test_generate_story_prioritizes_important_reviewed_memories(client):
    token = register_user(client, "story-important-memory@example.com")
    persona = create_persona(client, token)
    material = create_manual_material(client, token, persona["id"])
    important = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "important reviewed memory",
        title="important reviewed memory",
    )
    assert client.patch(
        f"/api/memories/{important['id']}",
        headers=auth(token),
        json={"is_important": True},
    ).status_code == 200
    confirm_memory(client, token, important["id"])
    ordinary = create_memory(
        client,
        token,
        persona["id"],
        material["id"],
        "ordinary reviewed memory",
        title="ordinary reviewed memory",
    )
    confirm_memory(client, token, ordinary["id"])

    response = client.post(
        f"/api/personas/{persona['id']}/stories",
        headers=auth(token),
        json={"theme": "priority"},
    )

    assert response.status_code == 201
    story = response.json()
    assert story["source_memory_ids"][0] == important["id"]
    assert story["source_memories"][0]["memory_card_id"] == important["id"]


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
