const DEFAULT_API_BASE_URL = "http://localhost:8000";

export const API_PATHS = {
  health: "/health",
  auth: {
    me: "/api/auth/me",
    demo: "/api/auth/demo"
  },
  personas: {
    list: "/api/personas",
    detail: (id: string) => `/api/personas/${encodeURIComponent(id)}`
  },
  materials: {
    list: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/materials`,
    upload: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/materials/upload`,
    manual: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/materials/manual`,
    detail: (id: string) => `/api/materials/${encodeURIComponent(id)}`,
    parse: (id: string) => `/api/materials/${encodeURIComponent(id)}/parse`
  },
  jobs: {
    list: (personaId: string) => `/api/personas/${encodeURIComponent(personaId)}/jobs`,
    detail: (id: string) => `/api/jobs/${encodeURIComponent(id)}`,
    retry: (id: string) => `/api/jobs/${encodeURIComponent(id)}/retry`,
    cancel: (id: string) => `/api/jobs/${encodeURIComponent(id)}/cancel`
  },
  memories: {
    list: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/memories`,
    detail: (id: string) => `/api/memories/${encodeURIComponent(id)}`,
    confirm: (id: string) => `/api/memories/${encodeURIComponent(id)}/confirm`,
    reject: (id: string) => `/api/memories/${encodeURIComponent(id)}/reject`,
    disable: (id: string) => `/api/memories/${encodeURIComponent(id)}/disable`
  },
  audit: {
    logs: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/audit/logs`,
    summary: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/audit/summary`,
    report: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/audit/report`,
    dashboard: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/audit/dashboard`,
    conflicts: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/audit/conflicts`,
    resolveConflict: (personaId: string, conflictId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/audit/conflicts/${encodeURIComponent(conflictId)}/resolve`,
    search: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/audit/search`,
    history: (memoryId: string) => `/api/memories/${encodeURIComponent(memoryId)}/history`
  },
  profile: {
    detail: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/profile`,
    regenerate: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/profile/regenerate`,
    recalculateTrust: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/recalculate-trust`
  },
  chat: {
    conversations: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/conversations`,
    guidedMemoryCandidates: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/guided-memory-candidates`,
    conversation: (conversationId: string) =>
      `/api/conversations/${encodeURIComponent(conversationId)}`,
    messages: (conversationId: string) =>
      `/api/conversations/${encodeURIComponent(conversationId)}/messages`,
    citations: (messageId: string) =>
      `/api/messages/${encodeURIComponent(messageId)}/citations`,
    correctMemory: (messageId: string) =>
      `/api/messages/${encodeURIComponent(messageId)}/correct-memory`
  },
  voice: {
    config: (personaId: string) => `/api/personas/${encodeURIComponent(personaId)}/voice`,
    defaultTts: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/voice/default-tts`,
    samples: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/voice/samples`,
    clone: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/voice/clone`,
    synthesize: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/voice/synthesize`,
    voiceMessage: (conversationId: string) =>
      `/api/conversations/${encodeURIComponent(conversationId)}/voice-message`
  },
  avatar: {
    config: (personaId: string) => `/api/personas/${encodeURIComponent(personaId)}/avatar`,
    defaultAvatar: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/avatar/default`,
    generate: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/avatar/generate`,
    upload: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/avatar/upload`,
    file: (avatarModelId: string) =>
      `/api/avatar-models/${encodeURIComponent(avatarModelId)}/file`
  },
  stories: {
    list: (personaId: string) => `/api/personas/${encodeURIComponent(personaId)}/stories`,
    create: (personaId: string) => `/api/personas/${encodeURIComponent(personaId)}/stories`,
    seed: (personaId: string) => `/api/personas/${encodeURIComponent(personaId)}/stories/seed`,
    favorite: (storyId: string) => `/api/stories/${encodeURIComponent(storyId)}/favorite`,
    export: (personaId: string, storyId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/export/story/${encodeURIComponent(storyId)}`,
    exportAudio: (personaId: string, storyId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/export/story/${encodeURIComponent(storyId)}/audio`
  },
  data: {
    exportProfile: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/export/profile`,
    exportMemories: (personaId: string) =>
      `/api/personas/${encodeURIComponent(personaId)}/export/memories`,
    exportConversation: (conversationId: string) =>
      `/api/conversations/${encodeURIComponent(conversationId)}/export`,
    clearAccountData: "/api/settings/data"
  },
  providerSettings: {
    detail: "/api/settings/providers"
  }
} as const;

export function getApiBaseUrl(): string {
  const configuredUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

  if (!configuredUrl) {
    return DEFAULT_API_BASE_URL;
  }

  return configuredUrl.replace(/\/+$/, "");
}

export function buildApiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${getApiBaseUrl()}${normalizedPath}`;
}

export async function readApiJson<T>(
  response: Response,
  fallbackMessage: string
): Promise<T> {
  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(readApiErrorMessage(body) ?? fallbackMessage);
  }

  return body as T;
}

function readApiErrorMessage(body: unknown): string | null {
  if (!isRecord(body) || !("detail" in body)) {
    return null;
  }

  const detail = body.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return "请求校验失败。";
  }

  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
