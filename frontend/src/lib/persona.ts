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

export type PersonaDraft = {
  name: string;
  persona_type: PersonaType;
  status: PersonaStatus;
  relationship_to_user: string;
  user_nickname_by_persona: string;
  gender: PersonaGender;
  language: string;
  short_bio: string;
  speaking_style: string;
  emotional_style: string;
  forbidden_expressions: string;
};

export type PersonaRead = PersonaDraft & {
  id: string;
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
  "gender",
  "language",
  "short_bio",
  "speaking_style",
  "emotional_style",
  "forbidden_expressions"
];

export function validatePersonaDraft(draft: Partial<PersonaDraft>): {
  ok: boolean;
  missingFields: Array<keyof PersonaDraft>;
} {
  const missingFields = REQUIRED_PERSONA_FIELDS.filter((field) => {
    const value = draft[field];
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

export async function createPersona(draft: PersonaDraft): Promise<PersonaRead> {
  const response = await fetch(buildApiUrl(API_PATHS.personas.list), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify(trimPersonaDraft(draft))
  });
  return readApiJson<PersonaRead>(response, "无法创建人物。");
}

function trimPersonaDraft(draft: PersonaDraft): PersonaDraft {
  return {
    name: draft.name.trim(),
    persona_type: draft.persona_type,
    status: draft.status,
    relationship_to_user: draft.relationship_to_user.trim(),
    user_nickname_by_persona: draft.user_nickname_by_persona.trim(),
    gender: draft.gender,
    language: draft.language.trim(),
    short_bio: draft.short_bio.trim(),
    speaking_style: draft.speaking_style.trim(),
    emotional_style: draft.emotional_style.trim(),
    forbidden_expressions: draft.forbidden_expressions.trim()
  };
}
