import test from "node:test";
import assert from "node:assert/strict";
import {
  canUseMemoryInConversation,
  memoryCategoryLabel,
  memoryStatusLabel
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
