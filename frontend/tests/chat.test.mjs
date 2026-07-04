import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  buildOptimisticUserMessage,
  buildPendingPersonaThinkingMessage,
  buildCorrectionPayload,
  citationSummary,
  hasPlayableAudio,
  isAvatarMouthActive,
  isBlankChatText,
  isPendingPersonaThinking,
  messageRoleLabel,
  personaMessageLabel
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

test("avatar mouth is active when any persona audio message is currently playing", () => {
  const messages = [
    {
      id: "u1",
      conversation_id: "c1",
      role: "user",
      content: "外婆，我想你。",
      audio_url: null,
      metadata_json: null,
      created_at: "2026-07-04T00:00:00",
      citations: []
    },
    {
      id: "p1",
      conversation_id: "c1",
      role: "persona",
      content: "小铭，我在。",
      audio_url: "mock://tts/p1.wav",
      metadata_json: null,
      created_at: "2026-07-04T00:00:01",
      citations: []
    }
  ];

  assert.equal(isAvatarMouthActive(messages, "p1"), true);
  assert.equal(isAvatarMouthActive(messages, "u1"), false);
  assert.equal(isAvatarMouthActive(messages, "missing"), false);
  assert.equal(isAvatarMouthActive(messages, null), false);
});

test("optimistic chat helpers create temporary user and pending persona messages", () => {
  const now = new Date("2026-07-05T10:30:00.000Z");
  const userMessage = buildOptimisticUserMessage("c1", "  我今天想你  ", now);
  const pendingMessage = buildPendingPersonaThinkingMessage("c1", "外婆", now);

  assert.equal(userMessage.id, "optimistic-user-1783247400000");
  assert.equal(userMessage.conversation_id, "c1");
  assert.equal(userMessage.role, "user");
  assert.equal(userMessage.content, "我今天想你");
  assert.equal(userMessage.audio_url, null);
  assert.deepEqual(userMessage.citations, []);

  assert.equal(pendingMessage.id, "pending-persona-1783247400000");
  assert.equal(pendingMessage.conversation_id, "c1");
  assert.equal(pendingMessage.role, "persona");
  assert.equal(pendingMessage.content, "外婆正在想...");
  assert.equal(isPendingPersonaThinking(pendingMessage), true);
  assert.equal(isPendingPersonaThinking(userMessage), false);
});

test("persona chat label uses the direct persona name", () => {
  assert.equal(personaMessageLabel("外婆"), "外婆");
  assert.equal(personaMessageLabel("  外婆  "), "外婆");
  assert.equal(personaMessageLabel(""), "TA");
});

test("chat page appends optimistic messages before awaiting the API response", () => {
  const source = readFileSync(new URL("../app/personas/[id]/chat/page.tsx", import.meta.url), "utf8");
  const sendStart = source.indexOf("async function handleSend");
  const sendEnd = source.indexOf("return (", sendStart);
  const sendSource = source.slice(sendStart, sendEnd);

  assert.notEqual(sendStart, -1);
  assert.notEqual(sendEnd, -1);
  assert.match(sendSource, /buildOptimisticUserMessage/);
  assert.match(sendSource, /buildPendingPersonaThinkingMessage/);
  assert.match(sendSource, /setMessages\(\(currentMessages\) => \[/);
  assert.match(sendSource, /const trimmedDraft = draft\.trim\(\);/);
  assert.match(sendSource, /buildOptimisticUserMessage\(conversation\.id, trimmedDraft,/);
  assert.match(sendSource, /setDraft\(""\);/);
  assert.match(sendSource, /await sendMessage\(conversation\.id, trimmedDraft\)/);
  assert.match(sendSource, /setDraft\(trimmedDraft\);/);
  assert.ok(
    sendSource.indexOf("buildOptimisticUserMessage") < sendSource.indexOf("await sendMessage"),
    "optimistic user message should be built before awaiting sendMessage"
  );
  assert.ok(
    sendSource.indexOf("buildPendingPersonaThinkingMessage") < sendSource.indexOf("await sendMessage"),
    "pending persona message should be built before awaiting sendMessage"
  );
  assert.ok(
    sendSource.indexOf('setDraft("")') < sendSource.indexOf("await sendMessage"),
    "draft should clear before awaiting sendMessage"
  );
  assert.match(source, /LoaderCircle/);
  assert.match(source, /animate-spin/);
  assert.match(source, /ConversationWorkspace/);
  assert.match(source, /ChatComposer/);
  assert.match(source, /CHAT_QUICK_PROMPTS/);
  assert.doesNotMatch(source, /scrollIntoView/);
  assert.match(source, /personaMessageLabel\(personaName\)/);
  assert.equal(source.includes("`${personaName}的星星`"), false);
});

test("chat page voice mode records audio and sends it through the voice-message flow", () => {
  const source = readFileSync(new URL("../app/personas/[id]/chat/page.tsx", import.meta.url), "utf8");
  const voiceStart = source.indexOf("function VoiceSurface");
  const messageBubbleStart = source.indexOf("function MessageBubble", voiceStart);
  const voiceSource = source.slice(voiceStart, messageBubbleStart);

  assert.notEqual(voiceStart, -1);
  assert.notEqual(messageBubbleStart, -1);
  assert.match(source, /getVoiceConfig/);
  assert.match(source, /hasChatReadyVoiceConfig/);
  assert.match(source, /voiceSourceLabel/);
  assert.match(source, /uploadMaterials/);
  assert.match(source, /sendVoiceMessage/);
  assert.match(source, /ROUTES\.personaVoice\(personaId\)/);
  assert.match(voiceSource, /navigator\.mediaDevices\.getUserMedia\(\{ audio: true \}\)/);
  assert.match(voiceSource, /new MediaRecorder/);
  assert.match(voiceSource, /uploadMaterials\(personaId/);
  assert.match(voiceSource, /sendVoiceMessage\(conversation\.id/);
  assert.match(voiceSource, /audio\/webm/);
  assert.match(voiceSource, /voiceReplyAudioRef/);
  assert.match(voiceSource, /正在识别语音/);
  assert.match(voiceSource, /去声音设置配置 TTS/);
  assert.doesNotMatch(voiceSource, /这里会用于和\{personaName\}进行语音对话。可以先用文字输入/);
});

test("chat page gesture mode uses local camera recognition and drives avatar motion", () => {
  const source = readFileSync(new URL("../app/personas/[id]/chat/page.tsx", import.meta.url), "utf8");
  const gestureStart = source.indexOf("function GestureSurface");
  const voiceStart = source.indexOf("function VoiceSurface", gestureStart);
  const gestureSource = source.slice(gestureStart, voiceStart);

  assert.notEqual(gestureStart, -1);
  assert.notEqual(voiceStart, -1);
  assert.match(source, /MotionIntent/);
  assert.match(source, /createGestureRecognizer/);
  assert.match(source, /motionIntentForGesture/);
  assert.match(source, /setMotionIntent/);
  assert.match(source, /motionIntent=\{avatarMotionIntent\}/);
  assert.match(gestureSource, /videoRef/);
  assert.match(gestureSource, /navigator\.mediaDevices\.getUserMedia\(\{\s*video:/s);
  assert.match(gestureSource, /requestAnimationFrame/);
  assert.match(gestureSource, /recognizeForVideo/);
  assert.match(gestureSource, /本地识别，不上传摄像头画面/);
  assert.match(gestureSource, /开始摄像头/);
  assert.match(gestureSource, /停止摄像头/);
  assert.doesNotMatch(
    gestureSource,
    /这里会用于和\{personaName\}进行视频手势互动。识别到你的停留、挥手或点头后/
  );
});

test("chat API helpers support conversation kind without changing message send shape", () => {
  const source = readFileSync(new URL("../src/lib/chat.ts", import.meta.url), "utf8");

  assert.match(source, /export type ConversationKind = "chat" \| "regrets" \| "wishes";/);
  assert.match(source, /export type ConversationContextKind = "general" \| "wishes";/);
  assert.match(source, /kind: ConversationKind;/);
  assert.match(source, /context_kind: ConversationContextKind;/);
  assert.match(source, /kind\?: ConversationKind/);
  assert.match(source, /contextKind\?: ConversationContextKind/);
  assert.match(source, /searchParams\.set\("kind", kind\)/);
  assert.match(source, /searchParams\.set\("context_kind", contextKind\)/);
  assert.match(source, /body: JSON\.stringify\(\{\s*title: title\?\.trim\(\) \|\| undefined,\s*kind,\s*context_kind: contextKind\s*\}\)/s);

  const sendStart = source.indexOf("export async function sendMessage");
  const sendEnd = source.indexOf("export async function sendVoiceMessage", sendStart);
  const sendSource = source.slice(sendStart, sendEnd);
  assert.match(sendSource, /body: JSON\.stringify\(\{ content: trimmedContent \}\)/);
  assert.doesNotMatch(sendSource, /kind/);
});

test("chat page loads only normal chat conversations", () => {
  const source = readFileSync(new URL("../app/personas/[id]/chat/page.tsx", import.meta.url), "utf8");
  const loadStart = source.indexOf("async function loadChat");
  const loadSource = source.slice(loadStart);

  assert.match(loadSource, /listConversations\(personaId, "chat"\)/);
  assert.match(loadSource, /createConversation\(personaId, `和\$\{persona\.name\}的对话`, "chat"\)/);
});

test("guided experience page uses a dedicated wishes conversation", () => {
  const source = readFileSync(
    new URL("../src/components/GuidedExperiencePage.tsx", import.meta.url),
    "utf8"
  );
  const loadStart = source.indexOf("async function loadGuidedExperience");
  const loadSource = source.slice(loadStart);

  assert.match(loadSource, /guidedExperienceConversationKind\(kind\)/);
  assert.match(loadSource, /guidedExperienceContextKind\(kind\)/);
  assert.match(loadSource, /listConversations\(personaId, conversationKind, contextKind\)/);
  assert.match(loadSource, /createConversation\(personaId, title, conversationKind, contextKind\)/);
  assert.doesNotMatch(loadSource, /listConversations\(personaId\)/);
});
