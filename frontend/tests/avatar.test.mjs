import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  AVATAR_FAILURE_NOTICE,
  avatarModelSummary,
  avatarStatusLabel,
  avatarStyleLabel,
  buildDefaultAvatarPayload,
  buildGenerateAvatarPayload,
  getAvatarDisplaySource,
  hasRenderableAvatarModel,
  hasUsablePreviewImage,
  personaAvatarRoute,
  shouldDriveAvatarMouth,
  shouldShowChatAvatar,
  uploadAvatarModel
} from "../src/lib/avatar.js";
import { API_PATHS } from "../src/lib/api.js";

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
  assert.equal(avatarStatusLabel("uploaded_ready"), "GLB 模型已上传");
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
    provider_type: "user_upload",
    provider_name: "glb_upload",
    status: "uploaded_ready",
    source_image_material_id: null,
    style: null,
    model_url: "/api/avatar-models/a1/file",
    preview_image_url: null,
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
    "GLB 模型已上传 · glb · glb_upload"
  );
});

test("avatar upload API path and helper send a GLB file as form data", async () => {
  const originalFetch = globalThis.fetch;
  const originalWindow = globalThis.window;
  const calls = [];
  globalThis.window = {
    localStorage: {
      getItem: () => "token-1",
      setItem: () => {},
      removeItem: () => {}
    }
  };
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return new Response(
      JSON.stringify({
        persona_id: "p1",
        avatar_status: "uploaded_ready",
        selected_avatar_model: null,
        avatar_models: [],
        style_options: ["memorial"],
        failure_notice: AVATAR_FAILURE_NOTICE
      }),
      { status: 201, headers: { "Content-Type": "application/json" } }
    );
  };

  try {
    const file = new File(["glb"], "waipo.glb", { type: "model/gltf-binary" });
    const result = await uploadAvatarModel("p1", file);

    assert.equal(API_PATHS.avatar.upload("p1"), "/api/personas/p1/avatar/upload");
    assert.equal(API_PATHS.avatar.file("a1"), "/api/avatar-models/a1/file");
    assert.equal(calls[0].url, "http://localhost:8000/api/personas/p1/avatar/upload");
    assert.equal(calls[0].init.method, "POST");
    assert.equal(calls[0].init.headers.Authorization, "Bearer token-1");
    assert.equal(calls[0].init.body instanceof FormData, true);
    assert.equal(calls[0].init.body.get("file"), file);
    assert.equal(result.avatar_status, "uploaded_ready");
  } finally {
    globalThis.fetch = originalFetch;
    globalThis.window = originalWindow;
  }
});

test("chat avatar renders only when a selected model is loadable", () => {
  const config = {
    persona_id: "p1",
    avatar_status: "uploaded_ready",
    selected_avatar_model: {
      id: "a1",
      persona_id: "p1",
      provider_type: "user_upload",
      provider_name: "glb_upload",
      status: "uploaded_ready",
      source_image_material_id: null,
      style: null,
      model_url: "/api/avatar-models/a1/file",
      preview_image_url: null,
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

test("chat avatar display source prefers renderable models then usable preview images", () => {
  const selectedModel = {
    id: "a1",
    persona_id: "p1",
    provider_type: "user_upload",
    provider_name: "glb_upload",
    status: "uploaded_ready",
    source_image_material_id: null,
    style: null,
    model_url: "/api/avatar-models/a1/file",
    preview_image_url: "/avatar-preview.png",
    format: "glb",
    expression_config_json: null,
    animation_config_json: null,
    lip_sync_config_json: null,
    user_selected: true,
    created_at: "2026-07-04T00:00:00",
    updated_at: "2026-07-04T00:00:00"
  };
  const config = {
    persona_id: "p1",
    avatar_status: "uploaded_ready",
    selected_avatar_model: selectedModel,
    avatar_models: [],
    style_options: ["memorial"],
    failure_notice: AVATAR_FAILURE_NOTICE
  };

  assert.equal(hasUsablePreviewImage("/avatar-preview.png"), true);
  assert.equal(hasUsablePreviewImage("https://example.test/avatar.png"), true);
  assert.equal(hasUsablePreviewImage("mock://avatar-preview/p1.png"), false);
  assert.equal(
    hasRenderableAvatarModel({ ...selectedModel, model_url: "mock://avatar/default/memorial.glb" }),
    false
  );
  assert.deepEqual(getAvatarDisplaySource(config), {
    kind: "model",
    model: selectedModel,
    previewImageUrl: null
  });
  assert.deepEqual(
    getAvatarDisplaySource({
      ...config,
      selected_avatar_model: {
        ...selectedModel,
        model_url: "",
        preview_image_url: "https://example.test/avatar.png"
      }
    }),
    {
      kind: "preview",
      model: null,
      previewImageUrl: "https://example.test/avatar.png"
    }
  );
  assert.deepEqual(
    getAvatarDisplaySource({
      ...config,
      selected_avatar_model: {
        ...selectedModel,
        model_url: "",
        preview_image_url: "mock://avatar-preview/p1.png"
      }
    }),
    { kind: "placeholder", model: null, previewImageUrl: null }
  );
});

test("uploaded GLB model is the preferred display source", () => {
  const selectedModel = {
    id: "a1",
    persona_id: "p1",
    provider_type: "user_upload",
    provider_name: "glb_upload",
    status: "uploaded_ready",
    source_image_material_id: null,
    style: null,
    model_url: "/api/avatar-models/a1/file",
    preview_image_url: null,
    format: "glb",
    expression_config_json: null,
    animation_config_json: null,
    lip_sync_config_json: null,
    user_selected: true,
    created_at: "2026-07-05T00:00:00",
    updated_at: "2026-07-05T00:00:00"
  };

  assert.equal(hasRenderableAvatarModel(selectedModel), true);
  assert.deepEqual(
    getAvatarDisplaySource({
      persona_id: "p1",
      avatar_status: "uploaded_ready",
      selected_avatar_model: selectedModel,
      avatar_models: [selectedModel],
      style_options: ["memorial"],
      failure_notice: AVATAR_FAILURE_NOTICE
    }),
    { kind: "model", model: selectedModel, previewImageUrl: null }
  );
});

test("avatar page exposes only the GLB upload flow", () => {
  const source = readFileSync(
    new URL("../app/personas/[id]/avatar/page.tsx", import.meta.url),
    "utf8"
  );

  assert.match(source, /上传 GLB 模型/);
  assert.match(source, /模型加载中/);
  assert.match(source, /模型加载失败/);
  assert.match(source, /uploadAvatarModel/);
  assert.equal(source.includes("选择默认纪念形象"), false);
  assert.equal(source.includes("图片生成"), false);
  assert.equal(source.includes("生成 mock 3D 形象"), false);
  assert.equal(source.includes("动作与口型"), false);
  assert.equal(source.includes("buildGenerateAvatarPayload"), false);
  assert.equal(source.includes("listMaterials"), false);
});

test("shared avatar stage uses the GLB loader for model cards", () => {
  const previewSource = readFileSync(
    new URL("../src/components/AvatarPreview.tsx", import.meta.url),
    "utf8"
  );
  const stageSource = readFileSync(
    new URL("../src/components/AvatarStage.tsx", import.meta.url),
    "utf8"
  );

  assert.match(previewSource, /GLTFLoader/);
  assert.match(previewSource, /MeshoptDecoder/);
  assert.match(previewSource, /setRequestHeader/);
  assert.match(previewSource, /setMeshoptDecoder/);
  assert.match(previewSource, /AnimationMixer/);
  assert.match(previewSource, /selectAvatarAnimationClipName/);
  assert.match(previewSource, /motionIntent/);
  assert.match(previewSource, /applyFallbackMotion/);
  assert.match(previewSource, /camera\.position\.set\(0, 0\.65, 5\.2\)/);
  assert.match(previewSource, /targetModelSize = 3\.15/);
  assert.match(previewSource, /模型加载中/);
  assert.match(previewSource, /模型加载失败/);
  assert.match(stageSource, /AvatarPreview/);
  assert.match(stageSource, /motionIntent/);
  assert.match(stageSource, /motionIntent=\{motionIntent\}/);
  assert.equal(stageSource.includes("right-[7%] top-[8%] h-56 w-56 rounded-full"), false);
  assert.equal(stageSource.includes("默认星空形象"), false);
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
