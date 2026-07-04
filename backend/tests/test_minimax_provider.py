from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import Settings
from app.providers.minimax import MiniMaxProvider


@pytest.mark.asyncio
async def test_minimax_tts_posts_sync_speech_request_and_returns_audio_url():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url == "https://api.minimaxi.com/v1/t2a_v2"
        assert request.headers["authorization"] == "Bearer minimax-secret"
        body = json.loads(request.content)
        assert body["model"] == "speech-2.8-hd"
        assert body["text"] == "小铭，慢慢来。"
        assert body["stream"] is False
        assert body["voice_setting"]["voice_id"] == "male-qn-qingse"
        assert body["audio_setting"]["format"] == "mp3"
        assert body["output_format"] == "url"
        return httpx.Response(
            200,
            json={
                "data": {
                    "audio": "https://api.minimaxi.com/audio/preview.mp3",
                    "status": 2,
                },
                "extra_info": {"audio_length": 1200},
                "trace_id": "trace-1",
                "base_resp": {"status_code": 0, "status_msg": "success"},
            },
        )

    provider = MiniMaxProvider(
        Settings(
            app_env="development",
            minimax_api_key="minimax-secret",
            minimax_base_url="https://api.minimaxi.com/v1",
            minimax_tts_model="speech-2.8-hd",
            minimax_default_voice_id="male-qn-qingse",
        ),
        transport=httpx.MockTransport(handler),
    )

    output = await provider.run("tts", {"text": "小铭，慢慢来。"})

    assert output["audio_url"] == "https://api.minimaxi.com/audio/preview.mp3"
    assert output["duration_ms"] == 1200
    assert output["trace_id"] == "trace-1"
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_minimax_voice_clone_uploads_audio_and_returns_voice_id(tmp_path):
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"fake-wav-bytes")
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        assert request.headers["authorization"] == "Bearer minimax-secret"
        if request.url.path == "/v1/files/upload":
            assert b'name="purpose"' in request.content
            assert b"voice_clone" in request.content
            assert b'name="file"' in request.content
            return httpx.Response(
                200,
                json={
                    "file": {"file_id": 123456789},
                    "base_resp": {"status_code": 0, "status_msg": "success"},
                },
            )
        if request.url.path == "/v1/voice_clone":
            body = json.loads(request.content)
            assert body["file_id"] == 123456789
            assert body["voice_id"] == "PMVabcdef12"
            assert body["model"] == "speech-2.8-hd"
            assert body["text"] == "你好，这是一段音色复刻试听。"
            return httpx.Response(
                200,
                json={
                    "demo_audio": "https://api.minimaxi.com/audio/clone.mp3",
                    "extra_info": {"audio_length": 1100},
                    "base_resp": {"status_code": 0, "status_msg": "success"},
                },
            )
        raise AssertionError(f"unexpected path: {request.url.path}")

    provider = MiniMaxProvider(
        Settings(
            app_env="development",
            minimax_api_key="minimax-secret",
            minimax_base_url="https://api.minimaxi.com/v1",
            minimax_clone_model="speech-2.8-hd",
        ),
        transport=httpx.MockTransport(handler),
    )

    output = await provider.run(
        "voice_clone",
        {
            "voice_model_id": "abcdef12-3456-7890-abcd-ef1234567890",
            "storage_url": audio_path.as_posix(),
            "sample_text": "你好，这是一段音色复刻试听。",
        },
    )

    assert output["clone_status"] == "succeeded"
    assert output["model_artifact_url"] == "minimax://voice/PMVabcdef12"
    assert output["preview_audio_url"] == "https://api.minimaxi.com/audio/clone.mp3"
    assert output["quality_score"] == 82
    assert seen_paths == ["/v1/files/upload", "/v1/voice_clone"]


@pytest.mark.asyncio
async def test_minimax_chat_llm_uses_openai_compatible_chat_completion():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url == "https://api.minimaxi.com/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer minimax-secret"
        body = json.loads(request.content)
        assert body["model"] == "MiniMax-M3"
        assert body["stream"] is False
        assert body["messages"][0]["role"] == "system"
        assert "Grandma" in body["messages"][0]["content"]
        assert body["messages"][-1]["role"] == "user"
        assert "What did you like cooking?" in body["messages"][-1]["content"]
        context = json.loads(body["messages"][-1]["content"])
        assert "Grandma liked making wontons." in context["long_term_memory_md"]
        assert "I am here with you." in context["short_term_memory_md"]
        assert context["selected_memory_ids"] == ["mem-1"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "Child, I remember making wontons with you."
                        }
                    }
                ],
                "id": "chatcmpl-test",
            },
        )

    provider = MiniMaxProvider(
        Settings(
            app_env="development",
            minimax_api_key="minimax-secret",
            minimax_base_url="https://api.minimaxi.com/v1",
            openai_compatible_model="MiniMax-M3",
        ),
        transport=httpx.MockTransport(handler),
    )

    output = await provider.run(
        "chat_llm",
        {
            "persona_name": "Grandma",
            "relationship_to_user": "grandmother",
            "user_nickname_by_persona": "Child",
            "speaking_style": "warm",
            "emotional_style": "comforting",
            "long_term_memory_md": "- memory_card_id: mem-1\n  content: Grandma liked making wontons.",
            "short_term_memory_md": "## 最近消息\n- TA: I am here with you.",
            "selected_memory_ids": ["mem-1"],
            "conversation_history": [
                {"role": "user", "content": "Hi"},
                {"role": "persona", "content": "I am here with you."},
            ],
            "user_message": "What did you like cooking?",
            "draft_reply": "Child, I remember making wontons.",
            "used_memory_ids": ["mem-1"],
        },
    )

    assert output["reply_text"] == "Child, I remember making wontons with you."
    assert output["used_memory_ids"] == ["mem-1"]
    assert output["trace_id"] == "chatcmpl-test"
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_minimax_memory_context_compression_uses_openai_compatible_chat_completion():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url == "https://api.minimaxi.com/v1/chat/completions"
        body = json.loads(request.content)
        assert body["model"] == "MiniMax-M3"
        assert body["messages"][0]["role"] == "system"
        assert "Compress persona memory Markdown" in body["messages"][0]["content"]
        context = json.loads(body["messages"][-1]["content"])
        assert context["memory_card_ids"] == ["mem-1"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "long_term_memory_md": "- memory_card_id: mem-1\n  content: wontons",
                                    "short_term_memory_md": "## 最近消息\n- 用户: hello",
                                    "selected_memory_ids": ["mem-1"],
                                }
                            )
                        }
                    }
                ],
                "id": "chatcmpl-compress",
            },
        )

    provider = MiniMaxProvider(
        Settings(
            app_env="development",
            minimax_api_key="minimax-secret",
            minimax_base_url="https://api.minimaxi.com/v1",
            openai_compatible_model="MiniMax-M3",
        ),
        transport=httpx.MockTransport(handler),
    )

    output = await provider.run(
        "memory_context_compression",
        {
            "user_message": "hello",
            "long_term_memory_md": "- memory_card_id: mem-1\n  content: Grandma liked making wontons.",
            "short_term_memory_md": "## 最近消息\n- TA: I am here with you.",
            "memory_card_ids": ["mem-1"],
        },
    )

    assert output["long_term_memory_md"].startswith("- memory_card_id: mem-1")
    assert output["short_term_memory_md"].startswith("## 最近消息")
    assert output["selected_memory_ids"] == ["mem-1"]
    assert output["trace_id"] == "chatcmpl-compress"
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_minimax_persona_profile_analysis_uses_persona_engine_prompt():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url == "https://api.minimaxi.com/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer minimax-secret"
        body = json.loads(request.content)
        assert body["model"] == "MiniMax-M3"
        assert body["stream"] is False
        assert body["messages"][0]["role"] == "system"
        assert "人格建模分析师" in body["messages"][0]["content"]
        assert body["messages"][-1]["role"] == "user"
        context = json.loads(body["messages"][-1]["content"])
        assert context["persona_card"]["name"] == "Grandma"
        assert context["active_memory_cards"][0]["id"] == "mem-1"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "persona_version": "persona_engine_v2_minimax",
                                    "basic_info": {"name": "Grandma"},
                                    "speech_style": {"summary": "warm", "evidence": ["mem-1"]},
                                    "interests": [],
                                    "habits": [],
                                    "emotional_style": {},
                                    "relationships": [],
                                    "worldview": {},
                                    "decision_style": {},
                                    "taboos": [],
                                    "overall_confidence": 0.82,
                                    "low_confidence_fields": [],
                                    "pending_verification": [],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ],
                "id": "chatcmpl-persona-engine",
            },
        )

    provider = MiniMaxProvider(
        Settings(
            app_env="development",
            minimax_api_key="minimax-secret",
            minimax_base_url="https://api.minimaxi.com/v1",
            openai_compatible_model="MiniMax-M3",
        ),
        transport=httpx.MockTransport(handler),
    )

    output = await provider.run(
        "persona_profile_analysis",
        {
            "persona_card": {"name": "Grandma"},
            "active_memory_cards": [{"id": "mem-1", "content": "Grandma spoke warmly."}],
            "parsed_chunks": [],
            "source_metadata": [],
        },
    )

    assert output["persona_version"] == "persona_engine_v2_minimax"
    assert output["trace_id"] == "chatcmpl-persona-engine"
    assert output["speech_style"]["summary"] == "warm"
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_minimax_story_generation_uses_openai_compatible_chat_completion():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url == "https://api.minimaxi.com/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer minimax-secret"
        body = json.loads(request.content)
        assert body["model"] == "MiniMax-M3"
        assert "birthday" in body["messages"][-1]["content"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "title": "Birthday wontons",
                                    "content": "Child, I remember that birthday meal.",
                                    "source_memory_ids": ["mem-1"],
                                    "source_memories": [
                                        {
                                            "memory_card_id": "mem-1",
                                            "title": "Wontons",
                                            "quote": "birthday wontons",
                                            "source_location": "manual:1",
                                        }
                                    ],
                                }
                            )
                        }
                    }
                ],
                "id": "chatcmpl-story",
            },
        )

    provider = MiniMaxProvider(
        Settings(
            app_env="development",
            minimax_api_key="minimax-secret",
            minimax_base_url="https://api.minimaxi.com/v1",
            openai_compatible_model="MiniMax-M3",
        ),
        transport=httpx.MockTransport(handler),
    )

    output = await provider.run(
        "story_generation",
        {
            "persona_name": "Grandma",
            "user_nickname_by_persona": "Child",
            "story_theme": "birthday",
            "retrieved_memories": [
                {
                    "id": "mem-1",
                    "title": "Wontons",
                    "content": "Grandma made birthday wontons.",
                    "quote": "birthday wontons",
                    "source_location": "manual:1",
                }
            ],
        },
    )

    assert output["title"] == "Birthday wontons"
    assert output["content"] == "Child, I remember that birthday meal."
    assert output["source_memory_ids"] == ["mem-1"]
    assert output["source_memories"][0]["memory_card_id"] == "mem-1"
    assert output["trace_id"] == "chatcmpl-story"
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_minimax_story_generation_falls_back_when_model_returns_plain_text():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "Child, I remember making birthday wontons for you."
                        }
                    }
                ],
                "id": "chatcmpl-story-plain",
            },
        )

    provider = MiniMaxProvider(
        Settings(
            app_env="development",
            minimax_api_key="minimax-secret",
            minimax_base_url="https://api.minimaxi.com/v1",
            openai_compatible_model="MiniMax-M3",
        ),
        transport=httpx.MockTransport(handler),
    )

    output = await provider.run(
        "story_generation",
        {
            "persona_name": "Grandma",
            "user_nickname_by_persona": "Child",
            "story_theme": "birthday",
            "retrieved_memories": [
                {
                    "id": "mem-1",
                    "title": "Wontons",
                    "content": "Grandma made birthday wontons.",
                    "quote": "birthday wontons",
                    "source_location": "manual:1",
                }
            ],
        },
    )

    assert output["title"] == "birthday"
    assert output["content"] == "Child, I remember making birthday wontons for you."
    assert output["source_memory_ids"] == ["mem-1"]
    assert output["source_memories"][0]["memory_card_id"] == "mem-1"
    assert output["trace_id"] == "chatcmpl-story-plain"
