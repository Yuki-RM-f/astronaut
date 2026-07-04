import { API_PATHS, buildApiUrl, readApiJson } from "./api";
import { authHeaders } from "./auth";

export const MEMORY_STATUS_OPTIONS = [
  { value: "pending_review", label: "待审核" },
  { value: "confirmed", label: "已确认" },
  { value: "corrected", label: "已修正" },
  { value: "rejected", label: "已拒绝" },
  { value: "disabled", label: "已停用" },
  { value: "auto_generated", label: "自动生成" }
] as const;

export const MEMORY_CATEGORY_OPTIONS = [
  { value: "basic_fact", label: "基础事实" },
  { value: "relationship", label: "关系" },
  { value: "preference", label: "偏好" },
  { value: "habit", label: "习惯" },
  { value: "expression_style", label: "表达风格" },
  { value: "shared_event", label: "共同经历" },
  { value: "value", label: "价值观" },
  { value: "emotional_pattern", label: "情绪模式" },
  { value: "story_material", label: "故事素材" },
  { value: "unknown", label: "未知" }
] as const;

export const MEMORY_CONFIDENCE_OPTIONS = [
  { value: "high", label: "高" },
  { value: "medium", label: "中" },
  { value: "low", label: "低" }
] as const;

export const MEMORY_SOURCE_TYPE_OPTIONS = [
  { value: "text", label: "文本" },
  { value: "image", label: "图片" },
  { value: "audio", label: "音频" },
  { value: "video", label: "视频" },
  { value: "manual", label: "手动资料" }
] as const;

export type MemoryStatus = (typeof MEMORY_STATUS_OPTIONS)[number]["value"];
export type MemoryCategory = (typeof MEMORY_CATEGORY_OPTIONS)[number]["value"];
export type MemoryConfidenceLevel =
  (typeof MEMORY_CONFIDENCE_OPTIONS)[number]["value"];
export type MemorySourceType = (typeof MEMORY_SOURCE_TYPE_OPTIONS)[number]["value"];

export type MemoryRead = {
  id: string;
  persona_id: string;
  title: string;
  content: string;
  category: MemoryCategory;
  confidence_level: MemoryConfidenceLevel;
  confidence_score: number;
  source_material_id: string | null;
  parsed_chunk_id: string | null;
  source_type: MemorySourceType | null;
  source_quote: string | null;
  source_location: string | null;
  evidence_json: Record<string, unknown> | unknown[] | null;
  status: MemoryStatus;
  is_important: boolean;
  user_correction: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
};

type MemoryListResponse = {
  items: MemoryRead[];
};

export type MemoryListFilters = {
  status?: MemoryStatus;
  category?: MemoryCategory;
  confidence_level?: MemoryConfidenceLevel;
};

export type MemoryUpdatePayload = Partial<{
  title: string;
  content: string;
  category: MemoryCategory;
  confidence_level: MemoryConfidenceLevel;
  confidence_score: number;
  status: MemoryStatus;
  is_important: boolean;
}>;

export type DimensionAction = "confirm" | "delete" | "update";

export function memoryStatusLabel(value: MemoryStatus): string {
  return MEMORY_STATUS_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

export function memoryCategoryLabel(value: MemoryCategory): string {
  return MEMORY_CATEGORY_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

export function memoryConfidenceLabel(value: MemoryConfidenceLevel): string {
  return (
    MEMORY_CONFIDENCE_OPTIONS.find((option) => option.value === value)?.label ?? value
  );
}

export function memorySourceTypeLabel(value: MemorySourceType | null): string {
  if (!value) {
    return "未知";
  }

  return (
    MEMORY_SOURCE_TYPE_OPTIONS.find((option) => option.value === value)?.label ?? value
  );
}

export function canUseMemoryInConversation(status: MemoryStatus): boolean {
  return status === "confirmed" || status === "corrected";
}

export function selectDimensionActionTargets(
  memories: Array<Pick<MemoryRead, "id" | "status">>,
  action: DimensionAction
): string[] {
  if (action === "delete") {
    return memories.map((memory) => memory.id);
  }
  if (action === "update") {
    return memories[0]?.id ? [memories[0].id] : [];
  }
  return memories
    .filter((memory) => !["confirmed", "corrected", "rejected", "disabled"].includes(memory.status))
    .map((memory) => memory.id);
}

export async function listMemories(
  personaId: string,
  filters: MemoryListFilters = {}
): Promise<MemoryRead[]> {
  const query = new URLSearchParams();
  if (filters.status) {
    query.set("status", filters.status);
  }
  if (filters.category) {
    query.set("category", filters.category);
  }
  if (filters.confidence_level) {
    query.set("confidence_level", filters.confidence_level);
  }

  const path = API_PATHS.memories.list(personaId);
  const url = query.size > 0 ? `${path}?${query.toString()}` : path;
  const response = await fetch(buildApiUrl(url), {
    headers: authHeaders()
  });
  const data = await readApiJson<MemoryListResponse>(
    response,
    "无法加载记忆。"
  );
  return data.items;
}

export async function confirmMemory(id: string): Promise<MemoryRead> {
  const response = await fetch(buildApiUrl(API_PATHS.memories.confirm(id)), {
    method: "POST",
    headers: authHeaders()
  });
  return readApiJson<MemoryRead>(response, "无法确认记忆。");
}

export async function rejectMemory(id: string): Promise<MemoryRead> {
  const response = await fetch(buildApiUrl(API_PATHS.memories.reject(id)), {
    method: "POST",
    headers: authHeaders()
  });
  return readApiJson<MemoryRead>(response, "无法拒绝记忆。");
}

export async function disableMemory(id: string): Promise<MemoryRead> {
  const response = await fetch(buildApiUrl(API_PATHS.memories.disable(id)), {
    method: "POST",
    headers: authHeaders()
  });
  return readApiJson<MemoryRead>(response, "无法停用记忆。");
}

export async function updateMemory(
  id: string,
  payload: MemoryUpdatePayload
): Promise<MemoryRead> {
  const response = await fetch(buildApiUrl(API_PATHS.memories.detail(id)), {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify(trimUpdatePayload(payload))
  });
  return readApiJson<MemoryRead>(response, "无法更新记忆。");
}

export async function deleteMemory(id: string): Promise<void> {
  const response = await fetch(buildApiUrl(API_PATHS.memories.detail(id)), {
    method: "DELETE",
    headers: authHeaders()
  });

  if (!response.ok) {
    await readApiJson<never>(response, "无法删除记忆。");
  }
}

function trimUpdatePayload(payload: MemoryUpdatePayload): MemoryUpdatePayload {
  return {
    ...payload,
    title: payload.title?.trim(),
    content: payload.content?.trim()
  };
}
