import pytest

from app.providers.gateway import ProviderGateway


@pytest.mark.asyncio
async def test_mock_gateway_returns_capability_result():
    result = await ProviderGateway().run("chat_llm", {"message": "你好"})

    assert result["provider_name"] == "mock"
    assert result["capability"] == "chat_llm"
    assert result["status"] == "succeeded"
    assert result["input"]["message"] == "你好"
    assert result["output"]["reply_text"]
