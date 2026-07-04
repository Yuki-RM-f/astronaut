export const ROUTES = {
  home: "/",
  login: "/login",
  register: "/register",
  dashboard: "/dashboard",
  personasNew: "/personas/new",
  personaDetail: (id: string) => `/personas/${encodeURIComponent(id)}`,
  personaUploads: (id: string) => `/personas/${encodeURIComponent(id)}/uploads`,
  personaJobs: (id: string) => `/personas/${encodeURIComponent(id)}/jobs`,
  personaMemories: (id: string) => `/personas/${encodeURIComponent(id)}/memories`,
  personaProfile: (id: string) => `/personas/${encodeURIComponent(id)}/profile`,
  personaChat: (id: string) => `/personas/${encodeURIComponent(id)}/chat`,
  personaVoice: (id: string) => `/personas/${encodeURIComponent(id)}/voice`,
  personaAvatar: (id: string) => `/personas/${encodeURIComponent(id)}/avatar`
} as const;
