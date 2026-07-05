from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import Settings
from app.providers.openai_next import OpenAINextTextProvider, OpenAINextTextProviderError


@pytest.mark.asyncio
async def test_openai_next_chat_llm_posts_text_only_chat_completion():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url == "https://api.openai-next.com/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer openai-next-secret"
        body = json.loads(request.content)
        assert body["model"] == "gpt-5"
        assert body["stream"] is False
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][-1]["role"] == "user"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "小铭，我会慢慢陪你说。"}}],
                "id": "openai-next-chat",
            },
        )

    provider = OpenAINextTextProvider(
        Settings(
            app_env="development",
            openai_next_api_key="openai-next-secret",
            openai_next_base_url="https://api.openai-next.com/v1",
            openai_next_model="gpt-5",
        ),
        transport=httpx.MockTransport(handler),
    )

    output = await provider.run(
        "chat_llm",
        {
            "persona_name": "外婆",
            "user_nickname_by_persona": "小铭",
            "user_message": "我有点想你",
            "draft_reply": "小铭，我在。",
            "used_memory_ids": ["mem-1"],
        },
    )

    assert output["reply_text"] == "小铭，我会慢慢陪你说。"
    assert output["used_memory_ids"] == ["mem-1"]
    assert output["trace_id"] == "openai-next-chat"
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_openai_next_memory_document_reuses_strict_json_repair():
    requests: list[dict] = []

    def memory_document_json() -> dict:
        return {
            "sources": [{"id": "src-1", "file_type": "manual", "label": "手动资料"}],
            "modules": {
                "basic_fact": [
                    {
                        "title": "称呼",
                        "content": "外婆会叫用户小铭。",
                        "category": "basic_fact",
                        "confidence_level": "high",
                        "confidence_score": 90,
                        "source_quote": "小铭",
                        "source_location": "manual:body",
                    }
                ],
                "relationship": [],
                "preference": [],
                "habit": [],
                "expression_style": [],
                "shared_event": [],
            },
            "unclassified": [],
            "warnings": [],
        }

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        assert body["model"] == "gpt-5"
        assert body["response_format"] == {"type": "json_object"}
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "not json"}}],
                    "id": "openai-next-memory-doc-invalid",
                },
            )
        assert "JSON validation error" in body["messages"][-1]["content"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "profile_summary": "外婆会叫用户小铭。",
                                    "structured_memory_document_json": memory_document_json(),
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
                "id": "openai-next-memory-doc-repaired",
            },
        )

    provider = OpenAINextTextProvider(
        Settings(
            app_env="development",
            openai_next_api_key="openai-next-secret",
            openai_next_base_url="https://api.openai-next.com/v1",
            openai_next_model="gpt-5",
        ),
        transport=httpx.MockTransport(handler),
    )

    output = await provider.run(
        "memory_document_generation",
        {
            "persona_card": {"name": "外婆"},
            "active_memory_cards": [],
            "parsed_chunks": [],
            "source_metadata": [],
        },
    )

    assert output["profile_summary"] == "外婆会叫用户小铭。"
    assert output["trace_id"] == "openai-next-memory-doc-repaired"
    assert len(requests) == 2


@pytest.mark.asyncio
async def test_openai_next_guided_memory_extraction_posts_text_completion():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content)
        assert body["model"] == "gpt-5"
        assert body["messages"][0]["role"] == "system"
        assert "Extract guided regrets or wishes" in body["messages"][0]["content"]
        context = json.loads(body["messages"][-1]["content"])
        assert context["kind"] == "regrets"
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
                                            "title": "没来得及道别",
                                            "summary": "外婆遗憾没来得及道别。",
                                            "suggested_user_message": "我想慢慢说说没来得及道别这件事。",
                                        }
                                    ],
                                    "empty_reason": None,
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ],
                "id": "openai-next-guided-memory",
            },
        )

    provider = OpenAINextTextProvider(
        Settings(
            app_env="development",
            openai_next_api_key="openai-next-secret",
            openai_next_base_url="https://api.openai-next.com/v1",
            openai_next_model="gpt-5",
        ),
        transport=httpx.MockTransport(handler),
    )

    output = await provider.run(
        "guided_memory_extraction",
        {
            "kind": "regrets",
            "active_memory_cards": [
                {"id": "mem-1", "title": "道别", "content": "外婆遗憾没来得及道别。"}
            ],
        },
    )

    assert output["items"][0]["memory_card_id"] == "mem-1"
    assert output["trace_id"] == "openai-next-guided-memory"
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_openai_next_memory_document_http_failure_does_not_repair():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(500, text="upstream failed")

    provider = OpenAINextTextProvider(
        Settings(
            app_env="development",
            openai_next_api_key="openai-next-secret",
            openai_next_base_url="https://api.openai-next.com/v1",
            openai_next_model="gpt-5",
        ),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(OpenAINextTextProviderError, match="HTTP 500"):
        await provider.run(
            "memory_document_generation",
            {
                "persona_card": {"name": "test persona"},
                "active_memory_cards": [],
                "parsed_chunks": [],
                "source_metadata": [],
            },
        )

    assert len(requests) == 1


@pytest.mark.asyncio
async def test_openai_next_rejects_non_text_capabilities():
    provider = OpenAINextTextProvider(
        Settings(
            app_env="development",
            openai_next_api_key="openai-next-secret",
            openai_next_base_url="https://api.openai-next.com/v1",
            openai_next_model="gpt-5",
        )
    )

    with pytest.raises(OpenAINextTextProviderError, match="does not support capability: tts"):
        await provider.run("tts", {"text": "hello"})
    with pytest.raises(OpenAINextTextProviderError, match="does not support capability: voice_clone"):
        await provider.run("voice_clone", {"storage_url": "sample.wav"})
