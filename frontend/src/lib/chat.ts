import { API_PATHS, buildApiUrl, readApiJson } from "./api";
import { authHeaders } from "./auth";
import { shouldDriveAvatarMouth } from "./avatar";
import { MemoryRead } from "./memories";

export type ConversationKind = "chat" | "regrets" | "wishes";
export type ConversationContextKind = "general" | "wishes";

export type ConversationRead = {
  id: string;
  user_id: string;
  persona_id: string;
  title: string | null;
  kind: ConversationKind;
  context_kind: ConversationContextKind;
  created_at: string;
  updated_at: string;
};

type ConversationListResponse = {
  items: ConversationRead[];
};

export type MessageRole = "user" | "persona" | string;

export type MessageCitationRead = {
  id: string;
  message_id: string;
  memory_card_id: string | null;
  source_material_id: string | null;
  parsed_chunk_id: string | null;
  quote: string | null;
  source_location: string | null;
  created_at: string;
};

export type MessageRead = {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  audio_url: string | null;
  metadata_json: Record<string, unknown> | unknown[] | null;
  created_at: string;
  citations: MessageCitationRead[];
};

type MessageListResponse = {
  items: MessageRead[];
};

type MessageCitationListResponse = {
  items: MessageCitationRead[];
};

export type MemoryCorrectionPayload = {
  memory_id: string;
  content: string;
  title?: string;
};

export type MemoryCorrectionResponse = {
  memory: MemoryRead;
  message: string;
};

export type VoiceMessagePayload = {
  source_material_id: string;
};

type MessageSendPayload = {
  content: string;
  guided_memory_ids?: string[];
};

export function messageRoleLabel(role: MessageRole): string {
  if (role === "user") {
    return "你";
  }
  if (role === "persona") {
    return "TA";
  }
  return role;
}

export function citationSummary(citation: MessageCitationRead): string {
  const parts = [
    citation.memory_card_id ? `记忆 ${citation.memory_card_id}` : null,
    citation.source_material_id ? `资料 ${citation.source_material_id}` : null,
    citation.source_location
  ].filter(Boolean);

  return parts.join(" · ") || "暂无来源引用";
}

export function isBlankChatText(value: string): boolean {
  return value.trim().length === 0;
}

export function hasPlayableAudio(message: MessageRead): boolean {
  return Boolean(message.audio_url?.trim());
}

export function isAvatarMouthActive(
  messages: Array<{ id: string; role: string; audio_url?: string | null }>,
  playingMessageId: string | null
): boolean {
  return messages.some((message) => shouldDriveAvatarMouth(message, playingMessageId));
}

export function personaMessageLabel(personaName: string): string {
  return personaName.trim() || "TA";
}

export function buildOptimisticUserMessage(
  conversationId: string,
  content: string,
  now = new Date()
): MessageRead {
  const createdAt = now.toISOString();
  return {
    id: `optimistic-user-${now.getTime()}`,
    conversation_id: conversationId,
    role: "user",
    content: content.trim(),
    audio_url: null,
    metadata_json: { optimistic: true },
    created_at: createdAt,
    citations: []
  };
}

export function buildPendingPersonaThinkingMessage(
  conversationId: string,
  personaName: string,
  now = new Date()
): MessageRead {
  const createdAt = now.toISOString();
  return {
    id: `pending-persona-${now.getTime()}`,
    conversation_id: conversationId,
    role: "persona",
    content: `${personaMessageLabel(personaName)}正在想...`,
    audio_url: null,
    metadata_json: { pending_persona_thinking: true },
    created_at: createdAt,
    citations: []
  };
}

export function isPendingPersonaThinking(message: MessageRead): boolean {
  if (message.id.startsWith("pending-persona-")) {
    return true;
  }
  const metadata = message.metadata_json;
  return (
    typeof metadata === "object" &&
    metadata !== null &&
    !Array.isArray(metadata) &&
    metadata.pending_persona_thinking === true
  );
}

export function buildCorrectionPayload(
  memoryId: string,
  content: string,
  title?: string
): MemoryCorrectionPayload {
  const trimmedContent = content.trim();
  if (!trimmedContent) {
    throw new Error("纠正内容不能为空。");
  }

  const payload: MemoryCorrectionPayload = {
    memory_id: memoryId,
    content: trimmedContent
  };
  const trimmedTitle = title?.trim();
  if (trimmedTitle) {
    payload.title = trimmedTitle;
  }
  return payload;
}

export async function listConversations(
  personaId: string,
  kind?: ConversationKind,
  contextKind?: ConversationContextKind
): Promise<ConversationRead[]> {
  const response = await fetch(buildApiUrl(conversationListPath(personaId, kind, contextKind)), {
    headers: authHeaders()
  });
  const data = await readApiJson<ConversationListResponse>(
    response,
    "无法加载对话。"
  );
  return data.items;
}

export async function createConversation(
  personaId: string,
  title?: string,
  kind: ConversationKind = "chat",
  contextKind?: ConversationContextKind
): Promise<ConversationRead> {
  const response = await fetch(buildApiUrl(API_PATHS.chat.conversations(personaId)), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify({
      title: title?.trim() || undefined,
      kind,
      context_kind: contextKind
    })
  });
  return readApiJson<ConversationRead>(response, "无法创建对话。");
}

function conversationListPath(
  personaId: string,
  kind?: ConversationKind,
  contextKind?: ConversationContextKind
): string {
  const path = API_PATHS.chat.conversations(personaId);
  const searchParams = new URLSearchParams();
  if (kind) {
    searchParams.set("kind", kind);
  }
  if (contextKind) {
    searchParams.set("context_kind", contextKind);
  }
  const query = searchParams.toString();
  return query ? `${path}?${query}` : path;
}

export async function listMessages(conversationId: string): Promise<MessageRead[]> {
  const response = await fetch(buildApiUrl(API_PATHS.chat.messages(conversationId)), {
    headers: authHeaders()
  });
  const data = await readApiJson<MessageListResponse>(
    response,
    "无法加载消息。"
  );
  return data.items;
}

export async function sendMessage(
  conversationId: string,
  content: string,
  guidedMemoryIds?: string[]
): Promise<MessageRead> {
  const trimmedContent = content.trim();
  const rawPayload: MessageSendPayload = {
    content: trimmedContent,
    guided_memory_ids: guidedMemoryIds
  };
  const response = await fetch(buildApiUrl(API_PATHS.chat.messages(conversationId)), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify(trimMessagePayload(rawPayload))
  });
  return readApiJson<MessageRead>(response, "无法发送消息。");
}

function trimMessagePayload(payload: MessageSendPayload): MessageSendPayload {
  const guidedMemoryIds = (payload.guided_memory_ids ?? [])
    .map((memoryId) => memoryId.trim())
    .filter(Boolean)
    .slice(0, 3);
  return {
    content: payload.content.trim(),
    ...(guidedMemoryIds.length > 0 ? { guided_memory_ids: guidedMemoryIds } : {})
  };
}

export async function sendVoiceMessage(
  conversationId: string,
  payload: VoiceMessagePayload
): Promise<MessageRead> {
  const response = await fetch(buildApiUrl(API_PATHS.voice.voiceMessage(conversationId)), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify(payload)
  });
  return readApiJson<MessageRead>(response, "无法发送语音消息。");
}

export async function listMessageCitations(
  messageId: string
): Promise<MessageCitationRead[]> {
  const response = await fetch(buildApiUrl(API_PATHS.chat.citations(messageId)), {
    headers: authHeaders()
  });
  const data = await readApiJson<MessageCitationListResponse>(
    response,
    "无法加载引用依据。"
  );
  return data.items;
}

export async function correctMessageMemory(
  messageId: string,
  payload: MemoryCorrectionPayload
): Promise<MemoryCorrectionResponse> {
  const response = await fetch(buildApiUrl(API_PATHS.chat.correctMemory(messageId)), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify(payload)
  });
  return readApiJson<MemoryCorrectionResponse>(
    response,
    "无法纠正记忆。"
  );
}
