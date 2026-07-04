import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  DEFAULT_TTS_NOTICE,
  DEFAULT_TTS_VOICES,
  VOICE_API_PATHS,
  buildDefaultTtsPayload,
  defaultTtsVoiceLabel,
  hasChatReadyVoiceConfig,
  isBlankVoiceText,
  latestCloneSourceModel,
  personaVoiceRoute,
  voiceIdFromModel,
  voiceModelSummary,
  voiceSourceLabel,
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
    emotion: "comfort",
    voice_id: "Chinese (Mandarin)_Kind-hearted_Elder"
  });
  assert.deepEqual(buildDefaultTtsPayload("Chinese (Mandarin)_Gentle_Senior"), {
    gender: "female",
    age_style: "elderly",
    style: "gentle",
    speed: "normal",
    emotion: "comfort",
    voice_id: "Chinese (Mandarin)_Gentle_Senior"
  });
});

test("default TTS voices expose MiniMax Mandarin system voices", () => {
  assert.equal(DEFAULT_TTS_VOICES[0].voice_id, "Chinese (Mandarin)_Reliable_Executive");
  assert.equal(DEFAULT_TTS_VOICES[0].voice_name, "可靠高管");
  assert.equal(
    DEFAULT_TTS_VOICES.some((voice) => voice.voice_id === "Robot_Armor"),
    false
  );
  assert.equal(
    DEFAULT_TTS_VOICES.some(
      (voice) => voice.voice_id === "Chinese (Mandarin)_Cute_Spirit"
    ),
    false
  );
  assert.ok(
    DEFAULT_TTS_VOICES.some(
      (voice) =>
        voice.voice_id === "Chinese (Mandarin)_Kind-hearted_Elder" &&
        voice.voice_name === "亲切长者"
    )
  );
  assert.ok(
    DEFAULT_TTS_VOICES.some(
      (voice) => voice.voice_id === "Chinese (Mandarin)_Warm-HeartedAunt"
    )
  );
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

test("voice helpers summarize default system voice and cloned voice source", () => {
  const defaultModel = {
    id: "default-1",
    persona_id: "p1",
    provider_type: "local",
    provider_name: "mock_default_tts",
    status: "default_tts",
    reference_audio_asset_id: null,
    model_artifact_url:
      "minimax://system-voice/Chinese%20%28Mandarin%29_Gentle_Senior",
    sample_text: "default_tts:voice_id=Chinese (Mandarin)_Gentle_Senior",
    sample_audio_url: null,
    quality_score: null,
    user_selected: true,
    created_at: "2026-07-04T00:00:00",
    updated_at: "2026-07-04T00:00:00"
  };
  const clonedModel = {
    ...defaultModel,
    id: "clone-1",
    status: "cloned_ready",
    provider_name: "minimax",
    model_artifact_url: "minimax://voice/PMV12345678",
    quality_score: 82
  };

  assert.equal(voiceIdFromModel(defaultModel), "Chinese (Mandarin)_Gentle_Senior");
  assert.equal(defaultTtsVoiceLabel("Chinese (Mandarin)_Gentle_Senior"), "温和长辈");
  assert.equal(
    voiceModelSummary(defaultModel),
    "系统默认 TTS · 温和长辈 · Chinese (Mandarin)_Gentle_Senior"
  );
  assert.equal(
    voiceSourceLabel(defaultModel, "speech-2.8-hd"),
    "MiniMax speech-2.8-hd · voice_id Chinese (Mandarin)_Gentle_Senior"
  );
  assert.equal(
    voiceSourceLabel(clonedModel, "speech-2.8-hd"),
    "用户创建的模拟音色 ID：clone-1 · MiniMax voice_id PMV12345678"
  );
});

test("voice chat readiness requires a selected default TTS or cloned voice", () => {
  const defaultModel = {
    id: "default-1",
    persona_id: "p1",
    provider_type: "local",
    provider_name: "mock_default_tts",
    status: "default_tts",
    reference_audio_asset_id: null,
    model_artifact_url:
      "minimax://system-voice/Chinese%20%28Mandarin%29_Gentle_Senior",
    sample_text: "default_tts:voice_id=Chinese (Mandarin)_Gentle_Senior",
    sample_audio_url: null,
    quality_score: null,
    user_selected: true,
    created_at: "2026-07-04T00:00:00",
    updated_at: "2026-07-04T00:00:00"
  };

  assert.equal(
    hasChatReadyVoiceConfig({
      persona_id: "p1",
      voice_status: "no_voice",
      selected_voice_model: null,
      voice_models: [],
      default_tts_notice: DEFAULT_TTS_NOTICE,
      default_tts_options: {},
      default_tts_voices: DEFAULT_TTS_VOICES,
      tts_model: "speech-2.8-hd"
    }),
    false
  );
  assert.equal(
    hasChatReadyVoiceConfig({
      persona_id: "p1",
      voice_status: "default_tts",
      selected_voice_model: defaultModel,
      voice_models: [defaultModel],
      default_tts_notice: DEFAULT_TTS_NOTICE,
      default_tts_options: {},
      default_tts_voices: DEFAULT_TTS_VOICES,
      tts_model: "speech-2.8-hd"
    }),
    true
  );
  assert.equal(
    hasChatReadyVoiceConfig({
      persona_id: "p1",
      voice_status: "cloned_ready",
      selected_voice_model: { ...defaultModel, status: "cloned_ready" },
      voice_models: [{ ...defaultModel, status: "cloned_ready" }],
      default_tts_notice: DEFAULT_TTS_NOTICE,
      default_tts_options: {},
      default_tts_voices: DEFAULT_TTS_VOICES,
      tts_model: "speech-2.8-hd"
    }),
    true
  );
  assert.equal(
    hasChatReadyVoiceConfig({
      persona_id: "p1",
      voice_status: "sample_ready",
      selected_voice_model: { ...defaultModel, status: "sample_ready" },
      voice_models: [{ ...defaultModel, status: "sample_ready" }],
      default_tts_notice: DEFAULT_TTS_NOTICE,
      default_tts_options: {},
      default_tts_voices: DEFAULT_TTS_VOICES,
      tts_model: "speech-2.8-hd"
    }),
    false
  );
});

test("voice clone source prefers the just-created sample then latest sample", () => {
  const baseModel = {
    id: "default-1",
    persona_id: "p1",
    provider_type: "local",
    provider_name: "mock_default_tts",
    status: "default_tts",
    reference_audio_asset_id: null,
    model_artifact_url: null,
    sample_text: null,
    sample_audio_url: null,
    quality_score: null,
    user_selected: true,
    created_at: "2026-07-04T00:00:00",
    updated_at: "2026-07-04T00:00:00"
  };
  const oldSample = {
    ...baseModel,
    id: "old-sample",
    status: "sample_ready",
    reference_audio_asset_id: "old-audio",
    created_at: "2026-07-04T00:01:00"
  };
  const newSample = {
    ...baseModel,
    id: "new-wav-sample",
    status: "sample_ready",
    reference_audio_asset_id: "new-wav-audio",
    created_at: "2026-07-04T00:02:00"
  };
  const failedSample = {
    ...baseModel,
    id: "failed-sample",
    status: "clone_failed",
    reference_audio_asset_id: "failed-audio",
    created_at: "2026-07-04T00:03:00"
  };
  const models = [baseModel, oldSample, newSample, failedSample];

  assert.equal(latestCloneSourceModel(models, "old-sample")?.id, "old-sample");
  assert.equal(latestCloneSourceModel(models)?.id, "new-wav-sample");
  assert.equal(latestCloneSourceModel([baseModel])?.id, undefined);
});

test("voice clone failure notice explains MiniMax short audio errors", () => {
  const source = readFileSync("app/personas/[id]/voice/page.tsx", "utf8");

  assert.match(source, /cloneFailureNotice/);
  assert.match(source, /voice duration too short/);
  assert.match(source, /至少 10 秒/);
});

test("voice page exposes selectable default TTS and preview source copy", () => {
  const source = readFileSync("app/personas/[id]/voice/page.tsx", "utf8");

  assert.match(source, /使用所选默认 TTS/);
  assert.match(source, /当前语音来源/);
  assert.match(source, /selectedDefaultVoiceId/);
  assert.match(source, /voice\.voice_name}：{voice\.voice_id}/);
  assert.doesNotMatch(source, /voice\.voice_name} · {voice\.voice_id}/);
  assert.doesNotMatch(source, /选择默认 TTS/);
});

test("voice page uploads clean human voice audio instead of selecting audio materials", () => {
  const source = readFileSync("app/personas/[id]/voice/page.tsx", "utf8");

  assert.match(source, /uploadMaterials/);
  assert.match(source, /id="voice-sample-upload"/);
  assert.match(source, /accept="audio\/\*"/);
  assert.match(source, /必须上传纯净无噪声的人声音频/);
  assert.match(source, /上传并创建音色样本/);
  assert.doesNotMatch(source, /id="audio-material"/);
  assert.doesNotMatch(source, /选择音频资料/);
  assert.doesNotMatch(source, /暂无可用音频资料/);
  assert.doesNotMatch(source, /listMaterials/);
});

test("voice page records TA voice sample in browser before uploading", () => {
  const source = readFileSync("app/personas/[id]/voice/page.tsx", "utf8");

  assert.match(source, /navigator\.mediaDevices\.getUserMedia/);
  assert.match(source, /new MediaRecorder/);
  assert.match(source, /convertRecordedBlobToWavFile/);
  assert.match(source, /encodeWavAudioBuffer/);
  assert.match(source, /new AudioContext|webkitAudioContext/);
  assert.match(source, /decodeAudioData/);
  assert.match(source, /audio\/wav/);
  assert.match(source, /voice-sample-recording-\$\{Date\.now\(\)\}\.wav/);
  assert.match(source, /MINIMAX_VOICE_CLONE_MIN_SECONDS/);
  assert.match(source, /readAudioDurationSeconds/);
  assert.match(source, /audio\.duration/);
  assert.match(source, /validateCloneSampleDuration/);
  assert.match(source, /MiniMax 音色克隆要求样本至少 10 秒/);
  assert.match(source, /recordingChunksRef/);
  assert.match(source, /URL\.createObjectURL/);
  assert.match(source, /URL\.revokeObjectURL/);
  assert.match(source, /track\.stop\(\)/);
  assert.match(source, /recordedVoiceFile/);
  assert.match(source, /recordingAudioUrl/);
  assert.match(source, /录制 TA 的人声音频/);
  assert.match(source, /开始录音/);
  assert.match(source, /停止录音/);
  assert.match(source, /重新录制/);
  assert.match(source, /确认上传录音并创建音色样本/);
  assert.match(source, /无法访问麦克风，请检查浏览器权限，或改为上传音频文件。/);
  assert.match(source, /没有录到可用音频，请重新录制。/);
  assert.match(source, /录音转 WAV 失败，请重新录制或上传 mp3\/m4a\/wav 音频。/);
  assert.match(source, /已转为 WAV，可用于 MiniMax 音色克隆上传。/);
  assert.doesNotMatch(source, /voice-sample-recording-\$\{Date\.now\(\)\}\.\$\{extension\}/);
});

test("voice page explains the two-step sample and clone workflow", () => {
  const source = readFileSync("app/personas/[id]/voice/page.tsx", "utf8");

  assert.match(source, /上传或录音后会创建“音色样本”，还不会生成可用模拟音色。/);
  assert.match(source, /生成模拟音色会调用 MiniMax 克隆接口，成功后得到 MiniMax voice_id 并设为当前模拟音色。/);
  assert.match(source, /上传并创建音色样本/);
  assert.match(source, /生成模拟音色/);
});
