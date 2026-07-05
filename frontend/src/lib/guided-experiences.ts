import { API_PATHS, buildApiUrl, readApiJson } from "./api";
import { authHeaders } from "./auth";
import { ROUTES } from "./routes";
import type {
  ConversationContextKind,
  ConversationKind
} from "./chat";

export type GuidedExperienceKind = "regrets" | "wishes";

export type GuidedExperienceConfig = {
  kind: GuidedExperienceKind;
  title: string;
  eyebrow: string;
  openingMessage: string;
  emptyState: string;
  inputPlaceholder: string;
  submitLabel: string;
  persistenceNotice: string;
};

export type GuidedMemoryCandidate = {
  memory_card_id: string;
  title: string;
  summary: string;
  suggested_user_message: string;
  source_quote: string | null;
  source_location: string | null;
};

export type GuidedMemoryCandidateResponse = {
  kind: GuidedExperienceKind;
  items: GuidedMemoryCandidate[];
  empty_reason: string | null;
};

export function getGuidedExperienceConfig(
  kind: GuidedExperienceKind,
  personaName: string
): GuidedExperienceConfig {
  if (kind === "regrets") {
    return {
      kind,
      title: "遗憾对话室",
      eyebrow: "说出没来得及说的话",
      openingMessage: `${personaName}想先听你说：有没有什么以前没说的话，今天想慢慢告诉我？`,
      emptyState: "这里适合放下道歉、感谢、想念，或一段一直没机会说出口的话。",
      inputPlaceholder: "写下那些来不及说的话...",
      submitLabel: "说给 TA 听",
      persistenceNotice: "当前不会创建独立遗憾记录，会以这次对话继续陪你说完。"
    };
  }

  return {
    kind,
    title: "心愿延续系统",
    eyebrow: "把想念落成下一步",
    openingMessage: `${personaName}想先问你：你现在有什么想完成的心愿，或者想替我继续做的一件事吗？`,
    emptyState: "先写下一个心愿，再一起把它拆成下一步可以做的小事。",
    inputPlaceholder: "写下一个想完成的心愿...",
    submitLabel: "继续梳理心愿",
    persistenceNotice: "当前不会创建独立心愿记录，会以这次对话继续陪你梳理。"
  };
}

export function guidedExperienceRoute(kind: GuidedExperienceKind, personaId: string): string {
  return kind === "regrets" ? ROUTES.personaRegrets(personaId) : ROUTES.personaWishes(personaId);
}

export function guidedExperienceConversationKind(
  kind: GuidedExperienceKind
): ConversationKind {
  return kind;
}

export function guidedExperienceContextKind(
  kind: GuidedExperienceKind
): ConversationContextKind | undefined {
  return kind === "wishes" ? "wishes" : undefined;
}

export async function loadGuidedMemoryCandidates(
  personaId: string,
  kind: GuidedExperienceKind
): Promise<GuidedMemoryCandidateResponse> {
  const response = await fetch(buildApiUrl(API_PATHS.chat.guidedMemoryCandidates(personaId)), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify({ kind })
  });
  return readApiJson<GuidedMemoryCandidateResponse>(
    response,
    "无法提取记忆线索。"
  );
}
