export const ROUTES = {
  home: "/",
  productIntro: "/product-intro",
  dashboard: "/dashboard",
  personasNew: "/personas/new",
  personaDetail: (id: string) => `/personas/${encodeURIComponent(id)}`,
  personaUploads: (id: string) => `/personas/${encodeURIComponent(id)}/uploads`,
  personaJobs: (id: string) => `/personas/${encodeURIComponent(id)}/jobs`,
  personaMemories: (id: string) => `/personas/${encodeURIComponent(id)}/memories`,
  personaChat: (id: string) => `/personas/${encodeURIComponent(id)}/chat`,
  personaVoice: (id: string) => `/personas/${encodeURIComponent(id)}/voice`,
  personaAvatar: (id: string) => `/personas/${encodeURIComponent(id)}/avatar`,
  personaRegrets: (id: string) => `/personas/${encodeURIComponent(id)}/regrets`,
  personaWishes: (id: string) => `/personas/${encodeURIComponent(id)}/wishes`
} as const;
