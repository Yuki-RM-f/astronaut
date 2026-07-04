import assert from "node:assert/strict";
import test from "node:test";
import { JOB_STATUSES, jobStatusLabel } from "../src/lib/jobs.js";
import {
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
