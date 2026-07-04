import assert from "node:assert/strict";
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
