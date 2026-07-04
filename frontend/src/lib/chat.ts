import { API_PATHS, buildApiUrl, readApiJson } from "./api";
import { authHeaders } from "./auth";
import { MemoryRead } from "./memories";

export type ConversationRead = {
  id: string;
  user_id: string;
  persona_id: string;
  title: string | null;
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
  personaId: string
): Promise<ConversationRead[]> {
  const response = await fetch(buildApiUrl(API_PATHS.chat.conversations(personaId)), {
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
  title?: string
): Promise<ConversationRead> {
  const response = await fetch(buildApiUrl(API_PATHS.chat.conversations(personaId)), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify({ title: title?.trim() || undefined })
  });
  return readApiJson<ConversationRead>(response, "无法创建对话。");
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
  content: string
): Promise<MessageRead> {
  const trimmedContent = content.trim();
  const response = await fetch(buildApiUrl(API_PATHS.chat.messages(conversationId)), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify({ content: trimmedContent })
  });
  return readApiJson<MessageRead>(response, "无法发送消息。");
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
