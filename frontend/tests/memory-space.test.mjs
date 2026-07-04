import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

async function loadMemorySpaceModule() {
  try {
    return await import("../src/lib/memory-space.js");
  } catch (error) {
    assert.fail(`Expected memory-space display helpers to be exported: ${error.message}`);
  }
}

test("homepage navigation exposes the requested tabs and page targets", async () => {
  const { MEMORY_SPACE_NAV_ITEMS, MEMORY_SPACE_COPY } = await loadMemorySpaceModule();

  assert.deepEqual(
    MEMORY_SPACE_NAV_ITEMS.map((item) => item.label),
    ["首页", "产品介绍", "创建档案", "我的星空"]
  );
  assert.deepEqual(
    MEMORY_SPACE_NAV_ITEMS.map((item) => item.href),
    ["/", "/product-intro", "/personas/new", "/dashboard"]
  );
  assert.equal(
    MEMORY_SPACE_NAV_ITEMS.some((item) => ["记忆审核", "星光故事"].includes(item.label)),
    false
  );
  assert.equal(MEMORY_SPACE_COPY.spaceName, "记忆空间");
});

test("homepage does not render the standalone star stories section", () => {
  const source = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");

  assert.equal(source.includes('id="star-stories"'), false);
  assert.equal(source.includes("星光故事"), false);
  assert.equal(source.includes("查看已有星星"), false);
});

test("persona workspace navigation groups all persona feature pages", async () => {
  const { getPersonaWorkspaceNavGroups } = await loadMemorySpaceModule();

  const groups = getPersonaWorkspaceNavGroups("p1");
  const items = groups.flatMap((group) => group.items);

  assert.deepEqual(
    groups.map((group) => group.label),
    ["总览", "资料", "记忆", "互动"]
  );
  assert.deepEqual(
    items.map((item) => item.key),
    [
      "overview",
      "uploads",
      "jobs",
      "memories",
      "chat",
      "regrets",
      "wishes",
      "voice",
      "avatar"
    ]
  );
  assert.deepEqual(
    items.map((item) => item.href),
    [
      "/personas/p1",
      "/personas/p1/uploads",
      "/personas/p1/jobs",
      "/personas/p1/memories",
      "/personas/p1/chat",
      "/personas/p1/regrets",
      "/personas/p1/wishes",
      "/personas/p1/voice",
      "/personas/p1/avatar"
    ]
  );
  assert.equal(items.some((item) => item.href === "/personas/p1/profile"), false);
});

test("persona feature pages do not render the workspace navigation panel", () => {
  const sourceFiles = [
    "../src/components/StarSite.tsx",
    "../app/personas/[id]/page.tsx",
    "../app/personas/[id]/uploads/page.tsx",
    "../app/personas/[id]/jobs/page.tsx",
    "../app/personas/[id]/memories/page.tsx",
    "../app/personas/[id]/profile/page.tsx",
    "../app/personas/[id]/chat/page.tsx",
    "../app/personas/[id]/regrets/page.tsx",
    "../app/personas/[id]/wishes/page.tsx",
    "../app/personas/[id]/voice/page.tsx",
    "../app/personas/[id]/avatar/page.tsx",
    "../src/components/GuidedExperiencePage.tsx"
  ];

  for (const sourceFile of sourceFiles) {
    const source = readFileSync(new URL(sourceFile, import.meta.url), "utf8");

    assert.equal(/<PersonaWorkspaceNav(?:\s|\/|>)/.test(source), false, sourceFile);
    assert.equal(source.includes("人物工作台导航"), false, sourceFile);
    assert.equal(source.includes("返回人物工作台"), false, sourceFile);
  }
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

test("workspace copy separates uploads review from memories storytelling", async () => {
  const { getPersonaWorkspaceNavGroups } = await loadMemorySpaceModule();

  const items = getPersonaWorkspaceNavGroups("p1").flatMap((group) => group.items);
  const uploads = items.find((item) => item.href === "/personas/p1/uploads");
  const memories = items.find((item) => item.href === "/personas/p1/memories");

  assert.ok(uploads);
  assert.ok(memories);
  assert.match(uploads.description, /资料解析|审核/);
  assert.doesNotMatch(memories.description, /审核|可信度/);
  assert.match(memories.description, /回忆|搜索/);
});

test("trust display is limited to uploads page source", () => {
  const uploadsSource = readFileSync(
    new URL("../app/personas/[id]/uploads/page.tsx", import.meta.url),
    "utf8"
  );
  assert.equal(uploadsSource.includes("记忆可信度"), true);
  assert.equal(uploadsSource.includes("完成审核，点亮星星"), true);
  assert.equal(uploadsSource.includes("档案摘要"), false);
  assert.equal(uploadsSource.includes("从已审核记忆重生成"), false);
  assert.equal(uploadsSource.includes("保存档案"), false);

  for (const sourceFile of [
    "../app/dashboard/page.tsx",
    "../app/personas/[id]/page.tsx",
    "../app/personas/[id]/profile/page.tsx",
    "../app/personas/[id]/memories/page.tsx"
  ]) {
    const source = readFileSync(new URL(sourceFile, import.meta.url), "utf8");

    assert.equal(source.includes("记忆可信度"), false, sourceFile);
    assert.equal(source.includes("可信度组成"), false, sourceFile);
    assert.equal(source.includes("重新计算可信度"), false, sourceFile);
    assert.equal(source.includes("trust_score"), false, sourceFile);
  }
});

test("uploads page uses memory tiles and card-level importance", () => {
  const uploadsSource = readFileSync(
    new URL("../app/personas/[id]/uploads/page.tsx", import.meta.url),
    "utf8"
  );

  for (const required of [
    "上传珍贵回忆",
    "照片",
    "视频",
    "声音",
    "文字",
    "手动资料",
    "资料内容",
    "UploadMemoryTile",
    "toggleMemoryImportance",
    "is_important"
  ]) {
    assert.equal(uploadsSource.includes(required), true, required);
  }

  for (const removed of [
    "备注",
    "重要程度",
    "ProfileSummaryPanel",
    "summaryDraft",
    "profileBusyAction",
    "regeneratePersonaProfile",
    "updatePersonaProfile"
  ]) {
    assert.equal(uploadsSource.includes(removed), false, removed);
  }
});
