import { API_PATHS, buildApiUrl, readApiJson } from "./api";
import { authHeaders } from "./auth";
import type { AIJobRead, AIJobStatus } from "./jobs";

export const MATERIAL_TYPE_OPTIONS = [
  { value: "text", label: "文本" },
  { value: "image", label: "图片" },
  { value: "audio", label: "音频" },
  { value: "video", label: "视频" },
  { value: "manual", label: "手动资料" }
] as const;

export const MATERIAL_IMPORTANCE_OPTIONS = [
  { value: "normal", label: "普通" },
  { value: "important", label: "重要" },
  { value: "very_important", label: "非常重要" }
] as const;

export type MaterialType = (typeof MATERIAL_TYPE_OPTIONS)[number]["value"];
export type MaterialImportance = (typeof MATERIAL_IMPORTANCE_OPTIONS)[number]["value"];

export type SourceMaterialRead = {
  id: string;
  persona_id: string;
  file_name: string | null;
  file_type: MaterialType;
  mime_type: string | null;
  file_size: number | null;
  storage_url: string | null;
  manual_text: string | null;
  user_description: string | null;
  material_time: string | null;
  people_tags: Record<string, unknown> | unknown[] | null;
  location_hint: string | null;
  importance: MaterialImportance;
  parse_status: AIJobStatus;
  created_at: string;
  updated_at: string;
  jobs: AIJobRead[];
};

type MaterialListResponse = {
  items: SourceMaterialRead[];
};

export type UploadMaterialsPayload = {
  files: File[];
  importance: MaterialImportance;
  user_description?: string;
};

export type ManualMaterialPayload = {
  manual_text: string;
  importance: MaterialImportance;
  user_description?: string;
};

export function materialTypeLabel(value: MaterialType): string {
  return MATERIAL_TYPE_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

export function materialImportanceLabel(value: MaterialImportance): string {
  return (
    MATERIAL_IMPORTANCE_OPTIONS.find((option) => option.value === value)?.label ?? value
  );
}

export async function listMaterials(personaId: string): Promise<SourceMaterialRead[]> {
  const response = await fetch(buildApiUrl(API_PATHS.materials.list(personaId)), {
    headers: authHeaders()
  });
  const data = await readApiJson<MaterialListResponse>(
    response,
    "无法加载资料。"
  );
  return data.items;
}

export async function uploadMaterials(
  personaId: string,
  payload: UploadMaterialsPayload
): Promise<SourceMaterialRead[]> {
  const formData = new FormData();
  payload.files.forEach((file) => formData.append("files", file));
  formData.append("importance", payload.importance);

  const description = payload.user_description?.trim();
  if (description) {
    formData.append("user_description", description);
  }

  const response = await fetch(buildApiUrl(API_PATHS.materials.upload(personaId)), {
    method: "POST",
    headers: authHeaders(),
    body: formData
  });
  const data = await readApiJson<MaterialListResponse>(
    response,
    "无法上传资料。"
  );
  return data.items;
}

export async function createManualMaterial(
  personaId: string,
  payload: ManualMaterialPayload
): Promise<SourceMaterialRead> {
  const description = payload.user_description?.trim();
  const response = await fetch(buildApiUrl(API_PATHS.materials.manual(personaId)), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify({
      manual_text: payload.manual_text.trim(),
      importance: payload.importance,
      user_description: description || null
    })
  });
  return readApiJson<SourceMaterialRead>(response, "无法创建手动资料。");
}
