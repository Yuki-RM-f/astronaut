import assert from "node:assert/strict";
import test from "node:test";
import { normalizeStoryTheme, storySourceSummary } from "../src/lib/stories.js";

test("story theme falls back to shared memory when blank", () => {
  assert.equal(normalizeStoryTheme("  "), "共同回忆");
  assert.equal(normalizeStoryTheme(" 遗憾告白 "), "遗憾告白");
});

test("story source summary keeps source titles scannable", () => {
  const baseStory = {
    id: "story-1",
    persona_id: "p1",
    theme: "共同回忆",
    title: "海边那天",
    content: "小铭，我还记得那天。",
    audio_url: null,
    source_memory_ids: ["m1", "m2"],
    is_favorite: false,
    metadata_json: null,
    created_at: "2026-07-04T00:00:00",
    updated_at: "2026-07-04T00:00:00"
  };

  assert.equal(
    storySourceSummary({
      ...baseStory,
      source_memories: [
        { memory_card_id: "m1", title: "海边日落", quote: "一起看日落", source_location: "相册第 1 页" },
        { memory_card_id: "m2", title: "生日馄饨", quote: "一起包馄饨", source_location: "手动资料" },
        { memory_card_id: "m3", title: "春天散步", quote: "一起散步", source_location: null }
      ]
    }),
    "海边日落（相册第 1 页） · 生日馄饨（手动资料）"
  );
  assert.equal(
    storySourceSummary({ ...baseStory, source_memory_ids: [], source_memories: [] }),
    "暂无已关联的记忆来源"
  );
});
