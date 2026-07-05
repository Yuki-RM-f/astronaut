import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  canUseMemoryInConversation,
  memoryCategoryLabel,
  memoryStatusLabel,
  selectDimensionActionTargets
} from "../src/lib/memories.js";

test("memory labels expose PRD Milestone 3 statuses and categories", () => {
  assert.equal(memoryStatusLabel("pending_review"), "待审核");
  assert.equal(memoryStatusLabel("confirmed"), "已确认");
  assert.equal(memoryStatusLabel("corrected"), "已修正");
  assert.equal(memoryStatusLabel("rejected"), "已拒绝");
  assert.equal(memoryStatusLabel("disabled"), "已停用");
  assert.equal(memoryStatusLabel("auto_generated"), "自动生成");
  assert.equal(memoryCategoryLabel("shared_event"), "共同经历");
});

test("only confirmed and corrected memories are future usable", () => {
  assert.equal(canUseMemoryInConversation("confirmed"), true);
  assert.equal(canUseMemoryInConversation("corrected"), true);
  assert.equal(canUseMemoryInConversation("disabled"), false);
});

test("dimension actions target visible memories without inventing backend dimensions", () => {
  const memories = [
    { id: "m1", status: "pending_review" },
    { id: "m2", status: "auto_generated" },
    { id: "m3", status: "confirmed" },
    { id: "m4", status: "disabled" }
  ];

  assert.deepEqual(selectDimensionActionTargets(memories, "confirm"), ["m1", "m2"]);
  assert.deepEqual(selectDimensionActionTargets(memories, "delete"), ["m1", "m2", "m3", "m4"]);
  assert.deepEqual(selectDimensionActionTargets(memories, "update"), ["m1"]);
  assert.deepEqual(selectDimensionActionTargets([], "confirm"), []);
});

test("memory helper exposes card-level importance updates", () => {
  const source = readFileSync(new URL("../src/lib/memories.ts", import.meta.url), "utf8");

  assert.equal(source.includes("is_important: boolean"), true);
  assert.equal(source.includes("is_important: boolean;"), true);
});

test("memories page keeps only story telling and semantic search", () => {
  const source = readFileSync(
    new URL("../app/personas/[id]/memories/page.tsx", import.meta.url),
    "utf8"
  );

  assert.equal(source.includes("语义搜索"), true);
  assert.equal(source.includes("让TA讲"), true);
  assert.equal(source.includes("长期/短期记忆"), true);
  assert.equal(source.includes("ensureDefaultStories"), true);
  assert.equal(source.includes(".then(() => listStories(personaId))"), false);
  assert.equal(source.includes("stories.slice(0, 3)"), false);
  assert.equal(source.includes("false ?"), false);
  assert.equal(source.includes("先去资料页审核记忆"), true);
  assert.equal(source.includes("metadata_json"), false);
  assert.equal(source.includes("<think>"), false);

  for (const forbidden of [
    "完成审核",
    "记忆可信度",
    "基础信息",
    "人物关系",
    "档案健康分",
    "待审核",
    "开放冲突",
    "冲突中心",
    "最近事件"
  ]) {
    assert.equal(source.includes(forbidden), false, forbidden);
  }
});
