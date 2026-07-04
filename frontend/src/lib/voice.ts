import { authHeaders } from "./auth";
import { API_PATHS, buildApiUrl, readApiJson } from "./api";

export const DEFAULT_TTS_NOTICE =
  "当前使用系统默认声音，不是 TA 的真实声音。上传 TA 的清晰语音后，可以尝试生成模拟音色。";

export type VoiceStatus =
  | "no_voice"
  | "default_tts"
  | "sample_ready"
  | "cloning"
  | "cloned_ready"
  | "clone_failed";

export type VoiceModelRead = {
  id: string;
  persona_id: string;
  provider_type: string | null;
  provider_name: string | null;
  status: string | null;
  reference_audio_asset_id: string | null;
  model_artifact_url: string | null;
  sample_text: string | null;
  sample_audio_url: string | null;
  quality_score: number | null;
  user_selected: boolean;
  created_at: string;
  updated_at: string;
};

export type VoiceConfigResponse = {
  persona_id: string;
  voice_status: VoiceStatus;
  selected_voice_model: VoiceModelRead | null;
  voice_models: VoiceModelRead[];
  default_tts_notice: string;
  default_tts_options: Record<string, string[]>;
};

export type DefaultTTSPayload = {
  gender: "male" | "female" | "neutral";
  age_style: "young" | "middle_aged" | "elderly";
  style: "gentle" | "calm" | "lively" | "kind" | "low";
  speed: "slow" | "normal" | "fast";
  emotion: "calm" | "comfort" | "encourage" | "nostalgia";
};

export type VoiceJobRead = {
  id: string;
  job_type: string;
  status: string;
};

export type SpeechSynthesisResponse = {
  audio_url: string;
  voice_status: VoiceStatus;
  selected_voice_model: VoiceModelRead;
  default_tts_notice: string;
  job: VoiceJobRead;
};

export type VoiceSampleResponse = {
  voice_status: VoiceStatus;
  voice_model: VoiceModelRead;
  job: VoiceJobRead;
};

export type VoiceCloneResponse = {
  voice_status: VoiceStatus;
  voice_model: VoiceModelRead;
  selected_voice_model: VoiceModelRead;
  default_tts_notice: string;
  job: VoiceJobRead;
};

export const VOICE_API_PATHS = API_PATHS.voice;

export function personaVoiceRoute(personaId: string): string {
  return `/personas/${encodeURIComponent(personaId)}/voice`;
}

export function buildDefaultTtsPayload(): DefaultTTSPayload {
  return {
    gender: "female",
    age_style: "elderly",
    style: "gentle",
    speed: "normal",
    emotion: "comfort"
  };
}

export function voiceStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case "no_voice":
      return "未设置声音";
    case "default_tts":
      return "系统默认 TTS";
    case "sample_ready":
      return "已有可克隆样本";
    case "cloning":
      return "音色克隆中";
    case "cloned_ready":
      return "模拟音色可用";
    case "clone_failed":
      return "音色克隆失败";
    default:
      return status || "未知状态";
  }
}

export function isBlankVoiceText(text: string): boolean {
  return text.trim().length === 0;
}

export function voiceModelSummary(model: VoiceModelRead): string {
  const parts = [
    voiceStatusLabel(model.status),
    model.provider_name,
    model.quality_score === null ? null : `质量 ${model.quality_score}`
  ].filter(Boolean);
  return parts.join(" · ");
}

export async function getVoiceConfig(personaId: string): Promise<VoiceConfigResponse> {
  const response = await fetch(buildApiUrl(VOICE_API_PATHS.config(personaId)), {
    headers: authHeaders()
  });
  return readApiJson<VoiceConfigResponse>(response, "无法加载声音配置。");
}

export async function selectDefaultTts(
  personaId: string,
  payload: DefaultTTSPayload = buildDefaultTtsPayload()
): Promise<VoiceConfigResponse> {
  const response = await fetch(buildApiUrl(VOICE_API_PATHS.defaultTts(personaId)), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload)
  });
  return readApiJson<VoiceConfigResponse>(response, "无法选择默认 TTS。");
}

export async function createVoiceSample(
  personaId: string,
  sourceMaterialId: string
): Promise<VoiceSampleResponse> {
  const response = await fetch(buildApiUrl(VOICE_API_PATHS.samples(personaId)), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ source_material_id: sourceMaterialId })
  });
  return readApiJson<VoiceSampleResponse>(response, "无法创建音色样本。");
}

export async function cloneVoice(
  personaId: string,
  voiceModelId: string
): Promise<VoiceCloneResponse> {
  const response = await fetch(buildApiUrl(VOICE_API_PATHS.clone(personaId)), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ voice_model_id: voiceModelId })
  });
  return readApiJson<VoiceCloneResponse>(response, "无法发起音色克隆。");
}

export async function synthesizeSpeech(
  personaId: string,
  text: string
): Promise<SpeechSynthesisResponse> {
  const response = await fetch(buildApiUrl(VOICE_API_PATHS.synthesize(personaId)), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ text })
  });
  return readApiJson<SpeechSynthesisResponse>(response, "无法生成语音。");
}
