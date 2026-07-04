import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { JOB_STATUSES, jobStatusLabel } from "../src/lib/jobs.js";
import {
  describeSelectedUploadFiles,
  materialImportanceLabel,
  MATERIAL_TYPE_OPTIONS,
  materialTypeLabel
} from "../src/lib/materials.js";

test("material type helper accepts PRD Milestone 2 types only", () => {
  assert.deepEqual(
    MATERIAL_TYPE_OPTIONS.map((option) => option.value),
    ["text", "image", "audio", "video", "manual"]
  );
  assert.equal(materialTypeLabel("manual"), "手动资料");
  assert.equal(materialImportanceLabel("very_important"), "非常重要");
});

test("job status helper exposes PRD statuses", () => {
  assert.deepEqual(JOB_STATUSES, [
    "pending",
    "running",
    "succeeded",
    "failed",
    "retrying",
    "canceled"
  ]);
  assert.equal(jobStatusLabel("succeeded"), "已完成");
});

test("selected upload files include kind, type, and size labels", () => {
  const rows = describeSelectedUploadFiles({
    照片: [new File(["hello"], "grandma.png", { type: "image/png" })],
    文字: [new File([new Uint8Array(2048)], "story.md")]
  });

  assert.deepEqual(rows, [
    {
      kind: "照片",
      name: "grandma.png",
      typeLabel: "image/png",
      sizeLabel: "5 B"
    },
    {
      kind: "文字",
      name: "story.md",
      typeLabel: ".md",
      sizeLabel: "2.0 KB"
    }
  ]);
});

test("material helpers keep material-level importance optional for legacy only", () => {
  const source = readFileSync(new URL("../src/lib/materials.ts", import.meta.url), "utf8");

  assert.equal(source.includes("importance?: MaterialImportance"), true);
  assert.equal(source.includes("if (payload.importance)"), true);
  assert.equal(
    source.includes("export type UploadMaterialsPayload = {\n  files: File[];\n  importance: MaterialImportance;"),
    false
  );
  assert.equal(
    source.includes("export type ManualMaterialPayload = {\n  manual_text: string;\n  importance: MaterialImportance;"),
    false
  );
  assert.equal(source.includes("importance: payload.importance,"), false);
});

test("uploads memory audit actions are attached to each parsed memory card", () => {
  const source = readFileSync(
    new URL("../app/personas/[id]/uploads/page.tsx", import.meta.url),
    "utf8"
  );

  assert.equal(source.includes("onConfirm([memory.id])"), true);
  assert.equal(source.includes("onDelete([memory.id])"), true);
  assert.equal(source.includes("setEditingMemoryId(memory.id)"), true);
  assert.equal(source.includes("memories.slice(0, 3)"), false);
});

test("uploads page shows staged progress while submitting materials", () => {
  const source = readFileSync(
    new URL("../app/personas/[id]/uploads/page.tsx", import.meta.url),
    "utf8"
  );

  assert.equal(source.includes("type SubmitProgressStage"), true);
  assert.equal(source.includes("role=\"progressbar\""), true);
  assert.equal(source.includes("aria-live=\"polite\""), true);
  assert.equal(source.includes("正在上传资料..."), true);
  assert.equal(source.includes("正在保存手动资料..."), true);
  assert.equal(source.includes("正在解析资料并抽取记忆..."), true);
  assert.equal(source.includes("正在生成结构化记忆文档..."), true);
  assert.equal(source.includes("正在刷新审核结果..."), true);
});

test("uploads material card hides memory document provider diagnostics from users", () => {
  const source = readFileSync(
    new URL("../app/personas/[id]/uploads/page.tsx", import.meta.url),
    "utf8"
  );

  assert.equal(source.includes("materialJobError"), true);
  assert.equal(source.includes("materialStatusForUser"), true);
  assert.equal(source.includes("isMemoryDocumentProviderDiagnostic"), true);
  assert.equal(source.includes("memoryDocumentWarning"), false);
  assert.equal(source.includes("memory_document_error"), false);
  assert.equal(source.includes("MiniMax"), false);
  assert.equal(source.includes("strict JSON"), false);
});

test("uploads structured document is rendered from current memory cards", () => {
  const source = readFileSync(
    new URL("../app/personas/[id]/uploads/page.tsx", import.meta.url),
    "utf8"
  );

  assert.equal(source.includes("structuredMemoryMd = useMemo"), true);
  assert.equal(source.includes("renderStructuredMemoryMd(memories"), true);
  assert.equal(source.includes("latestStructuredMemoryMd(materials"), false);
});

test("uploads polls background parse jobs after material submission", () => {
  const source = readFileSync(
    new URL("../app/personas/[id]/uploads/page.tsx", import.meta.url),
    "utf8"
  );

  assert.equal(source.includes("pollMaterialJobs"), true);
  assert.equal(source.includes("BACKGROUND_PARSE_TERMINAL_STATUSES"), true);
  assert.equal(source.includes("资料已加入，后台解析中"), true);
});

test("uploads existing materials collapse after the first two cards", () => {
  const source = readFileSync(
    new URL("../app/personas/[id]/uploads/page.tsx", import.meta.url),
    "utf8"
  );

  assert.equal(source.includes("MATERIAL_PREVIEW_COUNT = 2"), true);
  assert.equal(source.includes("isMaterialsExpanded"), true);
  assert.equal(source.includes("visibleMaterials"), true);
  assert.equal(source.includes("materials.slice(0, MATERIAL_PREVIEW_COUNT)"), true);
  assert.equal(source.includes("aria-expanded={isMaterialsExpanded}"), true);
  assert.equal(source.includes('aria-controls="existing-materials-list"'), true);
  assert.equal(source.includes("展开全部"), true);
  assert.equal(source.includes("收起资料"), true);
});
