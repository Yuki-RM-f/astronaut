import { API_PATHS, buildApiUrl, readApiJson } from "./api";
import { authHeaders } from "./auth";

export type TrustLevel = "initial" | "usable" | "trusted" | "high_trust";

export type ProfileValue = Record<string, unknown> | unknown[];

export const PROFILE_DIMENSION_OPTIONS = [
  { value: "basic_facts", label: "基础事实" },
  { value: "relationships", label: "关系" },
  { value: "preferences", label: "偏好" },
  { value: "habits", label: "习惯" },
  { value: "expression_style", label: "表达风格" },
  { value: "shared_events", label: "共同经历" },
  { value: "values_json", label: "价值观" },
  { value: "emotional_patterns", label: "情绪模式" }
] as const;

export type ProfileDimension = (typeof PROFILE_DIMENSION_OPTIONS)[number]["value"];

export type ProfileDimensionEntry = {
  memory_id: string;
  title: string;
  content: string;
  category: string;
  confidence_level: string;
  status: string;
};

export type TrustComponent = {
  name: string;
  score: number;
  weight: number;
  weighted_score: number;
  evidence: string;
};

export type PersonaProfileRead = Record<ProfileDimension, ProfileValue> & {
  id: string;
  persona_id: string;
  profile_summary: string | null;
  source_memory_ids: Record<string, string[]>;
  trust_score: number;
  trust_level: string;
  components: TrustComponent[];
  suggestions: string[];
  created_at: string;
  updated_at: string;
};

export type PersonaProfileUpdate = Partial<
  Record<ProfileDimension, ProfileValue> & {
    profile_summary: string;
  }
>;

export function trustLevelForScore(score: number): TrustLevel {
  if (score <= 30) {
    return "initial";
  }
  if (score <= 60) {
    return "usable";
  }
  if (score <= 80) {
    return "trusted";
  }
  return "high_trust";
}

export function trustLevelLabel(level: string): string {
  const labels: Record<string, string> = {
    initial: "初始",
    usable: "可用",
    trusted: "可信",
    high_trust: "高可信"
  };

  return labels[level] ?? level;
}

export function profileDimensionLabel(dimension: string): string {
  return (
    PROFILE_DIMENSION_OPTIONS.find((option) => option.value === dimension)?.label ??
    dimension
  );
}

export function trustComponentLabel(name: string): string {
  const labels: Record<string, string> = {
    material_coverage: "资料覆盖",
    memory_review_rate: "记忆审核率",
    source_traceability: "来源可追溯",
    expression_habit_completeness: "表达与习惯完整度",
    multimodal_completeness: "多模态完整度"
  };

  return labels[name] ?? name;
}

export function primaryUploadSuggestion(suggestions: string[]): string | null {
  return suggestions.find((suggestion) => suggestion.trim().length > 0) ?? null;
}

export async function getPersonaProfile(
  personaId: string
): Promise<PersonaProfileRead> {
  const response = await fetch(buildApiUrl(API_PATHS.profile.detail(personaId)), {
    headers: authHeaders()
  });
  return readApiJson<PersonaProfileRead>(response, "无法加载人格档案。");
}

export async function updatePersonaProfile(
  personaId: string,
  payload: PersonaProfileUpdate
): Promise<PersonaProfileRead> {
  const response = await fetch(buildApiUrl(API_PATHS.profile.detail(personaId)), {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify(trimProfileUpdatePayload(payload))
  });
  return readApiJson<PersonaProfileRead>(response, "无法更新人格档案。");
}

export async function regeneratePersonaProfile(
  personaId: string
): Promise<PersonaProfileRead> {
  const response = await fetch(
    buildApiUrl(API_PATHS.profile.regenerate(personaId)),
    {
      method: "POST",
      headers: authHeaders()
    }
  );
  return readApiJson<PersonaProfileRead>(response, "无法重生成人格档案。");
}

export async function recalculateTrust(personaId: string): Promise<PersonaProfileRead> {
  const response = await fetch(
    buildApiUrl(API_PATHS.profile.recalculateTrust(personaId)),
    {
      method: "POST",
      headers: authHeaders()
    }
  );
  return readApiJson<PersonaProfileRead>(response, "无法重新计算可信度。");
}

function trimProfileUpdatePayload(
  payload: PersonaProfileUpdate
): PersonaProfileUpdate {
  return {
    ...payload,
    profile_summary: payload.profile_summary?.trim()
  };
}
