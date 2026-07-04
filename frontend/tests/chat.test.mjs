import assert from "node:assert/strict";
import test from "node:test";
import {
  buildCorrectionPayload,
  citationSummary,
  hasPlayableAudio,
  isBlankChatText,
  messageRoleLabel
} from "../src/lib/chat.js";

test("chat role labels stay scoped to text chat", () => {
  assert.equal(messageRoleLabel("user"), "你");
  assert.equal(messageRoleLabel("persona"), "TA");
  assert.equal(messageRoleLabel("system"), "system");
});

test("citation summary prefers memory and source references", () => {
  assert.equal(
    citationSummary({
      id: "c1",
      message_id: "m1",
      memory_card_id: "mem-1",
      source_material_id: "mat-1",
      parsed_chunk_id: "chunk-1",
      quote: "外婆喜欢包馄饨。",
      source_location: "manual:body#1",
      created_at: "2026-07-04T00:00:00"
    }),
    "记忆 mem-1 · 资料 mat-1 · manual:body#1"
  );
});

test("blank chat and correction text is rejected before submit", () => {
  assert.equal(isBlankChatText("   "), true);
  assert.equal(isBlankChatText("我今天很想你"), false);
  assert.throws(() => buildCorrectionPayload("mem-1", " "), /纠正内容不能为空/);
  assert.deepEqual(buildCorrectionPayload("mem-1", " 外婆喜欢包馄饨。 "), {
    memory_id: "mem-1",
    content: "外婆喜欢包馄饨。"
  });
});

test("persona audio playback is shown only when a message has an audio url", () => {
  const baseMessage = {
    id: "m1",
    conversation_id: "c1",
    role: "persona",
    content: "小铭，我在。",
    metadata_json: null,
    created_at: "2026-07-04T00:00:00",
    citations: []
  };

  assert.equal(hasPlayableAudio({ ...baseMessage, audio_url: null }), false);
  assert.equal(hasPlayableAudio({ ...baseMessage, audio_url: "   " }), false);
  assert.equal(hasPlayableAudio({ ...baseMessage, audio_url: "mock://tts/m1.wav" }), true);
});
