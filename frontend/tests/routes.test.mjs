import assert from "node:assert/strict";
import test from "node:test";
import { ROUTES } from "../src/lib/routes.js";
import { API_PATHS, getApiBaseUrl } from "../src/lib/api.js";

test("PRD P0 routes are exposed for the current shell", () => {
  assert.equal(ROUTES.home, "/");
  assert.equal(ROUTES.dashboard, "/dashboard");
});

test("Milestone 1 persona routes are exposed", () => {
  assert.equal(ROUTES.personasNew, "/personas/new");
  assert.equal(ROUTES.personaDetail("abc"), "/personas/abc");
});

test("Milestone 2 routes are exposed", () => {
  assert.equal(ROUTES.personaUploads("p1"), "/personas/p1/uploads");
  assert.equal(ROUTES.personaJobs("p1"), "/personas/p1/jobs");
});

test("Milestone 3 memory audit routes are exposed", () => {
  assert.equal(ROUTES.personaMemories("p1"), "/personas/p1/memories");
});

test("Milestone 4 profile route is exposed", () => {
  assert.equal(ROUTES.personaProfile("p1"), "/personas/p1/profile");
});

test("Milestone 5 chat route is exposed", () => {
  assert.equal(ROUTES.personaChat("p1"), "/personas/p1/chat");
});

test("Milestone 6 voice route is exposed", () => {
  assert.equal(ROUTES.personaVoice("p1"), "/personas/p1/voice");
});

test("Milestone 7 avatar route is exposed", () => {
  assert.equal(ROUTES.personaAvatar("p1"), "/personas/p1/avatar");
});

test("Milestone 3 memory API paths are exposed", () => {
  assert.equal(API_PATHS.memories.list("p1"), "/api/personas/p1/memories");
  assert.equal(API_PATHS.memories.detail("m1"), "/api/memories/m1");
  assert.equal(API_PATHS.memories.confirm("m1"), "/api/memories/m1/confirm");
  assert.equal(API_PATHS.memories.reject("m1"), "/api/memories/m1/reject");
  assert.equal(API_PATHS.memories.disable("m1"), "/api/memories/m1/disable");
});

test("Milestone 4 profile API paths are exposed", () => {
  assert.equal(API_PATHS.profile.detail("p1"), "/api/personas/p1/profile");
  assert.equal(
    API_PATHS.profile.regenerate("p1"),
    "/api/personas/p1/profile/regenerate"
  );
  assert.equal(
    API_PATHS.profile.recalculateTrust("p1"),
    "/api/personas/p1/recalculate-trust"
  );
});

test("Milestone 5 chat API paths are exposed", () => {
  assert.equal(
    API_PATHS.chat.conversations("p1"),
    "/api/personas/p1/conversations"
  );
  assert.equal(
    API_PATHS.chat.messages("c1"),
    "/api/conversations/c1/messages"
  );
  assert.equal(
    API_PATHS.chat.citations("m1"),
    "/api/messages/m1/citations"
  );
  assert.equal(
    API_PATHS.chat.correctMemory("m1"),
    "/api/messages/m1/correct-memory"
  );
});

test("Milestone 6 voice API paths are exposed", () => {
  assert.equal(API_PATHS.voice.config("p1"), "/api/personas/p1/voice");
  assert.equal(API_PATHS.voice.defaultTts("p1"), "/api/personas/p1/voice/default-tts");
  assert.equal(API_PATHS.voice.samples("p1"), "/api/personas/p1/voice/samples");
  assert.equal(API_PATHS.voice.clone("p1"), "/api/personas/p1/voice/clone");
  assert.equal(API_PATHS.voice.synthesize("p1"), "/api/personas/p1/voice/synthesize");
  assert.equal(API_PATHS.voice.voiceMessage("c1"), "/api/conversations/c1/voice-message");
});

test("Milestone 7 avatar API paths are exposed", () => {
  assert.equal(API_PATHS.avatar.config("p1"), "/api/personas/p1/avatar");
  assert.equal(API_PATHS.avatar.defaultAvatar("p1"), "/api/personas/p1/avatar/default");
  assert.equal(API_PATHS.avatar.generate("p1"), "/api/personas/p1/avatar/generate");
});

test("Milestone 8 story API paths are exposed", () => {
  assert.equal(API_PATHS.stories.list("p1"), "/api/personas/p1/stories");
  assert.equal(API_PATHS.stories.favorite("s1"), "/api/stories/s1/favorite");
});

test("API base URL defaults to local FastAPI backend", () => {
  assert.equal(getApiBaseUrl(), "http://localhost:8000");
});

test("demo session API path is exposed", () => {
  assert.equal(API_PATHS.auth.demo, "/api/auth/demo");
});
