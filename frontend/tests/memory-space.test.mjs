import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import test from "node:test";

async function loadMemorySpaceModule() {
  try {
    return await import("../src/lib/memory-space.js");
  } catch (error) {
    assert.fail(`Expected memory-space display helpers to be exported: ${error.message}`);
  }
}

test("homepage navigation exposes the requested tabs and anchor targets", async () => {
  const { MEMORY_SPACE_NAV_ITEMS, MEMORY_SPACE_COPY } = await loadMemorySpaceModule();

  assert.deepEqual(
    MEMORY_SPACE_NAV_ITEMS.map((item) => item.label),
    ["首页", "产品介绍", "创建档案", "记忆审核", "星光故事"]
  );
  assert.deepEqual(
    MEMORY_SPACE_NAV_ITEMS.map((item) => item.href),
    ["/", "/#product-intro", "/personas/new", "/#memory-review", "/#star-stories"]
  );
  assert.equal(
    MEMORY_SPACE_NAV_ITEMS.some((item) => item.label.includes("工作台")),
    false
  );
  assert.equal(MEMORY_SPACE_COPY.spaceName, "记忆空间");
});

test("memory space assets are local files with source metadata", async () => {
  const { MEMORY_SPACE_ASSETS } = await loadMemorySpaceModule();
  const requiredAssets = [
    "grandmotherTea",
    "familyAlbum",
    "familyLivingRoom",
    "memoryStringLights"
  ];

  for (const key of requiredAssets) {
    const asset = MEMORY_SPACE_ASSETS[key];
    assert.ok(asset, `missing asset ${key}`);
    assert.match(asset.src, /^\/memory-space\/.+\.(jpg|jpeg|png|webp)$/);
    assert.match(asset.sourceUrl, /^https:\/\/www\.pexels\.com\/photo\//);
    assert.ok(asset.alt.length > 8);
    assert.ok(asset.usage.length > 8);
    assert.equal(
      existsSync(new URL(`../public${asset.src}`, import.meta.url)),
      true,
      `missing local asset file ${asset.src}`
    );
  }
});

test("memory journey copy uses immersive flow language", async () => {
  const { MEMORY_JOURNEY_STEPS } = await loadMemorySpaceModule();

  assert.deepEqual(
    MEMORY_JOURNEY_STEPS.map((step) => step.title),
    ["创建人物", "上传资料", "资料解析与审核", "开启互动"]
  );
  assert.equal(
    MEMORY_JOURNEY_STEPS.some((step) => step.description.includes("工作台")),
    false
  );
});
