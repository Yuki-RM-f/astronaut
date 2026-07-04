import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  profileDimensionLabel,
  trustLevelForScore,
  trustLevelLabel
} from "../src/lib/profile.js";

test("trust level helper follows PRD score bands", () => {
  assert.equal(trustLevelForScore(0), "initial");
  assert.equal(trustLevelForScore(31), "usable");
  assert.equal(trustLevelForScore(61), "trusted");
  assert.equal(trustLevelForScore(81), "high_trust");
  assert.equal(trustLevelLabel("trusted"), "可信");
  assert.equal(trustLevelLabel("high_trust"), "高可信");
});

test("profile dimension labels cover PRD dimensions", () => {
  assert.equal(profileDimensionLabel("basic_facts"), "基础事实");
  assert.equal(profileDimensionLabel("emotional_patterns"), "情绪模式");
});

test("profile page redirects to uploads instead of rendering profile UI", () => {
  const source = readFileSync(
    new URL("../app/personas/[id]/profile/page.tsx", import.meta.url),
    "utf8"
  );

  assert.equal(source.includes("redirect("), true);
  assert.equal(source.includes("ROUTES.personaUploads"), true);
  assert.equal(source.includes("档案摘要"), false);
  assert.equal(source.includes("JSON 值"), false);
  assert.equal(source.includes("PROFILE_DIMENSION_OPTIONS"), false);
});
