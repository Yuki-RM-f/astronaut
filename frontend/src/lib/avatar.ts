import { API_PATHS, buildApiUrl, readApiJson } from "./api";
import { authHeaders } from "./auth";
import { ROUTES } from "./routes";

export const AVATAR_FAILURE_NOTICE =
  "这张照片暂时没有生成成功。你可以换一张更清晰的正脸照，或者先使用默认纪念形象继续对话。";

export type AvatarStatus =
  | "no_avatar"
  | "default_avatar"
  | "uploaded_ready"
  | "generating"
  | "generated_ready"
  | "generation_failed";

export type AvatarStyle = "semi_realistic" | "cartoon" | "memorial";

export type AvatarModelRead = {
  id: string;
  persona_id: string;
  provider_type: string | null;
  provider_name: string | null;
  status: string | null;
  source_image_material_id: string | null;
  style: string | null;
  model_url: string | null;
  preview_image_url: string | null;
  format: string | null;
  expression_config_json: Record<string, unknown> | unknown[] | null;
  animation_config_json: Record<string, unknown> | unknown[] | null;
  lip_sync_config_json: Record<string, unknown> | unknown[] | null;
  user_selected: boolean;
  created_at: string;
  updated_at: string;
};

export type AvatarConfigResponse = {
  persona_id: string;
  avatar_status: AvatarStatus;
  selected_avatar_model: AvatarModelRead | null;
  avatar_models: AvatarModelRead[];
  style_options: AvatarStyle[];
  failure_notice: string;
};

export type DefaultAvatarPayload = {
  style: AvatarStyle;
};

export type GenerateAvatarPayload = {
  source_image_material_id: string;
  style: AvatarStyle;
};

export type AvatarJobRead = {
  id: string;
  job_type: string;
  status: string;
};

export type AvatarGenerateResponse = {
  avatar_status: AvatarStatus;
  avatar_model: AvatarModelRead;
  selected_avatar_model: AvatarModelRead;
  failure_notice: string;
  provider: Record<string, string>;
  job: AvatarJobRead;
};

export const AVATAR_API_PATHS = API_PATHS.avatar;

export type AvatarDisplaySource =
  | { kind: "model"; model: AvatarModelRead; previewImageUrl: null }
  | { kind: "preview"; model: null; previewImageUrl: string }
  | { kind: "placeholder"; model: null; previewImageUrl: null };

export function personaAvatarRoute(personaId: string): string {
  return ROUTES.personaAvatar(personaId);
}

export function buildDefaultAvatarPayload(style: AvatarStyle = "memorial"): DefaultAvatarPayload {
  return { style };
}

export function buildGenerateAvatarPayload(
  sourceImageMaterialId: string,
  style: AvatarStyle = "semi_realistic"
): GenerateAvatarPayload {
  return {
    source_image_material_id: sourceImageMaterialId,
    style
  };
}

export function avatarStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case "no_avatar":
      return "未设置形象";
    case "default_avatar":
      return "默认纪念形象";
    case "uploaded_ready":
      return "GLB 模型已上传";
    case "generating":
      return "3D 生成中";
    case "generated_ready":
      return "3D 形象可用";
    case "generation_failed":
      return "3D 生成失败";
    default:
      return status || "未知状态";
  }
}

export function avatarStyleLabel(style: string | null | undefined): string {
  switch (style) {
    case "semi_realistic":
      return "温柔半写实";
    case "cartoon":
      return "卡通";
    case "memorial":
      return "简洁纪念风";
    default:
      return style || "未设置";
  }
}

export function hasRenderableAvatarModel(
  model: AvatarModelRead | null | undefined
): boolean {
  return Boolean(model?.model_url?.trim() && model.format === "glb" && resolveAvatarModelUrl(model));
}

export function hasUsablePreviewImage(value: string | null | undefined): boolean {
  const url = value?.trim();
  if (!url) {
    return false;
  }
  return (
    url.startsWith("/") ||
    url.startsWith("https://") ||
    url.startsWith("http://") ||
    url.startsWith("data:image/")
  );
}

export function getAvatarDisplaySource(
  config: AvatarConfigResponse | null | undefined
): AvatarDisplaySource {
  const selectedModel = config?.selected_avatar_model;
  if (selectedModel && hasRenderableAvatarModel(selectedModel)) {
    return { kind: "model", model: selectedModel, previewImageUrl: null };
  }
  const previewImageUrl = selectedModel?.preview_image_url?.trim();
  if (previewImageUrl && hasUsablePreviewImage(previewImageUrl)) {
    return {
      kind: "preview",
      model: null,
      previewImageUrl
    };
  }
  return { kind: "placeholder", model: null, previewImageUrl: null };
}

export function resolveAvatarModelUrl(model: AvatarModelRead | null | undefined): string | null {
  const rawUrl = model?.model_url?.trim();
  if (!rawUrl || model?.format !== "glb") {
    return null;
  }
  if (rawUrl.startsWith("/api/")) {
    return buildApiUrl(rawUrl);
  }
  if (rawUrl.startsWith("http://") || rawUrl.startsWith("https://")) {
    return rawUrl;
  }
  return null;
}

export function shouldShowChatAvatar(
  config: AvatarConfigResponse | null | undefined
): boolean {
  return getAvatarDisplaySource(config).kind !== "placeholder";
}

export function shouldDriveAvatarMouth(
  message: { id: string; role: string; audio_url?: string | null },
  playingMessageId: string | null
): boolean {
  return (
    message.role === "persona" &&
    message.id === playingMessageId &&
    Boolean(message.audio_url?.trim())
  );
}

export function avatarModelSummary(model: AvatarModelRead): string {
  const parts = [
    avatarStatusLabel(model.status),
    model.style ? avatarStyleLabel(model.style) : null,
    model.format,
    model.provider_name
  ].filter(Boolean);
  return parts.join(" · ");
}

export async function getAvatarConfig(personaId: string): Promise<AvatarConfigResponse> {
  const response = await fetch(buildApiUrl(AVATAR_API_PATHS.config(personaId)), {
    headers: authHeaders()
  });
  return readApiJson<AvatarConfigResponse>(response, "无法加载形象配置。");
}

export async function selectDefaultAvatar(
  personaId: string,
  payload: DefaultAvatarPayload = buildDefaultAvatarPayload()
): Promise<AvatarConfigResponse> {
  const response = await fetch(buildApiUrl(AVATAR_API_PATHS.defaultAvatar(personaId)), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload)
  });
  return readApiJson<AvatarConfigResponse>(response, "无法选择默认形象。");
}

export async function generateAvatar(
  personaId: string,
  payload: GenerateAvatarPayload
): Promise<AvatarGenerateResponse> {
  const response = await fetch(buildApiUrl(AVATAR_API_PATHS.generate(personaId)), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload)
  });
  return readApiJson<AvatarGenerateResponse>(response, "无法生成 3D 形象。");
}

export async function uploadAvatarModel(
  personaId: string,
  file: File
): Promise<AvatarConfigResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(buildApiUrl(AVATAR_API_PATHS.upload(personaId)), {
    method: "POST",
    headers: authHeaders(),
    body: formData
  });
  return readApiJson<AvatarConfigResponse>(response, "无法上传 GLB 模型。");
}
