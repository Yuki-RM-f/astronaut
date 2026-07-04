import assert from "node:assert/strict";
import test from "node:test";
import {
  DEFAULT_TTS_NOTICE,
  VOICE_API_PATHS,
  buildDefaultTtsPayload,
  isBlankVoiceText,
  personaVoiceRoute,
  voiceModelSummary,
  voiceStatusLabel
} from "../src/lib/voice.js";

test("voice route and API paths follow Milestone 6 contract", () => {
  assert.equal(personaVoiceRoute("p1"), "/personas/p1/voice");
  assert.equal(VOICE_API_PATHS.config("p1"), "/api/personas/p1/voice");
  assert.equal(VOICE_API_PATHS.defaultTts("p1"), "/api/personas/p1/voice/default-tts");
  assert.equal(VOICE_API_PATHS.samples("p1"), "/api/personas/p1/voice/samples");
  assert.equal(VOICE_API_PATHS.clone("p1"), "/api/personas/p1/voice/clone");
  assert.equal(VOICE_API_PATHS.synthesize("p1"), "/api/personas/p1/voice/synthesize");
  assert.equal(
    VOICE_API_PATHS.voiceMessage("c1"),
    "/api/conversations/c1/voice-message"
  );
});

test("default TTS warning matches PRD copy exactly", () => {
  assert.equal(
    DEFAULT_TTS_NOTICE,
    "当前使用系统默认声音，不是 TA 的真实声音。上传 TA 的清晰语音后，可以尝试生成模拟音色。"
  );
});

test("voice status labels expose PRD statuses", () => {
  assert.equal(voiceStatusLabel("no_voice"), "未设置声音");
  assert.equal(voiceStatusLabel("default_tts"), "系统默认 TTS");
  assert.equal(voiceStatusLabel("sample_ready"), "已有可克隆样本");
  assert.equal(voiceStatusLabel("cloning"), "音色克隆中");
  assert.equal(voiceStatusLabel("cloned_ready"), "模拟音色可用");
  assert.equal(voiceStatusLabel("clone_failed"), "音色克隆失败");
});

test("default TTS payload preserves PRD option dimensions", () => {
  assert.deepEqual(buildDefaultTtsPayload(), {
    gender: "female",
    age_style: "elderly",
    style: "gentle",
    speed: "normal",
    emotion: "comfort"
  });
});

test("voice text validation rejects blank synthesis input", () => {
  assert.equal(isBlankVoiceText("   "), true);
  assert.equal(isBlankVoiceText("小铭，慢慢来。"), false);
});

test("voice model summary uses status and provider facts only", () => {
  assert.equal(
    voiceModelSummary({
      id: "v1",
      persona_id: "p1",
      provider_type: "local",
      provider_name: "mock_voice_clone",
      status: "cloned_ready",
      reference_audio_asset_id: "mat1",
      model_artifact_url: "mock://voice-model/v1",
      sample_text: "样本",
      sample_audio_url: "mock://voice-preview/v1.wav",
      quality_score: 82,
      user_selected: true,
      created_at: "2026-07-04T00:00:00",
      updated_at: "2026-07-04T00:00:00"
    }),
    "模拟音色可用 · mock_voice_clone · 质量 82"
  );
});
