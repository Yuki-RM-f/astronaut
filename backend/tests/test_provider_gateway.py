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
        return {
            "clone_status": "succeeded",
            "model_artifact_url": "minimax://voice/PMV12345678",
            "preview_audio_url": "https://api.minimaxi.com/audio/clone.mp3",
            "quality_score": 82,
        }


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

    assert chat["provider_name"] == "minimax"
    assert chat["provider_type"] == "third_party"
    assert chat["capability"] == "chat_llm"
    assert story["provider_name"] == "minimax"
    assert story["capability"] == "story_generation"
    assert compression["provider_name"] == "minimax"
    assert compression["capability"] == "memory_context_compression"
    assert compression["output"]["selected_memory_ids"] == ["mem-1"]
    assert [call[0] for call in minimax.calls] == [
        "chat_llm",
        "story_generation",
        "memory_context_compression",
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
