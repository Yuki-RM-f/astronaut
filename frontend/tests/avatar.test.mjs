import assert from "node:assert/strict";
import test from "node:test";
import {
  AVATAR_FAILURE_NOTICE,
  avatarModelSummary,
  avatarStatusLabel,
  avatarStyleLabel,
  buildDefaultAvatarPayload,
  buildGenerateAvatarPayload,
  hasRenderableAvatarModel,
  personaAvatarRoute,
  shouldDriveAvatarMouth,
  shouldShowChatAvatar
} from "../src/lib/avatar.js";

test("avatar route follows Milestone 7 contract", () => {
  assert.equal(personaAvatarRoute("p1"), "/personas/p1/avatar");
});

test("avatar failure notice matches PRD copy exactly", () => {
  assert.equal(
    AVATAR_FAILURE_NOTICE,
    "这张照片暂时没有生成成功。你可以换一张更清晰的正脸照，或者先使用默认纪念形象继续对话。"
  );
});

test("avatar status and style labels expose PRD states", () => {
  assert.equal(avatarStatusLabel("no_avatar"), "未设置形象");
  assert.equal(avatarStatusLabel("default_avatar"), "默认纪念形象");
  assert.equal(avatarStatusLabel("generated_ready"), "3D 形象可用");
  assert.equal(avatarStatusLabel("generation_failed"), "3D 生成失败");
  assert.equal(avatarStyleLabel("semi_realistic"), "温柔半写实");
  assert.equal(avatarStyleLabel("cartoon"), "卡通");
  assert.equal(avatarStyleLabel("memorial"), "简洁纪念风");
});

test("avatar payload helpers preserve PRD defaults", () => {
  assert.deepEqual(buildDefaultAvatarPayload(), { style: "memorial" });
  assert.deepEqual(buildGenerateAvatarPayload("mat1", "cartoon"), {
    source_image_material_id: "mat1",
    style: "cartoon"
  });
});

test("avatar model summary and renderability use model facts only", () => {
  const model = {
    id: "a1",
    persona_id: "p1",
    provider_type: "local",
    provider_name: "mock_avatar_3d",
    status: "generated_ready",
    source_image_material_id: "mat1",
    style: "semi_realistic",
    model_url: "mock://avatar-model/p1/job1.glb",
    preview_image_url: "mock://avatar-preview/p1/job1.png",
    format: "glb",
    expression_config_json: { smile: true },
    animation_config_json: { idle_breath: true },
    lip_sync_config_json: { mode: "audio_envelope" },
    user_selected: true,
    created_at: "2026-07-04T00:00:00",
    updated_at: "2026-07-04T00:00:00"
  };

  assert.equal(hasRenderableAvatarModel(model), true);
  assert.equal(
    avatarModelSummary(model),
    "3D 形象可用 · 温柔半写实 · glb · mock_avatar_3d"
  );
});

test("chat avatar renders only when a selected model is loadable", () => {
  const config = {
    persona_id: "p1",
    avatar_status: "generated_ready",
    selected_avatar_model: {
      id: "a1",
      persona_id: "p1",
      provider_type: "mock",
      provider_name: "mock_avatar_3d",
      status: "generated_ready",
      source_image_material_id: "mat1",
      style: "memorial",
      model_url: "mock://avatar/default/memorial.glb",
      preview_image_url: "mock://avatar/default/memorial.png",
      format: "glb",
      expression_config_json: null,
      animation_config_json: null,
      lip_sync_config_json: null,
      user_selected: true,
      created_at: "2026-07-04T00:00:00",
      updated_at: "2026-07-04T00:00:00"
    },
    avatar_models: [],
    style_options: ["memorial"],
    failure_notice: AVATAR_FAILURE_NOTICE
  };

  assert.equal(shouldShowChatAvatar(config), true);
  assert.equal(
    shouldShowChatAvatar({
      ...config,
      selected_avatar_model: { ...config.selected_avatar_model, model_url: " " }
    }),
    false
  );
  assert.equal(shouldShowChatAvatar({ ...config, selected_avatar_model: null }), false);
});

test("avatar mouth is driven only by the currently playing persona audio message", () => {
  const message = {
    id: "m1",
    conversation_id: "c1",
    role: "persona",
    content: "小铭，我在。",
    audio_url: "mock://tts/m1.wav",
    metadata_json: null,
    created_at: "2026-07-04T00:00:00",
    citations: []
  };

  assert.equal(shouldDriveAvatarMouth(message, "m1"), true);
  assert.equal(shouldDriveAvatarMouth({ ...message, role: "user" }, "m1"), false);
  assert.equal(shouldDriveAvatarMouth({ ...message, audio_url: null }, "m1"), false);
  assert.equal(shouldDriveAvatarMouth(message, "m2"), false);
  assert.equal(shouldDriveAvatarMouth(message, null), false);
});
