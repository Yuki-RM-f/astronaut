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

export type DefaultTTSVoice = {
  voice_id: string;
  voice_name: string;
  language: string;
  description: string;
};

export type VoiceConfigResponse = {
  persona_id: string;
  voice_status: VoiceStatus;
  selected_voice_model: VoiceModelRead | null;
  voice_models: VoiceModelRead[];
  default_tts_notice: string;
  default_tts_options: Record<string, string[]>;
  default_tts_voices: DefaultTTSVoice[];
  tts_model: string;
};

export type DefaultTTSPayload = {
  gender: "male" | "female" | "neutral";
  age_style: "young" | "middle_aged" | "elderly";
  style: "gentle" | "calm" | "lively" | "kind" | "low";
  speed: "slow" | "normal" | "fast";
  emotion: "calm" | "comfort" | "encourage" | "nostalgia";
  voice_id: string;
};

export type VoiceJobRead = {
  id: string;
  job_type: string;
  status: string;
  error_message?: string | null;
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
export const DEFAULT_MINIMAX_TTS_VOICE_ID = "Chinese (Mandarin)_Kind-hearted_Elder";
export const DEFAULT_TTS_VOICES: DefaultTTSVoice[] = [
  { voice_id: "Chinese (Mandarin)_Reliable_Executive", voice_name: "可靠高管", language: "Chinese (Mandarin)", description: "稳重可靠的普通话男声。" },
  { voice_id: "Chinese (Mandarin)_News_Anchor", voice_name: "新闻主播", language: "Chinese (Mandarin)", description: "新闻播报风格的普通话女声。" },
  { voice_id: "Chinese (Mandarin)_Unrestrained_Young_Man", voice_name: "洒脱青年", language: "Chinese (Mandarin)", description: "松弛外放的年轻男声。" },
  { voice_id: "Chinese (Mandarin)_Mature_Woman", voice_name: "成熟女性", language: "Chinese (Mandarin)", description: "成熟稳重的普通话女声。" },
  { voice_id: "Arrogant_Miss", voice_name: "傲娇小姐", language: "Chinese (Mandarin)", description: "有个性、略带骄傲感的女声。" },
  { voice_id: "Chinese (Mandarin)_Kind-hearted_Antie", voice_name: "亲切阿姨", language: "Chinese (Mandarin)", description: "亲切温和的阿姨声线。" },
  { voice_id: "Chinese (Mandarin)_HK_Flight_Attendant", voice_name: "港风空乘", language: "Chinese (Mandarin)", description: "服务感较强的空乘声线。" },
  { voice_id: "Chinese (Mandarin)_Humorous_Elder", voice_name: "幽默长者", language: "Chinese (Mandarin)", description: "幽默长者声线。" },
  { voice_id: "Chinese (Mandarin)_Gentleman", voice_name: "温和绅士", language: "Chinese (Mandarin)", description: "温和绅士男声。" },
  { voice_id: "Chinese (Mandarin)_Warm_Bestie", voice_name: "暖心挚友", language: "Chinese (Mandarin)", description: "温暖亲近的朋友声线。" },
  { voice_id: "Chinese (Mandarin)_Stubborn_Friend", voice_name: "固执朋友", language: "Chinese (Mandarin)", description: "固执朋友感声线。" },
  { voice_id: "Chinese (Mandarin)_Sweet_Lady", voice_name: "甜美女士", language: "Chinese (Mandarin)", description: "甜美温柔女声。" },
  { voice_id: "Chinese (Mandarin)_Southern_Young_Man", voice_name: "南方青年", language: "Chinese (Mandarin)", description: "南方年轻男声。" },
  { voice_id: "Chinese (Mandarin)_Wise_Women", voice_name: "睿智女性", language: "Chinese (Mandarin)", description: "沉稳智慧女声。" },
  { voice_id: "Chinese (Mandarin)_Gentle_Youth", voice_name: "温柔青年", language: "Chinese (Mandarin)", description: "温柔青年声线。" },
  { voice_id: "Chinese (Mandarin)_Warm_Girl", voice_name: "温暖女孩", language: "Chinese (Mandarin)", description: "温暖年轻女声。" },
  { voice_id: "Chinese (Mandarin)_Male_Announcer", voice_name: "男播音员", language: "Chinese (Mandarin)", description: "播音男声。" },
  { voice_id: DEFAULT_MINIMAX_TTS_VOICE_ID, voice_name: "亲切长者", language: "Chinese (Mandarin)", description: "亲切长者声线，适合作为默认纪念陪伴音色。" },
  { voice_id: "Chinese (Mandarin)_Radio_Host", voice_name: "电台主持", language: "Chinese (Mandarin)", description: "电台主持声线。" },
  { voice_id: "Chinese (Mandarin)_Lyrical_Voice", voice_name: "抒情声线", language: "Chinese (Mandarin)", description: "抒情声线。" },
  { voice_id: "Chinese (Mandarin)_Straightforward_Boy", voice_name: "直率男孩", language: "Chinese (Mandarin)", description: "直率男孩声线。" },
  { voice_id: "Chinese (Mandarin)_Sincere_Adult", voice_name: "真诚成年人", language: "Chinese (Mandarin)", description: "真诚成人声线。" },
  { voice_id: "Chinese (Mandarin)_Gentle_Senior", voice_name: "温和长辈", language: "Chinese (Mandarin)", description: "温和长辈声线。" },
  { voice_id: "Chinese (Mandarin)_Crisp_Girl", voice_name: "清亮女孩", language: "Chinese (Mandarin)", description: "清脆女声。" },
  { voice_id: "Chinese (Mandarin)_Pure-hearted_Boy", voice_name: "纯真男孩", language: "Chinese (Mandarin)", description: "纯真男孩声线。" },
  { voice_id: "Chinese (Mandarin)_Soft_Girl", voice_name: "柔和女孩", language: "Chinese (Mandarin)", description: "柔和女声。" },
  { voice_id: "Chinese (Mandarin)_IntellectualGirl", voice_name: "知性女孩", language: "Chinese (Mandarin)", description: "知性女声。" },
  { voice_id: "Chinese (Mandarin)_Warm_HeartedGirl", voice_name: "暖心女孩", language: "Chinese (Mandarin)", description: "暖心女声。" },
  { voice_id: "Chinese (Mandarin)_Laid_BackGirl", voice_name: "松弛女孩", language: "Chinese (Mandarin)", description: "松弛女声。" },
  { voice_id: "Chinese (Mandarin)_ExplorativeGirl", voice_name: "探索女孩", language: "Chinese (Mandarin)", description: "探索感年轻女声。" },
  { voice_id: "Chinese (Mandarin)_Warm-HeartedAunt", voice_name: "暖心阿姨", language: "Chinese (Mandarin)", description: "暖心阿姨声线。" },
  { voice_id: "Chinese (Mandarin)_BashfulGirl", voice_name: "害羞女孩", language: "Chinese (Mandarin)", description: "羞涩女声。" }
];

export function personaVoiceRoute(personaId: string): string {
  return `/personas/${encodeURIComponent(personaId)}/voice`;
}

export function buildDefaultTtsPayload(
  voiceId: string = DEFAULT_MINIMAX_TTS_VOICE_ID
): DefaultTTSPayload {
  return {
    gender: "female",
    age_style: "elderly",
    style: "gentle",
    speed: "normal",
    emotion: "comfort",
    voice_id: voiceId
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
  const systemVoiceId = voiceIdFromModel(model);
  const parts = [
    voiceStatusLabel(model.status),
    model.status === "default_tts" && systemVoiceId
      ? `${defaultTtsVoiceLabel(systemVoiceId)} · ${systemVoiceId}`
      : model.provider_name,
    model.quality_score === null ? null : `质量 ${model.quality_score}`
  ].filter(Boolean);
  return parts.join(" · ");
}

export function voiceIdFromModel(model: VoiceModelRead | null | undefined): string | null {
  const artifact = model?.model_artifact_url ?? "";
  if (artifact.startsWith("minimax://system-voice/")) {
    return decodeURIComponent(artifact.replace("minimax://system-voice/", ""));
  }
  if (artifact.startsWith("minimax://voice/")) {
    return artifact.split("/").pop() || null;
  }
  if (model?.status === "default_tts") {
    return DEFAULT_MINIMAX_TTS_VOICE_ID;
  }
  return null;
}

export function defaultTtsVoiceLabel(voiceId: string | null | undefined): string {
  const voice = DEFAULT_TTS_VOICES.find((item) => item.voice_id === voiceId);
  return voice?.voice_name ?? voiceId ?? "未记录";
}

export function voiceSourceLabel(
  model: VoiceModelRead | null | undefined,
  ttsModel: string | null | undefined
): string {
  if (!model) {
    return "尚未选择语音来源";
  }
  const voiceId = voiceIdFromModel(model);
  if (model.status === "cloned_ready") {
    const suffix = voiceId ? ` · MiniMax voice_id ${voiceId}` : "";
    return `用户创建的模拟音色 ID：${model.id}${suffix}`;
  }
  if (model.status === "default_tts") {
    return `MiniMax ${ttsModel || "speech-2.8-hd"} · voice_id ${
      voiceId || DEFAULT_MINIMAX_TTS_VOICE_ID
    }`;
  }
  return voiceModelSummary(model);
}

export function hasChatReadyVoiceConfig(
  config: VoiceConfigResponse | null | undefined
): boolean {
  const status = config?.selected_voice_model?.status;
  return status === "default_tts" || status === "cloned_ready";
}

export function latestCloneSourceModel(
  models: VoiceModelRead[],
  preferredVoiceModelId?: string | null
): VoiceModelRead | null {
  const cloneableModels = models.filter(
    (model) =>
      (model.status === "sample_ready" || model.status === "clone_failed") &&
      Boolean(model.reference_audio_asset_id)
  );
  const preferredModel = cloneableModels.find((model) => model.id === preferredVoiceModelId);
  if (preferredModel) {
    return preferredModel;
  }
  const sampleReadyModels = cloneableModels.filter((model) => model.status === "sample_ready");
  const candidates = sampleReadyModels.length > 0 ? sampleReadyModels : cloneableModels;
  return (
    candidates.sort((left, right) => {
      const rightTime = Date.parse(right.created_at);
      const leftTime = Date.parse(left.created_at);
      return rightTime - leftTime || right.id.localeCompare(left.id);
    })[0] ?? null
  );
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
