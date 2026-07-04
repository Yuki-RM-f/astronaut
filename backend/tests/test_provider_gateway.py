import pytest

from app.core.config import Settings
from app.providers.dashscope import _normalize_memory_candidates
from app.providers.gateway import ProviderGateway


@pytest.mark.asyncio
async def test_mock_gateway_returns_capability_result():
    result = await ProviderGateway().run("chat_llm", {"message": "你好"})

    assert result["provider_name"] == "mock"
    assert result["capability"] == "chat_llm"
    assert result["status"] == "succeeded"
    assert result["input"]["message"] == "你好"
    assert result["output"]["reply_text"]


class FakeDashScopeProvider:
    is_configured = True

    def __init__(self):
        self.calls = []

    async def run(self, capability, payload):
        self.calls.append((capability, payload))
        if capability == "memory_extraction":
            return {
                "memories": [
                    {
                        "title": "真实记忆",
                        "content": "外婆喜欢在厨房教我包馄饨。",
                        "category": "shared_event",
                        "confidence_level": "high",
                        "confidence_score": 88,
                        "source_quote": "教我包馄饨",
                        "source_location": payload["source_location"],
                    }
                ]
            }
        return {"message": "dashscope result"}


@pytest.mark.asyncio
async def test_dashscope_gateway_routes_real_parsing_capabilities():
    dashscope = FakeDashScopeProvider()
    settings = Settings(default_llm_provider="dashscope", dashscope_api_key="sk-test")
    result = await ProviderGateway(settings=settings, dashscope_client=dashscope).run(
        "memory_extraction",
        {
            "content": "外婆喜欢在厨房教我包馄饨。",
            "source_location": "text:note.txt#page=1",
        },
    )

    assert result["provider_name"] == "dashscope"
    assert result["provider_type"] == "third_party"
    assert result["status"] == "succeeded"
    assert dashscope.calls[0][0] == "memory_extraction"
    assert result["output"]["memories"][0]["title"] == "真实记忆"


@pytest.mark.asyncio
async def test_dashscope_gateway_falls_back_to_mock_when_api_key_missing():
    settings = Settings(default_llm_provider="dashscope", dashscope_api_key="")

    result = await ProviderGateway(settings=settings).run(
        "ocr",
        {"file_name": "birthday.jpg", "user_description": "生日照片"},
    )

    assert result["provider_name"] == "mock"
    assert result["provider_type"] == "local"
    assert result["output"]["ocr_text"]


class FakeMiniMaxProvider:
    provider_name = "minimax"
    provider_type = "third_party"
    is_configured = True

    def __init__(self):
        self.calls = []

    async def run(self, capability, payload):
        self.calls.append((capability, payload))
        if capability == "tts":
            return {
                "audio_url": "https://api.minimaxi.com/audio/preview.mp3",
                "duration_ms": 1200,
                "voice_status": payload["voice_status"],
                "voice_model_id": payload["voice_model_id"],
            }
        if capability == "memory_context_compression":
            return {
                "long_term_memory_md": payload.get("long_term_memory_md", ""),
                "short_term_memory_md": payload.get("short_term_memory_md", ""),
                "selected_memory_ids": ["mem-1"],
            }
        if capability == "persona_profile_analysis":
            return {
                "persona_version": "persona_engine_v2_test",
                "overall_confidence": 0.74,
                "basic_info": {"name": payload.get("persona_card", {}).get("name")},
                "low_confidence_fields": [],
                "pending_verification": [],
            }
        if capability == "memory_document_generation":
            return {
                "profile_summary": "Grandma is warm and grounded in reviewed memories.",
                "trust_score": 72,
                "trust_level": "trusted",
                "trust_rationale": "third-party memory document generation",
                "suggestions": ["add more materials"],
            }
        return {
            "clone_status": "succeeded",
            "model_artifact_url": "minimax://voice/PMV12345678",
            "preview_audio_url": "https://api.minimaxi.com/audio/clone.mp3",
            "quality_score": 82,
        }


class FailingMiniMaxProvider(FakeMiniMaxProvider):
    def __init__(self, error: str = "MiniMax upstream failed"):
        super().__init__()
        self.error = error

    async def run(self, capability, payload):
        self.calls.append((capability, payload))
        raise RuntimeError(self.error)


class FakeOpenAINextTextProvider:
    provider_name = "openai_next"
    provider_type = "third_party"
    is_configured = True

    def __init__(self):
        self.calls = []

    async def run(self, capability, payload):
        self.calls.append((capability, payload))
        if capability == "chat_llm":
            return {
                "reply_text": "openai-next chat reply",
                "used_memory_ids": payload.get("used_memory_ids") or [],
            }
        if capability == "story_generation":
            return {
                "title": "openai-next story",
                "content": "小铭，我记得这段回忆。",
                "source_memory_ids": [],
                "source_memories": [],
            }
        if capability == "memory_context_compression":
            return {
                "long_term_memory_md": payload.get("long_term_memory_md", ""),
                "short_term_memory_md": payload.get("short_term_memory_md", ""),
                "selected_memory_ids": ["fallback-mem-1"],
            }
        if capability == "persona_profile_analysis":
            return {
                "persona_version": "persona_engine_v2_openai_next",
                "overall_confidence": 0.71,
                "basic_info": {"name": payload.get("persona_card", {}).get("name")},
                "low_confidence_fields": [],
                "pending_verification": [],
            }
        if capability == "memory_document_generation":
            return {
                "profile_summary": "Grandma is warm.",
                "trust_score": 72,
                "trust_level": "trusted",
                "trust_rationale": "openai-next fallback",
                "suggestions": ["add more materials"],
            }
        raise AssertionError(f"unexpected capability: {capability}")


@pytest.mark.asyncio
async def test_minimax_gateway_routes_voice_capabilities_when_configured():
    minimax = FakeMiniMaxProvider()
    settings = Settings(
        app_env="development",
        minimax_api_key="sk-test",
        minimax_base_url="https://api.minimaxi.com/v1",
    )

    tts = await ProviderGateway(settings=settings, minimax_client=minimax).run(
        "tts",
        {
            "text": "小铭，慢慢来。",
            "voice_status": "default_tts",
            "voice_model_id": "voice-1",
        },
    )
    clone = await ProviderGateway(settings=settings, minimax_client=minimax).run(
        "voice_clone",
        {
            "voice_model_id": "voice-1",
            "storage_url": "storage/materials/sample.wav",
        },
    )

    assert tts["provider_name"] == "minimax"
    assert tts["provider_type"] == "third_party"
    assert tts["output"]["audio_url"].startswith("https://")
    assert clone["provider_name"] == "minimax"
    assert clone["output"]["model_artifact_url"] == "minimax://voice/PMV12345678"
    assert [call[0] for call in minimax.calls] == ["tts", "voice_clone"]


@pytest.mark.asyncio
async def test_minimax_gateway_routes_text_llm_capabilities_when_configured():
    minimax = FakeMiniMaxProvider()
    settings = Settings(
        app_env="development",
        minimax_api_key="sk-test",
        minimax_base_url="https://api.minimaxi.com/v1",
        openai_compatible_model="MiniMax-M3",
    )

    chat = await ProviderGateway(settings=settings, minimax_client=minimax).run(
        "chat_llm",
        {
            "persona_name": "Grandma",
            "user_message": "hello",
            "draft_reply": "hello from draft",
            "used_memory_ids": ["mem-1"],
        },
    )
    story = await ProviderGateway(settings=settings, minimax_client=minimax).run(
        "story_generation",
        {
            "persona_name": "Grandma",
            "story_theme": "birthday",
            "retrieved_memories": [],
        },
    )
    compression = await ProviderGateway(settings=settings, minimax_client=minimax).run(
        "memory_context_compression",
        {
            "user_message": "hello",
            "long_term_memory_md": "- memory_card_id: mem-1",
            "short_term_memory_md": "## 最近消息",
            "memory_card_ids": ["mem-1"],
        },
    )
    memory_document = await ProviderGateway(settings=settings, minimax_client=minimax).run(
        "memory_document_generation",
        {
            "persona_card": {"name": "Grandma"},
            "active_memory_cards": [{"id": "mem-1", "content": "warm"}],
            "source_metadata": [{"id": "src-1", "file_type": "manual"}],
        },
    )

    assert chat["provider_name"] == "minimax"
    assert chat["provider_type"] == "third_party"
    assert chat["capability"] == "chat_llm"
    assert story["provider_name"] == "minimax"
    assert story["capability"] == "story_generation"
    assert compression["provider_name"] == "minimax"
    assert compression["capability"] == "memory_context_compression"
    assert compression["output"]["selected_memory_ids"] == ["mem-1"]
    assert memory_document["provider_name"] == "minimax"
    assert memory_document["capability"] == "memory_document_generation"
    assert memory_document["output"]["profile_summary"]
    assert [call[0] for call in minimax.calls] == [
        "chat_llm",
        "story_generation",
        "memory_context_compression",
        "memory_document_generation",
    ]


@pytest.mark.asyncio
async def test_mock_gateway_returns_persona_profile_analysis():
    result = await ProviderGateway().run(
        "persona_profile_analysis",
        {
            "persona_card": {"name": "外婆", "relationship_to_user": "外婆"},
            "active_memory_cards": [
                {
                    "id": "mem-1",
                    "title": "慢慢来",
                    "content": "外婆总说慢慢来。",
                    "category": "expression_style",
                    "source_quote": "慢慢来",
                }
            ],
            "parsed_chunks": [{"content": "外婆总说慢慢来。"}],
            "source_metadata": [{"id": "src-1", "file_type": "manual"}],
        },
    )

    assert result["provider_name"] == "mock"
    assert result["capability"] == "persona_profile_analysis"
    assert result["output"]["persona_version"] == "persona_engine_v2_mock"
    assert result["output"]["overall_confidence"] >= 0
    assert result["output"]["speech_style"]["evidence"]


@pytest.mark.asyncio
async def test_mock_gateway_returns_memory_summary_and_trust_metadata():
    result = await ProviderGateway().run(
        "memory_document_generation",
        {
            "persona_card": {"name": "外婆"},
            "source_metadata": [{"id": "src-1", "file_type": "manual", "file_name": None}],
            "active_memory_cards": [
                {
                    "id": "mem-1",
                    "title": "馄饨",
                    "content": "外婆喜欢包馄饨。",
                    "category": "preference",
                    "status": "pending_review",
                    "source_quote": "喜欢包馄饨",
                    "source_location": "manual:body#1",
                },
                {
                    "id": "mem-2",
                    "title": "慢慢来",
                    "content": "外婆常说慢慢来。",
                    "category": "expression_style",
                    "status": "confirmed",
                    "source_quote": "慢慢来",
                    "source_location": "manual:body#2",
                },
            ],
        },
    )

    output = result["output"]
    assert result["provider_name"] == "mock"
    assert result["capability"] == "memory_document_generation"
    assert 0 <= output["trust_score"] <= 100
    assert output["trust_level"] in {"initial", "usable", "trusted", "high_trust"}
    assert output["trust_rationale"]
    assert output["suggestions"]
    assert output["profile_summary"]
    assert "structured_memory_document_json" not in output
    assert "structured_memory_md" not in output


@pytest.mark.asyncio
async def test_mock_memory_extraction_returns_strict_module_json():
    result = await ProviderGateway().run(
        "memory_extraction",
        {
            "source_material_id": "src-1",
            "source_type": "manual",
            "content": "外婆喜欢包馄饨。她常说慢慢来。",
            "source_location": "manual:body",
            "persona_card": {"name": "外婆", "relationship_to_user": "外婆"},
            "source_material": {"id": "src-1", "file_type": "manual"},
        },
    )

    output = result["output"]
    structured = output["structured_memory_json"]
    assert result["capability"] == "memory_extraction"
    assert structured["source_material_id"] == "src-1"
    assert set(structured["modules"]) == {
        "basic_fact",
        "relationship",
        "preference",
        "habit",
        "expression_style",
        "shared_event",
    }
    assert output["memories"]
    assert all(memory["category"] in structured["modules"] for memory in output["memories"])
    assert all(memory["source_quote"] for memory in output["memories"])


@pytest.mark.asyncio
async def test_minimax_gateway_routes_persona_profile_analysis_when_configured():
    minimax = FakeMiniMaxProvider()
    settings = Settings(
        app_env="development",
        minimax_api_key="sk-test",
        minimax_base_url="https://api.minimaxi.com/v1",
        openai_compatible_model="MiniMax-M3",
    )

    result = await ProviderGateway(settings=settings, minimax_client=minimax).run(
        "persona_profile_analysis",
        {
            "persona_card": {"name": "Grandma"},
            "active_memory_cards": [{"id": "mem-1", "content": "warm"}],
        },
    )

    assert result["provider_name"] == "minimax"
    assert result["capability"] == "persona_profile_analysis"
    assert result["output"]["persona_version"] == "persona_engine_v2_test"
    assert minimax.calls[-1][0] == "persona_profile_analysis"


@pytest.mark.asyncio
async def test_minimax_text_failure_falls_back_to_openai_next_for_all_text_capabilities():
    minimax = FailingMiniMaxProvider("MiniMax request failed with HTTP 500: secret detail")
    openai_next = FakeOpenAINextTextProvider()
    settings = Settings(
        app_env="development",
        minimax_api_key="sk-test",
        minimax_base_url="https://api.minimaxi.com/v1",
        openai_compatible_model="MiniMax-M3",
        openai_next_api_key="openai-next-secret",
        openai_next_base_url="https://api.openai-next.com/v1",
        openai_next_model="gpt-5",
    )
    gateway = ProviderGateway(
        settings=settings,
        minimax_client=minimax,
        openai_next_client=openai_next,
    )

    chat = await gateway.run("chat_llm", {"draft_reply": "draft"})
    story = await gateway.run("story_generation", {"retrieved_memories": []})
    compression = await gateway.run(
        "memory_context_compression",
        {"long_term_memory_md": "- memory_card_id: mem-1"},
    )
    profile = await gateway.run("persona_profile_analysis", {"persona_card": {"name": "Grandma"}})
    document = await gateway.run(
        "memory_document_generation",
        {"persona_card": {"name": "Grandma"}},
    )

    for result in [chat, story, compression, profile, document]:
        assert result["provider_name"] == "openai_next"
        assert result["provider_type"] == "third_party"
        assert result["fallback_from_provider"] == "minimax"
        assert "secret detail" in result["fallback_reason"]
        assert "openai-next-secret" not in result["fallback_reason"]
    assert [call[0] for call in minimax.calls] == [
        "chat_llm",
        "story_generation",
        "memory_context_compression",
        "persona_profile_analysis",
        "memory_document_generation",
    ]
    assert [call[0] for call in openai_next.calls] == [
        "chat_llm",
        "story_generation",
        "memory_context_compression",
        "persona_profile_analysis",
        "memory_document_generation",
    ]
    assert chat["output"]["reply_text"] == "openai-next chat reply"
    assert compression["output"]["selected_memory_ids"] == ["fallback-mem-1"]
    assert profile["output"]["persona_version"] == "persona_engine_v2_openai_next"
    assert document["output"]["profile_summary"]
    assert document["output"]["trust_score"] == 72


@pytest.mark.asyncio
async def test_minimax_voice_failure_does_not_fallback_to_openai_next():
    minimax = FailingMiniMaxProvider("MiniMax voice failed")
    openai_next = FakeOpenAINextTextProvider()
    settings = Settings(
        app_env="development",
        minimax_api_key="sk-test",
        minimax_base_url="https://api.minimaxi.com/v1",
        openai_next_api_key="openai-next-secret",
        openai_next_base_url="https://api.openai-next.com/v1",
        openai_next_model="gpt-5",
    )

    with pytest.raises(RuntimeError, match="MiniMax voice failed"):
        await ProviderGateway(
            settings=settings,
            minimax_client=minimax,
            openai_next_client=openai_next,
        ).run("tts", {"text": "hello"})

    assert [call[0] for call in minimax.calls] == ["tts"]
    assert openai_next.calls == []


@pytest.mark.asyncio
async def test_unconfigured_openai_next_preserves_minimax_text_failure_behavior():
    minimax = FailingMiniMaxProvider("MiniMax text failed")
    settings = Settings(
        app_env="development",
        minimax_api_key="sk-test",
        minimax_base_url="https://api.minimaxi.com/v1",
        openai_compatible_model="MiniMax-M3",
    )

    with pytest.raises(RuntimeError, match="MiniMax text failed"):
        await ProviderGateway(settings=settings, minimax_client=minimax).run(
            "chat_llm",
            {"draft_reply": "draft"},
        )


@pytest.mark.asyncio
async def test_minimax_gateway_falls_back_to_mock_in_test_env():
    settings = Settings(
        app_env="test",
        minimax_api_key="sk-test",
        minimax_base_url="https://api.minimaxi.com/v1",
    )

    result = await ProviderGateway(settings=settings).run(
        "tts",
        {
            "text": "小铭，慢慢来。",
            "voice_status": "default_tts",
            "voice_model_id": "voice-1",
        },
    )

    assert result["provider_name"] == "mock"
    assert result["provider_type"] == "local"
    assert result["output"]["audio_url"].startswith("mock://tts/")


def test_dashscope_memory_candidates_normalize_to_prd_categories():
    normalized = _normalize_memory_candidates(
        [
            {
                "title": "口头禅",
                "content": "外婆常说慢慢来。",
                "category": "言语习惯",
                "confidence_level": "high",
                "confidence_score": 90,
                "source_quote": "慢慢来",
            },
            {
                "title": "模糊分类",
                "content": "外婆说过一件没有明确分类的事。",
                "category": "模型自创分类",
                "confidence_level": "medium",
                "confidence_score": 60,
                "source_quote": "一件事",
            },
        ],
        {"source_location": "manual:body"},
    )

    assert normalized[0]["category"] == "expression_style"
    assert normalized[1]["category"] == "unknown"
