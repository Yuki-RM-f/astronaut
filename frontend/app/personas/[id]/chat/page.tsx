"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { AvatarPreview } from "@/src/components/AvatarPreview";
import { DemoEntry } from "@/src/components/DemoEntry";
import {
  AiReminder,
  GlassPanel,
  MemoryContainer,
  MemoryShell,
  PaperNote,
  VoiceWave
} from "@/src/components/MemorySpace";
import {
  buildCorrectionPayload,
  citationSummary,
  correctMessageMemory,
  ConversationRead,
  createConversation,
  hasPlayableAudio,
  isBlankChatText,
  listConversations,
  listMessages,
  MessageCitationRead,
  MessageRead,
  messageRoleLabel,
  sendMessage,
  sendVoiceMessage
} from "@/src/lib/chat";
import {
  AvatarConfigResponse,
  getAvatarConfig,
  shouldDriveAvatarMouth,
  shouldShowChatAvatar
} from "@/src/lib/avatar";
import { getAuthToken } from "@/src/lib/auth";
import { listMaterials, SourceMaterialRead, uploadMaterials } from "@/src/lib/materials";
import { getPersona, PersonaRead } from "@/src/lib/persona";
import { ROUTES } from "@/src/lib/routes";

type PageState = "checking" | "signedOut" | "loading" | "ready" | "error";
type RecordingState = "idle" | "recording" | "uploading";

export default function PersonaChatPage() {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<PageState>("checking");
  const [persona, setPersona] = useState<PersonaRead | null>(null);
  const [conversation, setConversation] = useState<ConversationRead | null>(null);
  const [messages, setMessages] = useState<MessageRead[]>([]);
  const [audioMaterials, setAudioMaterials] = useState<SourceMaterialRead[]>([]);
  const [avatarConfig, setAvatarConfig] = useState<AvatarConfigResponse | null>(null);
  const [selectedAudioMaterialId, setSelectedAudioMaterialId] = useState("");
  const [playingAudioMessageId, setPlayingAudioMessageId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [sendingVoice, setSendingVoice] = useState(false);
  const [recordingState, setRecordingState] = useState<RecordingState>("idle");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    if (!getAuthToken()) {
      setState("signedOut");
      return;
    }

    if (!personaId) {
      setError("缺少人物 ID。");
      setState("error");
      return;
    }

    let isCurrent = true;
    setState("loading");
    setError(null);

    loadChat(personaId)
      .then((loaded) => {
        if (!isCurrent) {
          return;
        }
        setPersona(loaded.persona);
        setConversation(loaded.conversation);
        setMessages(loaded.messages);
        setAudioMaterials(loaded.audioMaterials);
        setAvatarConfig(loaded.avatarConfig);
        setSelectedAudioMaterialId(loaded.audioMaterials[0]?.id ?? "");
        setPlayingAudioMessageId(null);
        setState("ready");
      })
      .catch((caught) => {
        if (!isCurrent) {
          return;
        }
        setError(caught instanceof Error ? caught.message : "无法加载对话。");
        setState("error");
      });

    return () => {
      isCurrent = false;
      stopRecordingTracks();
    };
  }, [personaId]);

  async function refreshMessages(currentConversation: ConversationRead) {
    setPlayingAudioMessageId(null);
    setMessages(await listMessages(currentConversation.id));
  }

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!conversation || isBlankChatText(draft)) {
      return;
    }

    setError(null);
    setNotice(null);
    setSending(true);
    try {
      await sendMessage(conversation.id, draft);
      setDraft("");
      await refreshMessages(conversation);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法发送消息。");
    } finally {
      setSending(false);
    }
  }

  async function handleSendVoice() {
    if (!conversation || !selectedAudioMaterialId) {
      setError("需要先选择已上传的音频资料。");
      return;
    }

    setError(null);
    setNotice(null);
    setSendingVoice(true);
    try {
      await sendVoiceMessage(conversation.id, {
        source_material_id: selectedAudioMaterialId
      });
      setNotice("已发送语音消息，并生成一条带语音播放的回复。");
      await refreshMessages(conversation);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法发送语音消息。");
    } finally {
      setSendingVoice(false);
    }
  }

  async function handleStartRecording() {
    if (!persona || recordingState !== "idle") {
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("当前浏览器不支持录音。可以先上传音频资料后发送语音消息。");
      return;
    }

    setError(null);
    setNotice(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaStreamRef.current = stream;
      mediaRecorderRef.current = recorder;
      recordedChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunksRef.current.push(event.data);
        }
      };
      recorder.onerror = () => {
        setError("录音失败。可以改用上传音频资料。");
        setRecordingState("idle");
        stopRecordingTracks();
      };
      recorder.onstop = () => {
        void uploadRecordedVoice(persona.id);
      };

      recorder.start();
      setRecordingState("recording");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法开始录音。");
      setRecordingState("idle");
      stopRecordingTracks();
    }
  }

  function handleStopRecording() {
    const recorder = mediaRecorderRef.current;
    if (recorder?.state === "recording") {
      setRecordingState("uploading");
      recorder.stop();
      return;
    }

    stopRecordingTracks();
    setRecordingState("idle");
  }

  async function uploadRecordedVoice(currentPersonaId: string) {
    try {
      const chunks = recordedChunksRef.current;
      if (chunks.length === 0) {
        throw new Error("没有录到可上传的音频。");
      }
      const mimeType = chunks[0]?.type || "audio/webm";
      const fileExtension = mimeType.includes("ogg") ? "ogg" : "webm";
      const audioBlob = new Blob(chunks, { type: mimeType });
      const audioFile = new File([audioBlob], `voice-message-${Date.now()}.${fileExtension}`, {
        type: mimeType
      });
      const uploaded = await uploadMaterials(currentPersonaId, {
        files: [audioFile],
        importance: "normal",
        user_description: "聊天页录音"
      });
      const audioMaterial =
        uploaded.find((material) => material.file_type === "audio") ?? uploaded[0];
      if (!audioMaterial) {
        throw new Error("录音上传后没有生成音频资料。");
      }
      setAudioMaterials((current) => [
        ...current.filter((material) => material.id !== audioMaterial.id),
        audioMaterial
      ]);
      setSelectedAudioMaterialId(audioMaterial.id);
      setNotice("录音已上传，可点击发送语音消息。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法上传录音。");
    } finally {
      recordedChunksRef.current = [];
      mediaRecorderRef.current = null;
      stopRecordingTracks();
      setRecordingState("idle");
    }
  }

  function stopRecordingTracks() {
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
  }

  async function handleCorrection(
    message: MessageRead,
    citation: MessageCitationRead,
    content: string
  ) {
    if (!citation.memory_card_id) {
      setError("这条依据没有关联记忆卡片。");
      return;
    }
    if (!conversation) {
      setError("缺少当前对话。");
      return;
    }

    setError(null);
    setNotice(null);
    try {
      const result = await correctMessageMemory(
        message.id,
        buildCorrectionPayload(citation.memory_card_id, content)
      );
      setNotice(result.message);
      await refreshMessages(conversation);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法纠正记忆。");
    }
  }

  const selectedAvatarModel = avatarConfig?.selected_avatar_model ?? null;
  const showChatAvatar = shouldShowChatAvatar(avatarConfig);
  const isAvatarMouthActive = messages.some((message) =>
    shouldDriveAvatarMouth(message, playingAudioMessageId)
  );

  return (
    <MemoryShell background="grandmotherTea">
      <MemoryContainer>
      <div className="flex flex-wrap items-center gap-3 text-sm font-semibold text-memoryAccent">
        <Link href={personaId ? ROUTES.personaDetail(personaId) : ROUTES.dashboard}>
          返回记忆空间
        </Link>
        {personaId ? <Link href={ROUTES.personaMemories(personaId)}>审核记忆</Link> : null}
        {personaId ? <Link href={ROUTES.personaProfile(personaId)}>人格档案</Link> : null}
        {personaId ? <Link href={ROUTES.personaVoice(personaId)}>声音设置</Link> : null}
        {personaId ? <Link href={ROUTES.personaAvatar(personaId)}>3D 形象</Link> : null}
      </div>

      <header className="mt-6 grid gap-4">
        <p className="inline-flex w-fit rounded-full border border-memoryLine/70 bg-white/68 px-4 py-2 text-sm font-semibold tracking-[0.08em] text-memoryAccent shadow-soft backdrop-blur">
          文本对话
        </p>
        <h1 className="font-serif text-4xl font-semibold leading-tight text-memoryText sm:text-5xl">
          {persona ? `和${persona.name}说说话` : "和 TA 说说话"}
        </h1>
        <p className="max-w-3xl text-sm leading-7 text-memoryText/72">
          回复会使用人物设定、已审核记忆和人格档案，并在消息下方展示来源依据。当前仍是 deterministic mock 对话。
        </p>
        <AiReminder />
      </header>

      {state === "signedOut" ? <SignedOutState /> : null}
      {state === "loading" || state === "checking" ? <Notice text="正在加载对话..." /> : null}
      {state === "error" ? <Notice text={error ?? "无法加载对话。"} /> : null}

      {state === "ready" && persona && conversation ? (
        <div className="mt-8 grid gap-6 lg:grid-cols-[0.75fr_1.25fr]">
          <aside className="grid content-between gap-5">
            {showChatAvatar ? (
              <div className="grid gap-2">
                <AvatarPreview
                  model={selectedAvatarModel}
                  mouthActive={isAvatarMouthActive}
                  className="min-h-[18rem] rounded-[1.5rem]"
                  canvasClassName="h-[18rem]"
                />
                <p className="text-xs leading-6 text-memoryText/60">
                  播放 TA 的语音回复时，mock 口型会跟随播放状态开合。
                </p>
              </div>
            ) : null}
            <GlassPanel>
              <h2 className="font-serif text-3xl font-semibold text-memoryText">{persona.name}</h2>
              <p className="mt-4 text-sm leading-7 text-memoryText/72">
                她记得你小时候的模样，也记得那些一起走过的日子。现在，轮到你来听她说心里话。
              </p>
              <div className="mt-5">
                <VoiceWave label={`${persona.name}的声音`} />
              </div>
            </GlassPanel>
            <PaperNote className="rotate-[-2deg]">
              <p className="font-serif text-lg leading-8">
                可以从一句：
                <br />
                「外婆，我今天很想你」
                <br />
                开始。
              </p>
            </PaperNote>
            <GlassPanel>
              <h2 className="text-lg font-semibold text-memoryText">当前设定</h2>
            <dl className="mt-5 grid gap-4 text-sm">
              <Detail label="TA 对你的称呼" value={persona.user_nickname_by_persona} />
              <Detail label="你们的关系" value={persona.relationship_to_user} />
              <Detail label="说话风格" value={persona.speaking_style} />
              <Detail label="情绪方式" value={persona.emotional_style} />
              <Detail label="语音" value="可用已上传音频发送 mock 语音消息" />
              <Detail
                label="数字人"
                value={
                  showChatAvatar
                    ? "已接入对话侧 mock 预览，播放语音回复时口型跟随音频状态开合"
                    : "可在 3D 形象页选择默认/mock 头像或生成任务"
                }
              />
            </dl>
            </GlassPanel>
          </aside>

          <GlassPanel className="p-4 sm:p-5">
            {error ? <Alert tone="error" text={error} /> : null}
            {notice ? <Alert tone="success" text={notice} /> : null}

            {messages.length === 0 ? (
              <p className="rounded-2xl bg-memoryPaper/75 p-4 text-sm text-memoryText/70">
                现在可以和 TA 说话了。可以从一句「外婆，我今天很想你」开始。
              </p>
            ) : (
              <div className="grid max-h-[36rem] gap-4 overflow-y-auto pr-1">
                {messages.map((message) => (
                  <MessageCard
                    key={message.id}
                    message={message}
                    onCorrect={handleCorrection}
                    onAudioPlay={setPlayingAudioMessageId}
                    onAudioStop={(messageId) =>
                      setPlayingAudioMessageId((current) =>
                        current === messageId ? null : current
                      )
                    }
                  />
                ))}
              </div>
            )}

            <form onSubmit={handleSend} className="mt-5 grid gap-3">
              <label className="text-sm font-semibold text-memoryText" htmlFor="chat-message">
                想说的话
              </label>
              <textarea
                id="chat-message"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                rows={4}
                className="w-full rounded-2xl border border-memoryLine/80 bg-white/74 px-4 py-3 text-sm leading-7 text-memoryText outline-none focus:border-memoryAccent focus:ring-4 focus:ring-memoryAccent/20"
                placeholder="外婆，我今天很想你。"
              />
              <button
                type="submit"
                disabled={sending || isBlankChatText(draft)}
                className="memory-button w-full rounded-2xl bg-memoryAccent px-5 py-3 text-sm font-semibold text-white shadow-warm disabled:cursor-not-allowed disabled:bg-memoryText/30 md:w-fit"
              >
                {sending ? "正在发送..." : "发送"}
              </button>
            </form>

            <div className="mt-6 rounded-[1.5rem] border border-memoryLine/60 bg-memoryPaper/70 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-sm font-semibold text-memoryText">语音消息</h2>
                  <p className="mt-1 text-sm leading-6 text-memoryText/70">
                    可以直接录音并上传，也可以选择已上传音频资料。当前仍使用 mock ASR/TTS。
                  </p>
                </div>
                <Link
                  href={ROUTES.personaVoice(persona.id)}
                  className="rounded-2xl border border-memoryLine/80 bg-white/72 px-3 py-2 text-sm font-semibold text-memoryText"
                >
                  声音设置
                </Link>
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={handleStartRecording}
                  disabled={recordingState !== "idle" || sendingVoice}
                  className="rounded-2xl border border-memoryLine/80 bg-white/72 px-4 py-2.5 text-sm font-semibold text-memoryText disabled:cursor-not-allowed disabled:text-memoryText/40"
                >
                  开始录音
                </button>
                <button
                  type="button"
                  onClick={handleStopRecording}
                  disabled={recordingState !== "recording"}
                  className="rounded-2xl border border-memoryLine/80 bg-white/72 px-4 py-2.5 text-sm font-semibold text-memoryText disabled:cursor-not-allowed disabled:text-memoryText/40"
                >
                  {recordingState === "uploading" ? "正在上传录音..." : "停止并上传"}
                </button>
              </div>
              <label className="mt-4 block text-sm font-semibold text-memoryText" htmlFor="voice-material">
                选择音频资料
              </label>
              <select
                id="voice-material"
                value={selectedAudioMaterialId}
                onChange={(event) => setSelectedAudioMaterialId(event.target.value)}
                className="mt-2 w-full rounded-2xl border border-memoryLine/80 bg-white/74 px-4 py-3 text-sm text-memoryText outline-none focus:border-memoryAccent focus:ring-4 focus:ring-memoryAccent/20"
              >
                <option value="">暂无可用音频资料</option>
                {audioMaterials.map((material) => (
                  <option key={material.id} value={material.id}>
                    {material.file_name || material.user_description || material.id}
                  </option>
                ))}
              </select>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={handleSendVoice}
                  disabled={sendingVoice || !selectedAudioMaterialId}
                  className="memory-button rounded-2xl bg-memoryAccent px-5 py-3 text-sm font-semibold text-white shadow-warm disabled:cursor-not-allowed disabled:bg-memoryText/30"
                >
                  {sendingVoice ? "正在发送语音..." : "发送语音消息"}
                </button>
                <Link
                  href={ROUTES.personaUploads(persona.id)}
                  className="rounded-2xl border border-memoryLine/80 bg-white/72 px-5 py-3 text-sm font-semibold text-memoryText"
                >
                  上传音频
                </Link>
              </div>
            </div>
          </GlassPanel>
        </div>
      ) : null}
      </MemoryContainer>
    </MemoryShell>
  );
}

async function loadChat(personaId: string): Promise<{
  persona: PersonaRead;
  conversation: ConversationRead;
  messages: MessageRead[];
  audioMaterials: SourceMaterialRead[];
  avatarConfig: AvatarConfigResponse;
}> {
  const [persona, materials, avatarConfig] = await Promise.all([
    getPersona(personaId),
    listMaterials(personaId),
    getAvatarConfig(personaId)
  ]);
  const conversations = await listConversations(personaId);
  const conversation =
    conversations[0] ?? (await createConversation(personaId, `和${persona.name}的对话`));
  const messages = await listMessages(conversation.id);
  return {
    persona,
    conversation,
    messages,
    audioMaterials: materials.filter((material) => material.file_type === "audio"),
    avatarConfig
  };
}

function MessageCard({
  message,
  onCorrect,
  onAudioPlay,
  onAudioStop
}: {
  message: MessageRead;
  onCorrect: (
    message: MessageRead,
    citation: MessageCitationRead,
    content: string
  ) => Promise<void>;
  onAudioPlay?: (messageId: string) => void;
  onAudioStop?: (messageId: string) => void;
}) {
  const [correctionTextByCitation, setCorrectionTextByCitation] = useState<
    Record<string, string>
  >({});
  const isPersona = message.role === "persona";

  return (
    <article
      className={`chat-pop rounded-[1.5rem] border p-4 shadow-soft ${
        isPersona
          ? "mr-auto max-w-[88%] border-memoryLine/70 bg-white/78"
          : "ml-auto max-w-[88%] border-memoryAccent/25 bg-memoryWarm/82"
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-memoryText">
          {messageRoleLabel(message.role)}
        </p>
        <time className="text-xs text-memoryText/50">{formatDate(message.created_at)}</time>
      </div>
      <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-memoryText">
        {message.content}
      </p>
      {hasPlayableAudio(message) ? (
        <div className="mt-4 rounded-2xl bg-white/74 p-3">
          <p className="text-xs font-semibold tracking-[0.08em] text-memoryAccent">
            语音回复
          </p>
          <audio
            className="mt-3 w-full"
            controls
            src={message.audio_url ?? undefined}
            onPlay={() => onAudioPlay?.(message.id)}
            onPause={() => onAudioStop?.(message.id)}
            onEnded={() => onAudioStop?.(message.id)}
          >
            <track kind="captions" />
          </audio>
        </div>
      ) : null}

      {isPersona ? (
        <div className="mt-4 border-t border-memoryLine/60 pt-4">
          <p className="text-xs font-semibold tracking-[0.08em] text-memoryAccent">
            回复依据
          </p>
          {message.citations.length === 0 ? (
            <p className="mt-2 text-sm text-memoryText/60">
              这条回复没有使用来源记忆。
            </p>
          ) : (
            <div className="mt-3 grid gap-3">
              {message.citations.map((citation) => (
                <div key={citation.id} className="rounded-2xl bg-white/74 p-3">
                  <p className="text-xs font-semibold text-memoryText/60">
                    {citationSummary(citation)}
                  </p>
                  {citation.quote ? (
                    <p className="mt-2 text-sm leading-6 text-memoryText">{citation.quote}</p>
                  ) : null}
                  {citation.memory_card_id ? (
                    <div className="mt-3 grid gap-2">
                      <label className="text-xs font-semibold text-memoryText/60">
                        修正这条记忆
                      </label>
                      <textarea
                        value={correctionTextByCitation[citation.id] ?? citation.quote ?? ""}
                        onChange={(event) =>
                          setCorrectionTextByCitation({
                            ...correctionTextByCitation,
                            [citation.id]: event.target.value
                          })
                        }
                        rows={3}
                        className="w-full rounded-2xl border border-memoryLine/80 bg-white/74 px-4 py-3 text-sm leading-6 text-memoryText outline-none focus:border-memoryAccent focus:ring-4 focus:ring-memoryAccent/20"
                      />
                      <button
                        type="button"
                        onClick={() =>
                          onCorrect(
                            message,
                            citation,
                            correctionTextByCitation[citation.id] ??
                              citation.quote ??
                              ""
                          )
                        }
                        className="rounded-2xl border border-memoryLine/80 bg-white/72 px-4 py-2.5 text-sm font-semibold text-memoryText md:w-fit"
                      >
                        保存为修正记忆
                      </button>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </article>
  );
}

function SignedOutState() {
  return (
    <GlassPanel className="mt-8 max-w-3xl">
      <h2 className="font-serif text-2xl font-semibold text-memoryText">需要先进入记忆空间</h2>
      <p className="mt-2 max-w-2xl text-sm leading-7 text-memoryText/70">
        可以免注册体验外婆示例，或登录已有账号继续私有对话。
      </p>
      <div className="mt-5 flex flex-wrap gap-3">
        <DemoEntry label="立即体验示例" />
        <Link
          href={ROUTES.login}
          className="rounded-2xl border border-memoryLine/80 bg-white/72 px-5 py-3 text-sm font-semibold text-memoryText shadow-soft"
        >
          登录已有账号
        </Link>
      </div>
    </GlassPanel>
  );
}

function Detail({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="font-semibold text-memoryText/60">{label}</dt>
      <dd className="mt-1 whitespace-pre-wrap leading-6 text-memoryText">
        {value || "未设置"}
      </dd>
    </div>
  );
}

function Notice({ text }: { text: string }) {
  return (
    <GlassPanel className="mt-8 text-sm leading-7 text-memoryText/72">
      {text}
    </GlassPanel>
  );
}

function Alert({ tone, text }: { tone: "error" | "success"; text: string }) {
  const color =
    tone === "error"
      ? "text-red-700 bg-red-50"
      : "text-memoryAccentDark bg-memoryWarm/70";
  return <div className={`mb-4 rounded-2xl p-3 text-sm ${color}`}>{text}</div>;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}
