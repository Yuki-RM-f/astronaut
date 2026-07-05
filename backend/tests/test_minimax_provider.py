from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import Settings
from app.providers.minimax import MiniMaxProvider, MiniMaxProviderError


def _valid_memory_document_md() -> str:
    return (
        "## 资料来源\n"
        "- manual\n\n"
        "## 基础信息\n"
        "- 外婆享年 72 岁。\n\n"
        "## 人物关系\n"
        "- 外婆会叫用户小铭。\n\n"
        "## 兴趣偏好\n"
        "- 外婆喜欢包馄饨。\n\n"
        "## 生活习惯\n"
        "- 无\n\n"
        "## 表达习惯\n"
        "- 无\n\n"
        "## 共同经历\n"
        "- 无\n\n"
        "## 待用户确认\n"
        "- 继续补充资料。"
    )


def _valid_memory_document_json() -> dict:
    return {
        "sources": [
            {
                "id": "material-1",
                "file_type": "manual",
                "label": "手动资料",
            }
        ],
        "modules": {
            "basic_fact": [
                {
                    "title": "享年",
                    "content": "外婆享年 72 岁。",
                    "category": "basic_fact",
                    "confidence_level": "high",
                    "confidence_score": 90,
                    "source_quote": "享年 72 岁",
                    "source_location": "manual:body",
                }
            ],
            "relationship": [
                {
                    "title": "称呼",
                    "content": "外婆会叫用户小铭。",
                    "category": "relationship",
                    "confidence_level": "high",
                    "confidence_score": 88,
                    "source_quote": "小铭",
                    "source_location": "manual:body",
                }
            ],
            "preference": [],
            "habit": [],
            "expression_style": [],
            "shared_event": [],
        },
        "unclassified": [],
        "warnings": [],
    }


def _memory_document_payload() -> dict:
    return {
        "persona_card": {
            "id": "persona-1",
            "name": "外婆",
            "relationship_to_user": "外婆",
            "user_nickname_by_persona": "小铭",
        },
        "parsed_chunks": [
            {
                "id": "chunk-1",
                "content": "外婆喜欢包馄饨，会叫我小铭。",
                "source_location": "manual:body",
            }
        ],
        "active_memory_cards": [
            {
                "id": "mem-1",
                "title": "称呼",
                "content": "外婆会叫用户小铭。",
                "category": "relationship",
                "source_quote": "小铭",
                "source_location": "manual:body",
            }
        ],
        "source_metadata": [{"id": "material-1", "file_type": "manual"}],
        "current_profile": {},
    }


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
async def test_minimax_tts_uses_system_voice_artifact_when_voice_id_is_absent():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["voice_setting"]["voice_id"] == "Chinese (Mandarin)_Gentle_Senior"
        return httpx.Response(
            200,
            json={
                "data": {
                    "audio": "https://api.minimaxi.com/audio/gentle-senior.mp3",
                    "status": 2,
                },
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

    output = await provider.run(
        "tts",
        {
            "text": "小铭，慢慢来。",
            "model_artifact_url": (
                "minimax://system-voice/"
                "Chinese%20%28Mandarin%29_Gentle_Senior"
            ),
        },
    )

    assert output["audio_url"] == "https://api.minimaxi.com/audio/gentle-senior.mp3"


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
async def test_minimax_chat_llm_includes_regrets_guided_prompt_in_system_message():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content)
        system_message = body["messages"][0]["content"]
        assert "Grandma" in system_message
        assert "有没有什么以前没说的话" in system_message
        assert "道歉、感谢、想念、告别或心结" in system_message
        context = json.loads(body["messages"][-1]["content"])
        assert context["conversation_kind"] == "regrets"
        assert "有没有什么以前没说的话" in context["guided_system_prompt"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "Child, we can take the unsaid words slowly."
                        }
                    }
                ],
                "id": "chatcmpl-regrets",
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
            "conversation_kind": "regrets",
            "guided_system_prompt": (
                "这里是遗憾对话室。请围绕“有没有什么以前没说的话，今天想慢慢告诉我？”"
                "引导用户表达道歉、感谢、想念、告别或心结。"
            ),
            "long_term_memory_md": "",
            "short_term_memory_md": "",
            "selected_memory_ids": [],
            "conversation_history": [],
            "user_message": "Hi",
            "draft_reply": "Child, we can take the unsaid words slowly.",
            "used_memory_ids": [],
        },
    )

    assert output["reply_text"] == "Child, we can take the unsaid words slowly."
    assert output["trace_id"] == "chatcmpl-regrets"
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_minimax_chat_llm_includes_wishes_guided_prompt_in_system_message():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content)
        system_message = body["messages"][0]["content"]
        assert "Grandma" in system_message
        assert "你现在有什么想完成的心愿，或者想替我继续做的一件事吗？" in system_message
        assert "只围绕心愿、替我继续做的一件事、下一步行动" in system_message
        assert "不要把其他普通聊天、遗憾对话或无关上下文带入本轮" in system_message
        context = json.loads(body["messages"][-1]["content"])
        assert context["context_kind"] == "wishes"
        assert context["conversation_kind"] == "wishes"
        assert context["long_term_memory_md"] == ""
        assert context["short_term_memory_md"] == ""
        assert context["selected_memory_ids"] == []
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "Child, I hear this wish. Let's choose one small step for today."
                        }
                    }
                ],
                "id": "chatcmpl-wishes",
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
            "context_kind": "wishes",
            "conversation_kind": "wishes",
            "system_prompt_kind": "wishes",
            "guided_system_prompt": (
                "你现在有什么想完成的心愿，或者想替我继续做的一件事吗？"
                "只围绕心愿、替我继续做的一件事、下一步行动展开。"
                "不要把其他普通聊天、遗憾对话或无关上下文带入本轮。"
            ),
            "long_term_memory_md": "",
            "short_term_memory_md": "",
            "selected_memory_ids": [],
            "conversation_history": [],
            "user_message": "I want to replant your garden.",
            "draft_reply": "Child, I hear this wish.",
            "used_memory_ids": [],
        },
    )

    assert output["reply_text"] == "Child, I hear this wish. Let's choose one small step for today."
    assert output["used_memory_ids"] == []
    assert output["trace_id"] == "chatcmpl-wishes"
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
async def test_minimax_guided_memory_extraction_uses_openai_compatible_chat_completion():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content)
        assert body["model"] == "MiniMax-M3"
        assert body["messages"][0]["role"] == "system"
        assert "Extract guided regrets or wishes" in body["messages"][0]["content"]
        context = json.loads(body["messages"][-1]["content"])
        assert context["kind"] == "wishes"
        assert context["active_memory_cards"][0]["id"] == "mem-1"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "items": [
                                        {
                                            "memory_card_id": "mem-1",
                                            "title": "继续花园",
                                            "summary": "外婆希望小铭继续照顾花园。",
                                            "suggested_user_message": "我想继续照顾花园。",
                                        }
                                    ],
                                    "empty_reason": None,
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ],
                "id": "chatcmpl-guided-memory",
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
        "guided_memory_extraction",
        {
            "kind": "wishes",
            "active_memory_cards": [
                {"id": "mem-1", "title": "花园", "content": "外婆希望小铭继续照顾花园。"}
            ],
        },
    )

    assert output["items"][0]["memory_card_id"] == "mem-1"
    assert output["trace_id"] == "chatcmpl-guided-memory"
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
async def test_minimax_memory_document_generation_repairs_invalid_json_response():
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        assert body["model"] == "MiniMax-M3"
        assert body["messages"][0]["role"] == "system"
        assert "ONLY return one strict JSON object" in body["messages"][0]["content"]
        assert "profile_summary" in body["messages"][0]["content"]
        assert "Do not output Markdown" in body["messages"][0]["content"]
        assert "structured_memory_document_json" in body["messages"][0]["content"]
        assert body["response_format"] == {"type": "json_object"}
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "这是一段说明，不是 JSON"}}],
                    "id": "chatcmpl-memory-doc-invalid",
                },
            )
        assert "JSON validation error" in body["messages"][-1]["content"]
        assert "这是一段说明，不是 JSON" in body["messages"][-1]["content"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "profile_summary": "外婆喜欢包馄饨，会叫用户小铭。",
                                    "trust_score": 72,
                                    "trust_level": "trusted",
                                    "trust_rationale": "来自带来源的记忆卡片。",
                                    "suggestions": ["继续上传照片和语音资料"],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ],
                "id": "chatcmpl-memory-doc-repaired",
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

    output = await provider.run("memory_document_generation", _memory_document_payload())

    assert output["profile_summary"] == "外婆喜欢包馄饨，会叫用户小铭。"
    assert output["trust_score"] == 72
    assert output["trust_level"] == "trusted"
    assert output["trace_id"] == "chatcmpl-memory-doc-repaired"
    assert len(requests) == 2


@pytest.mark.asyncio
async def test_minimax_memory_document_generation_repairs_missing_required_field():
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        content = {
            "trust_score": 72,
            "trust_level": "trusted",
            "trust_rationale": "来自带来源的记忆卡片。",
            "suggestions": ["继续上传照片和语音资料"],
        }
        if len(requests) == 2:
            content["profile_summary"] = "外婆喜欢包馄饨。"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}],
                "id": f"chatcmpl-memory-doc-{len(requests)}",
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

    output = await provider.run("memory_document_generation", _memory_document_payload())

    assert output["profile_summary"] == "外婆喜欢包馄饨。"
    assert output["trace_id"] == "chatcmpl-memory-doc-2"
    assert "missing field: profile_summary" in requests[1]["messages"][-1]["content"]
    assert len(requests) == 2


@pytest.mark.asyncio
async def test_minimax_memory_document_generation_accepts_wrapped_json_object():
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        output = {
            "profile_summary": "外婆会叫用户小铭。",
            "trust_score": 68,
            "trust_level": "trusted",
            "trust_rationale": "来自结构化记忆卡片。",
            "suggestions": ["继续上传照片和语音资料"],
        }
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                "<think>先检查字段</think>\n"
                                "```json\n"
                                f"{json.dumps(output, ensure_ascii=False)}\n"
                                "```\n以上为结构化结果。"
                            )
                        }
                    }
                ],
                "id": "chatcmpl-memory-doc-wrapped",
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

    output = await provider.run("memory_document_generation", _memory_document_payload())

    assert output["profile_summary"] == "外婆会叫用户小铭。"
    assert output["trust_score"] == 68
    assert output["trace_id"] == "chatcmpl-memory-doc-wrapped"
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_minimax_memory_document_generation_fails_after_three_repair_attempts():
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "not json"}}],
                "id": f"chatcmpl-memory-doc-bad-{len(requests)}",
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

    with pytest.raises(MiniMaxProviderError, match="after 3 repair attempts"):
        await provider.run("memory_document_generation", _memory_document_payload())

    assert len(requests) == 4


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
async def test_minimax_story_generation_strips_thinking_before_json_parse():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                "<think>I should reason privately.</think>\n"
                                + json.dumps(
                                    {
                                        "title": "生日馄饨",
                                        "content": "小铭，我还记得那天给你包馄饨。",
                                        "source_memory_ids": ["mem-1"],
                                        "source_memories": [
                                            {
                                                "memory_card_id": "mem-1",
                                                "title": "馄饨",
                                                "quote": "生日馄饨",
                                                "source_location": "manual:1",
                                            }
                                        ],
                                    },
                                    ensure_ascii=False,
                                )
                            )
                        }
                    }
                ],
                "id": "chatcmpl-story-think-json",
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
            "persona_name": "外婆",
            "user_nickname_by_persona": "小铭",
            "story_theme": "生日",
            "retrieved_memories": [
                {
                    "id": "mem-1",
                    "title": "馄饨",
                    "content": "外婆给小铭包馄饨。",
                    "quote": "生日馄饨",
                    "source_location": "manual:1",
                }
            ],
        },
    )

    assert output["title"] == "生日馄饨"
    assert output["content"] == "小铭，我还记得那天给你包馄饨。"
    assert "<think>" not in output["content"]
    assert output["source_memory_ids"] == ["mem-1"]


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


@pytest.mark.asyncio
async def test_minimax_story_generation_plain_text_strips_unclosed_thinking():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "<think>The user wants a warm story from memories."
                        }
                    }
                ],
                "id": "chatcmpl-story-unclosed-think",
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
            "persona_name": "外婆",
            "user_nickname_by_persona": "小铭",
            "story_theme": "生日",
            "retrieved_memories": [
                {
                    "id": "mem-1",
                    "title": "热汤",
                    "content": "外婆给小铭煮热汤。",
                    "quote": "生日热汤",
                    "source_location": "manual:1",
                }
            ],
        },
    )

    assert "<think>" not in output["content"]
    assert "The user wants" not in output["content"]
    assert "热汤" in output["content"]
    assert output["source_memory_ids"] == ["mem-1"]
    assert output["trace_id"] == "chatcmpl-story-unclosed-think"
