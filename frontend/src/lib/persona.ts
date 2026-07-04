import { API_PATHS, buildApiUrl, readApiJson } from "./api";
import { authHeaders } from "./auth";

export const PERSONA_TYPE_OPTIONS = [
  { value: "deceased_relative", label: "已故亲友" },
  { value: "living_relative", label: "在世亲友" },
  { value: "public_figure", label: "公众人物" },
  { value: "fictional_character", label: "虚拟角色" }
] as const;

export const PERSONA_STATUS_OPTIONS = [
  { value: "deceased", label: "已故" },
  { value: "living", label: "在世" },
  { value: "public", label: "公众人物" },
  { value: "fictional", label: "虚拟角色" }
] as const;

export const PERSONA_GENDER_OPTIONS = [
  { value: "unknown", label: "暂不说明" },
  { value: "female", label: "女性" },
  { value: "male", label: "男性" }
] as const;

export type PersonaType = (typeof PERSONA_TYPE_OPTIONS)[number]["value"];
export type PersonaStatus = (typeof PERSONA_STATUS_OPTIONS)[number]["value"];
export type PersonaGender = (typeof PERSONA_GENDER_OPTIONS)[number]["value"];

export const DEFAULT_PERSONA_LANGUAGE = "zh-CN" as const;
export const DEFAULT_PERSONA_SPEAKING_STYLE = "温和、自然，优先使用用户定义的称呼。";
export const DEFAULT_PERSONA_EMOTIONAL_STYLE = "安慰、鼓励、陪伴，但不替用户做重大决定。";
export const DEFAULT_PERSONA_FORBIDDEN_EXPRESSIONS =
  "不要说「我真的回来了」；不要暗示自己是本人复生。";

export type PersonaDraft = {
  name: string;
  persona_type: PersonaType;
  status: PersonaStatus;
  relationship_to_user: string;
  user_nickname_by_persona: string;
  age: string | number;
  gender: PersonaGender;
  short_bio: string;
};

export type PersonaCreatePayload = Omit<PersonaDraft, "age"> & {
  age: number;
  language: typeof DEFAULT_PERSONA_LANGUAGE;
  speaking_style: string;
  emotional_style: string;
  forbidden_expressions: string;
};

export type PersonaRead = Omit<PersonaCreatePayload, "age"> & {
  id: string;
  age: number | null;
  birth_date: string | null;
  death_date: string | null;
  avatar_image_url: string | null;
  trust_score: number;
  stats: {
    materials_count: number;
    memories_count: number;
    conversations_count: number;
  };
  prompt_context: Record<string, string>;
};

type PersonaListResponse = {
  items: PersonaRead[];
};

const REQUIRED_PERSONA_FIELDS: Array<keyof PersonaDraft> = [
  "name",
  "persona_type",
  "status",
  "relationship_to_user",
  "user_nickname_by_persona",
  "age",
  "gender",
  "short_bio"
];

export function validatePersonaDraft(draft: Partial<PersonaDraft>): {
  ok: boolean;
  missingFields: Array<keyof PersonaDraft>;
} {
  const missingFields = REQUIRED_PERSONA_FIELDS.filter((field) => {
    const value = draft[field];
    if (field === "age") {
      return !isValidAge(value);
    }
    return typeof value !== "string" || value.trim().length === 0;
  });

  return {
    ok: missingFields.length === 0,
    missingFields
  };
}

export function defaultStatusForType(personaType: PersonaType): PersonaStatus {
  const statusByType: Record<PersonaType, PersonaStatus> = {
    deceased_relative: "deceased",
    living_relative: "living",
    public_figure: "public",
    fictional_character: "fictional"
  };

  return statusByType[personaType];
}

export function personaTypeLabel(value: string): string {
  return PERSONA_TYPE_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

export async function listPersonas(): Promise<PersonaRead[]> {
  const response = await fetch(buildApiUrl(API_PATHS.personas.list), {
    headers: authHeaders()
  });
  const data = await readApiJson<PersonaListResponse>(
    response,
    "无法加载人物列表。"
  );
  return data.items;
}

export async function getPersona(id: string): Promise<PersonaRead> {
  const response = await fetch(buildApiUrl(API_PATHS.personas.detail(id)), {
    headers: authHeaders()
  });
  return readApiJson<PersonaRead>(response, "无法加载人物。");
}

export async function deletePersona(id: string): Promise<void> {
  const response = await fetch(buildApiUrl(API_PATHS.personas.detail(id)), {
    method: "DELETE",
    headers: authHeaders()
  });
  await readApiJson<never>(response, "无法删除星星。");
}

export async function createPersona(draft: PersonaDraft): Promise<PersonaRead> {
  const response = await fetch(buildApiUrl(API_PATHS.personas.list), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify(buildPersonaCreatePayload(draft))
  });
  return readApiJson<PersonaRead>(response, "无法创建人物。");
}

export function buildPersonaCreatePayload(draft: PersonaDraft): PersonaCreatePayload {
  return {
    name: draft.name.trim(),
    persona_type: draft.persona_type,
    status: draft.status,
    relationship_to_user: draft.relationship_to_user.trim(),
    user_nickname_by_persona: draft.user_nickname_by_persona.trim(),
    age: Number(draft.age),
    gender: draft.gender,
    short_bio: draft.short_bio.trim(),
    language: DEFAULT_PERSONA_LANGUAGE,
    speaking_style: DEFAULT_PERSONA_SPEAKING_STYLE,
    emotional_style: DEFAULT_PERSONA_EMOTIONAL_STYLE,
    forbidden_expressions: DEFAULT_PERSONA_FORBIDDEN_EXPRESSIONS
  };
}

export function buildCreatePersonaShortBio({
  birthDate,
  message
}: {
  birthDate: string;
  message: string;
}): string {
  return [
    birthDate.trim() ? `${birthDate.trim()} 出生` : "",
    message.trim() ? `有关TA的一切：${message.trim()}` : "",
    "由星记创建的专属星星。"
  ]
    .filter(Boolean)
    .join("\n");
}

export type CreatePersonaProcessingStage =
  | "demo_session"
  | "persona_card"
  | "upload_memories"
  | "review_entry";

export type CreatePersonaProgress = {
  label: string;
  percent: number;
};

export function buildCreatePersonaProgress(
  stage: CreatePersonaProcessingStage,
  uploadCount = 0
): CreatePersonaProgress {
  if (stage === "demo_session") {
    return { label: "正在准备演示会话...", percent: 20 };
  }

  if (stage === "persona_card") {
    return { label: "正在保存资料卡片...", percent: 45 };
  }

  if (stage === "upload_memories") {
    return {
      label: `正在上传 ${uploadCount} 个回忆文件...`,
      percent: 75
    };
  }

  return { label: "正在进入资料审核...", percent: 95 };
}

function isValidAge(value: PersonaDraft["age"] | undefined): boolean {
  const age = Number(value);
  return Number.isInteger(age) && age >= 1 && age <= 150;
}
