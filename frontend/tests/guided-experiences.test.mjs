import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  getGuidedExperienceConfig,
  guidedExperienceConversationKind,
  guidedExperienceContextKind,
  guidedExperienceRoute
} from "../src/lib/guided-experiences.js";

test("regret experience asks for unsaid words first", () => {
  const config = getGuidedExperienceConfig("regrets", "外婆");

  assert.equal(config.title, "遗憾对话室");
  assert.match(config.openingMessage, /以前没说的话/);
  assert.match(config.inputPlaceholder, /来不及说/);
  assert.equal(guidedExperienceConversationKind("regrets"), "regrets");
  assert.equal(guidedExperienceRoute("regrets", "p1"), "/personas/p1/regrets");
});

test("wish experience asks for a wish and frames action without persistence claims", () => {
  const config = getGuidedExperienceConfig("wishes", "外婆");

  assert.equal(config.title, "心愿延续系统");
  assert.match(config.openingMessage, /想完成的心愿/);
  assert.match(config.emptyState, /下一步可以做的小事/);
  assert.equal(config.persistenceNotice, "当前不会创建独立心愿记录，会以这次对话继续陪你梳理。");
  assert.equal(guidedExperienceConversationKind("wishes"), "wishes");
  assert.equal(guidedExperienceContextKind("wishes"), "wishes");
  assert.equal(guidedExperienceRoute("wishes", "p1"), "/personas/p1/wishes");
});

test("guided experience page loads a conversation scoped to the guided kind", () => {
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
