import pytest

from app.core.config import Settings
from app.providers.dashscope import DashScopeProvider


@pytest.mark.asyncio
async def test_dashscope_asr_uses_input_audio_payload(tmp_path):
    audio_path = tmp_path / "voice.mp3"
    audio_path.write_bytes(b"fake mp3 bytes")
    provider = DashScopeProvider(
        Settings(
            dashscope_api_key="sk-test",
            qwen_asr_model="qwen3-asr-flash",
        )
    )
    captured = {}

    async def fake_chat_completion(model, messages, **request_options):
        captured["model"] = model
        captured["messages"] = messages
        captured["request_options"] = request_options
        return "外婆说慢慢来。"

    provider._chat_completion = fake_chat_completion

    result = await provider._asr(
        {"storage_url": audio_path.as_posix(), "file_name": "voice.mp3"}
    )

    content = captured["messages"][0]["content"]
    assert len(content) == 1
    audio_item = content[0]
    assert captured["model"] == "qwen3-asr-flash"
    assert audio_item["type"] == "input_audio"
    assert audio_item["input_audio"]["data"].startswith("data:audio/mpeg;base64,")
    assert set(audio_item["input_audio"]) == {"data"}
    assert "audio_url" not in audio_item
    assert captured["request_options"]["asr_options"] == {"enable_itn": False}
    assert result["transcript"] == "外婆说慢慢来。"
    assert result["sample_metadata"]["speaker"] == "unknown"


@pytest.mark.asyncio
async def test_dashscope_video_blob_uses_video_url_payload():
    provider = DashScopeProvider(
        Settings(
            dashscope_api_key="sk-test",
            qwen_vision_model="qwen3.7-plus",
        )
    )
    captured = {}

    async def fake_chat_completion(model, messages, **request_options):
        captured["model"] = model
        captured["messages"] = messages
        captured["request_options"] = request_options
        return "视频里有人在介绍火山熔岩。"

    provider._chat_completion = fake_chat_completion

    result = await provider._describe_video_blob(
        {"file_name": "volcano.webm", "user_description": "公开视频样本"},
        "data:video/webm;base64,AAAA",
        "This is lava.",
    )

    video_item = captured["messages"][0]["content"][1]
    assert captured["model"] == "qwen3.7-plus"
    assert video_item == {
        "type": "video_url",
        "video_url": {"url": "data:video/webm;base64,AAAA", "fps": 1},
    }
    assert captured["request_options"] == {}
    assert result == "视频里有人在介绍火山熔岩。"


@pytest.mark.asyncio
async def test_dashscope_video_frames_use_dashscope_minimum_safe_fps():
    provider = DashScopeProvider(
        Settings(
            dashscope_api_key="sk-test",
            qwen_vision_model="qwen3.7-plus",
        )
    )
    captured = {}

    async def fake_chat_completion(model, messages, **request_options):
        captured["messages"] = messages
        return "视频关键帧显示一段公开视频场景。"

    provider._chat_completion = fake_chat_completion

    await provider._describe_video_frames(
        {"file_name": "clip.mp4"},
        [
            "data:image/jpeg;base64,1",
            "data:image/jpeg;base64,2",
            "data:image/jpeg;base64,3",
            "data:image/jpeg;base64,4",
        ],
        "short transcript",
    )

    video_item = captured["messages"][0]["content"][1]
    assert video_item["type"] == "video"
    assert video_item["fps"] == 0.5
