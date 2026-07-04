import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

async function loadPersonaModule() {
  try {
    return await import("../src/lib/persona.js");
  } catch (error) {
    assert.fail(`Expected persona helpers to be exported: ${error.message}`);
  }
}

test("persona form validation requires PRD Milestone 1 fields", async () => {
  const { validatePersonaDraft } = await loadPersonaModule();

  const result = validatePersonaDraft({
    name: "",
    persona_type: "deceased_relative"
  });

  assert.equal(result.ok, false);
  assert.ok(result.missingFields.includes("name"));
  assert.ok(result.missingFields.includes("age"));
  assert.ok(result.missingFields.includes("user_nickname_by_persona"));
});

test("persona form validation accepts PRD age as a numeric required field", async () => {
  const { validatePersonaDraft } = await loadPersonaModule();

  const result = validatePersonaDraft({
    name: "外婆",
    persona_type: "deceased_relative",
    status: "deceased",
    relationship_to_user: "外婆",
    user_nickname_by_persona: "小铭",
    age: 72,
    gender: "female",
    short_bio: "她很温柔，喜欢做饭。"
  });

  assert.deepEqual(result, { ok: true, missingFields: [] });
});

test("persona create payload uses fixed Chinese and default style boundaries", async () => {
  const { buildPersonaCreatePayload } = await loadPersonaModule();

  const payload = buildPersonaCreatePayload({
    name: " 外婆 ",
    persona_type: "deceased_relative",
    status: "deceased",
    relationship_to_user: " 外婆 ",
    user_nickname_by_persona: " 小铭 ",
    age: "72",
    gender: "female",
    short_bio: " 她很温柔，喜欢做饭。 "
  });

  assert.equal(payload.language, "zh-CN");
  assert.equal(payload.speaking_style, "温和、自然，优先使用用户定义的称呼。");
  assert.equal(payload.emotional_style, "安慰、鼓励、陪伴，但不替用户做重大决定。");
  assert.equal(payload.forbidden_expressions, "不要说「我真的回来了」；不要暗示自己是本人复生。");
  assert.equal(payload.short_bio, "她很温柔，喜欢做饭。");
  assert.equal(payload.age, 72);
});

test("creation page bio uses the broad TA details prefix", async () => {
  const { buildCreatePersonaShortBio } = await loadPersonaModule();

  const bio = buildCreatePersonaShortBio({
    birthDate: "1949-10-01",
    message: "喜欢晒太阳，也总是说慢慢来。"
  });

  assert.equal(
    bio,
    "1949-10-01 出生\n有关TA的一切：喜欢晒太阳，也总是说慢慢来。\n由星记创建的专属星星。"
  );
});

test("creation submit progress maps stages to labels and percentages", async () => {
  const { buildCreatePersonaProgress } = await loadPersonaModule();

  assert.deepEqual(buildCreatePersonaProgress("demo_session", 4), {
    label: "正在准备演示会话...",
    percent: 20
  });
  assert.deepEqual(buildCreatePersonaProgress("upload_memories", 4), {
    label: "正在上传 4 个回忆文件...",
    percent: 75
  });
  assert.deepEqual(buildCreatePersonaProgress("review_entry", 4), {
    label: "正在进入资料审核...",
    percent: 95
  });
});

test("creation page routes created personas to uploads review", () => {
  const source = readFileSync(new URL("../app/personas/new/page.tsx", import.meta.url), "utf8");

  assert.equal(source.includes("ROUTES.personaUploads(created.id)"), true);
  assert.equal(source.includes("ROUTES.personaMemories(created.id)"), false);
});

test("persona detail overview shows only user-entered basic facts", () => {
  const source = readFileSync(new URL("../app/personas/[id]/page.tsx", import.meta.url), "utf8");
  const overviewStart = source.indexOf("资料概览");
  const overviewEnd = source.indexOf("</StarPanel>", overviewStart);
  const overviewSource = source.slice(overviewStart, overviewEnd);

  assert.notEqual(overviewStart, -1);
  assert.notEqual(overviewEnd, -1);
  assert.equal(source.includes("人格设定"), false);
  assert.equal(overviewSource.includes("基础信息"), true);

  for (const label of ["年龄", "你们的关系", "TA 对你的称呼"]) {
    assert.equal(overviewSource.includes(label), true, label);
  }

  for (const defaultOnlyLabel of ["说话风格", "情绪方式", "禁止表达"]) {
    assert.equal(overviewSource.includes(defaultOnlyLabel), false, defaultOnlyLabel);
  }
});

test("persona detail hero uses profile summary instead of short bio", () => {
  const source = readFileSync(new URL("../app/personas/[id]/page.tsx", import.meta.url), "utf8");

  assert.equal(source.includes("profile.profile_summary"), true);
  assert.equal(source.includes("档案摘要将在新的资料上传解析后自动生成。"), true);
  assert.equal(source.includes("persona.short_bio"), false);
});

test("persona detail does not render the next-step suggestion card", () => {
  const source = readFileSync(new URL("../app/personas/[id]/page.tsx", import.meta.url), "utf8");

  assert.equal(source.includes("下一步建议"), false);
  assert.equal(source.includes("primaryAction.description"), false);
  assert.equal(source.includes("<Link href={primaryAction.href} className=\"star-button gap-2\">"), true);
});

test("reserved expert role is not a create option", async () => {
  const { PERSONA_TYPE_OPTIONS } = await loadPersonaModule();

  assert.deepEqual(
    PERSONA_TYPE_OPTIONS.map((option) => option.value),
    ["deceased_relative", "living_relative", "public_figure", "fictional_character"]
  );
  assert.deepEqual(
    PERSONA_TYPE_OPTIONS.map((option) => option.label),
    ["已故亲友", "在世亲友", "公众人物", "虚拟角色"]
  );
});
