"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Camera,
  CameraOff,
  Hand,
  LoaderCircle,
  MessageCircle,
  Mic2,
  Send,
  Star,
  Video,
  Volume2
} from "lucide-react";
import { ConversationWorkspace, ChatComposer } from "@/src/components/ConversationWorkspace";
import { PersonaBackLink } from "@/src/components/PersonaBackLink";
import {
  PlanetStar,
  StarButton,
  StarNav,
  StarPanel,
  StarShell
} from "@/src/components/StarSite";
import { AvatarStage } from "@/src/components/AvatarStage";
import { ensureDemoSession } from "@/src/lib/auth";
import {
  AvatarConfigResponse,
  getAvatarConfig,
  getAvatarDisplaySource
} from "@/src/lib/avatar";
import {
  buildOptimisticUserMessage,
  buildPendingPersonaThinkingMessage,
  ConversationRead,
  createConversation,
  hasPlayableAudio,
  isAvatarMouthActive,
  isBlankChatText,
  isPendingPersonaThinking,
  listConversations,
  listMessages,
  MessageRead,
  personaMessageLabel,
  sendMessage,
  sendVoiceMessage
} from "@/src/lib/chat";
import {
  acceptGestureSignal,
  createGestureRecognizer,
  gestureSignalFromRecognizerResult,
  gestureStatusLabel,
  motionIntentForGesture,
  type GestureRecognizerInstance,
  type GestureSignal,
  type MotionIntent
} from "@/src/lib/gesture";
import { uploadMaterials } from "@/src/lib/materials";
import { getPersona, PersonaRead } from "@/src/lib/persona";
import { ROUTES } from "@/src/lib/routes";
import {
  getVoiceConfig,
  hasChatReadyVoiceConfig,
  VoiceConfigResponse,
  voiceSourceLabel
} from "@/src/lib/voice";

type PageState = "checking" | "loading" | "ready" | "error";
type InteractionMode = "text" | "gesture" | "voice";

const INTERACTION_MODES: Array<{
  id: InteractionMode;
  label: string;
  icon: typeof MessageCircle;
}> = [
  { id: "text", label: "文字对话", icon: MessageCircle },
  { id: "gesture", label: "视频手势互动", icon: Hand },
  { id: "voice", label: "语音对话", icon: Mic2 }
];

const CHAT_QUICK_PROMPTS = [
  "我今天很想你。",
  "你还记得我们一起过生日吗？",
  "你能给我讲一个以前的故事吗？",
  "我最近有点累，你能鼓励我一下吗？"
] as const;

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
  const [avatarConfig, setAvatarConfig] = useState<AvatarConfigResponse | null>(null);
  const [voiceConfig, setVoiceConfig] = useState<VoiceConfigResponse | null>(null);
  const [voiceReplyAudio, setVoiceReplyAudio] = useState<{
    messageId: string;
    audioUrl: string;
  } | null>(null);
  const [mode, setMode] = useState<InteractionMode>("text");
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);
  const [motionIntent, setMotionIntent] = useState<MotionIntent>("idle");
  const avatarMotionIntent: MotionIntent = playingMessageId
    ? "speaking"
    : sending
      ? "thinking"
      : motionIntent;

  useEffect(() => {
    if (!personaId) {
      setError("缺少人物 ID。");
      setState("error");
      return;
    }

    let isCurrent = true;
    setState("loading");
    ensureDemoSession()
      .then(() => loadChat(personaId))
      .then((loaded) => {
        if (!isCurrent) {
          return;
        }
        setPersona(loaded.persona);
        setConversation(loaded.conversation);
        setMessages(loaded.messages);
        setAvatarConfig(loaded.avatarConfig);
        setVoiceConfig(loaded.voiceConfig);
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
    };
  }, [personaId]);

  useEffect(() => {
    if (!personaId || mode !== "voice") {
      return;
    }

    let isCurrent = true;
    getVoiceConfig(personaId)
      .then((config) => {
        if (isCurrent) {
          setVoiceConfig(config);
        }
      })
      .catch(() => {
        if (isCurrent) {
          setVoiceConfig(null);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [mode, personaId]);

  async function refreshMessages(currentConversation: ConversationRead) {
    setMessages(await listMessages(currentConversation.id));
  }

  async function handleVoiceMessageSent(reply: MessageRead) {
    if (!conversation) {
      return;
    }
    await refreshMessages(conversation);
    if (reply.audio_url?.trim()) {
      setVoiceReplyAudio({ messageId: reply.id, audioUrl: reply.audio_url });
    }
  }

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedDraft = draft.trim();
    if (!conversation || isBlankChatText(trimmedDraft)) {
      return;
    }

    setSending(true);
    setError(null);
    const now = new Date();
    const optimisticUserMessage = buildOptimisticUserMessage(conversation.id, trimmedDraft, now);
    const pendingPersonaMessage = buildPendingPersonaThinkingMessage(
      conversation.id,
      persona?.name ?? "TA",
      now
    );
    setMessages((currentMessages) => [
      ...currentMessages,
      optimisticUserMessage,
      pendingPersonaMessage
    ]);
    setDraft("");
    try {
      await sendMessage(conversation.id, trimmedDraft);
      await refreshMessages(conversation);
    } catch (caught) {
      setMessages((currentMessages) =>
        currentMessages.filter(
          (message) =>
            message.id !== optimisticUserMessage.id && message.id !== pendingPersonaMessage.id
        )
      );
      setDraft(trimmedDraft);
      setError(caught instanceof Error ? caught.message : "无法发送消息。");
    } finally {
      setSending(false);
    }
  }

  return (
    <StarShell>
      <StarNav />
      <main className="mx-auto w-full max-w-7xl px-5 pb-10 sm:px-8 lg:px-10">
        {personaId ? <PersonaBackLink personaId={personaId} /> : null}

        <section className="relative hidden overflow-hidden pt-1 md:block">
          <div className="pointer-events-none absolute -right-16 -top-20 hidden opacity-90 lg:block">
            <PlanetStar />
          </div>
          <div className="relative z-10 max-w-3xl">
            <p className="inline-flex items-center gap-2 text-sm font-bold text-starGold">
              <Star className="h-4 w-4 fill-current" aria-hidden="true" />
              审核完成，星星已点亮
            </p>
            <h1 className="mt-2 font-serif text-4xl font-bold leading-tight text-starGold sm:text-5xl">
              与TA的星星对话
            </h1>
            <p className="mt-3 max-w-2xl text-sm font-semibold leading-7 text-starMist/72">
              在这片星空里，听TA继续说话。你可以文字对话，也可以从视频手势互动进入语音对话。
            </p>
          </div>
        </section>

        {state === "loading" || state === "checking" ? <Notice text="正在连接这颗星星..." /> : null}
        {state === "error" ? <Notice text={error ?? "无法加载对话。"} /> : null}

        {state === "ready" && persona && conversation ? (
          <div className="relative z-10 mt-6 grid gap-4">
            <ConversationWorkspace
              modeBar={
                <div className="grid grid-cols-3 gap-1 overflow-hidden rounded-2xl border border-starGold/12 bg-indigo-950/36 p-1">
                  {INTERACTION_MODES.map((item) => (
                    <ModeButton
                      key={item.id}
                      active={mode === item.id}
                      icon={item.icon}
                      onClick={() => setMode(item.id)}
                    >
                      {item.label}
                    </ModeButton>
                  ))}
                </div>
              }
              scrollKey={`${mode}:${messages.length}:${sending}`}
              composer={
                <ChatComposer
                  value={draft}
                  onValueChange={setDraft}
                  onSubmit={handleSend}
                  placeholder={`今天想和${persona.name}说些什么？`}
                  disabled={sending || isBlankChatText(draft)}
                  submitLabel={sending ? "发送中" : undefined}
                  quickPrompts={mode === "text" ? CHAT_QUICK_PROMPTS : undefined}
                  rightAction={
                    <button
                      type="button"
                      className="inline-flex h-[3.3rem] w-[3.3rem] shrink-0 items-center justify-center rounded-full border border-sky-200/18 bg-sky-300/10 text-sky-100 transition hover:bg-sky-300/16"
                      aria-label="语音消息"
                      onClick={() => setMode("voice")}
                    >
                      <Mic2 className="h-5 w-5" aria-hidden="true" />
                    </button>
                  }
                />
              }
              avatar={
                <AvatarStage
                  personaName={persona.name}
                  source={getAvatarDisplaySource(avatarConfig)}
                  mouthActive={isAvatarMouthActive(messages, playingMessageId)}
                  motionIntent={avatarMotionIntent}
                  className="h-full xl:min-h-[37rem]"
                  subtitle={persona.short_bio || "这颗星星正在慢慢收集 TA 的故事。"}
                />
              }
            >
              {error ? (
                <p className="mb-4 rounded-2xl border border-rose-300/20 bg-rose-500/15 p-3 text-sm font-semibold text-rose-100">
                  {error}
                </p>
              ) : null}
              {mode === "text" ? (
                <ChatSurface
                  messages={messages}
                  persona={persona}
                  playingMessageId={playingMessageId}
                  onAudioPlay={setPlayingMessageId}
                  onAudioStop={(messageId) =>
                    setPlayingMessageId((currentId) =>
                      currentId === messageId ? null : currentId
                    )
                  }
                />
              ) : null}
              {mode === "gesture" ? (
                <GestureSurface
                  personaName={persona.name}
                  onMotionIntentChange={setMotionIntent}
                  onVoice={() => setMode("voice")}
                />
              ) : null}
              {mode === "voice" ? (
                <VoiceSurface
                  personaId={persona.id}
                  personaName={persona.name}
                  conversation={conversation}
                  voiceConfig={voiceConfig}
                  voiceReplyAudio={voiceReplyAudio}
                  busy={sending}
                  onBusyChange={setSending}
                  onError={setError}
                  onVoiceMessageSent={handleVoiceMessageSent}
                  onAudioPlay={setPlayingMessageId}
                  onAudioStop={(messageId) =>
                    setPlayingMessageId((currentId) =>
                      currentId === messageId ? null : currentId
                    )
                  }
                />
              ) : null}
            </ConversationWorkspace>
          </div>
        ) : null}

        {false && state === "ready" && persona && conversation ? (
          <div className="relative z-10 mt-6">
            <div className="grid gap-5 md:grid-cols-[minmax(0,0.66fr)_minmax(20rem,0.34fr)]">
              <StarPanel className="overflow-hidden p-0">
                <div className="border-b border-white/8 bg-indigo-950/24 p-4 sm:p-5">
                  <div className="grid grid-cols-3 gap-1 overflow-hidden rounded-2xl border border-starGold/12 bg-indigo-950/36 p-1">
                    {INTERACTION_MODES.map((item) => (
                      <ModeButton
                        key={item.id}
                        active={mode === item.id}
                        icon={item.icon}
                        onClick={() => setMode(item.id)}
                      >
                        {item.label}
                      </ModeButton>
                    ))}
                  </div>
                </div>

                <div className="min-h-[30rem]">
                  {mode === "text" ? (
                    <ChatSurface
                      messages={messages}
                      persona={persona!}
                      playingMessageId={playingMessageId}
                      onAudioPlay={setPlayingMessageId}
                      onAudioStop={(messageId) =>
                        setPlayingMessageId((currentId) => (currentId === messageId ? null : currentId))
                      }
                    />
                  ) : null}
                  {mode === "gesture" ? (
                    <GestureSurface
                      personaName={persona!.name}
                      onMotionIntentChange={setMotionIntent}
                      onVoice={() => setMode("voice")}
                    />
                  ) : null}
                  {mode === "voice" ? (
                    <VoiceSurface
                      personaId={persona!.id}
                      personaName={persona!.name}
                      conversation={conversation!}
                      voiceConfig={voiceConfig}
                      voiceReplyAudio={voiceReplyAudio}
                      busy={sending}
                      onBusyChange={setSending}
                      onError={setError}
                      onVoiceMessageSent={handleVoiceMessageSent}
                      onAudioPlay={setPlayingMessageId}
                      onAudioStop={(messageId) =>
                        setPlayingMessageId((currentId) => (currentId === messageId ? null : currentId))
                      }
                    />
                  ) : null}
                </div>

                {error ? (
                  <p className="mx-4 mb-4 rounded-2xl border border-rose-300/20 bg-rose-500/15 p-3 text-sm font-semibold text-rose-100 sm:mx-5">
                    {error}
                  </p>
                ) : null}

                <form onSubmit={handleSend} className="flex gap-3 border-t border-white/8 p-4 sm:p-5">
                  <input
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    className="star-input min-h-[3.3rem] flex-1"
                    placeholder={`今天想和${persona!.name}说些什么？`}
                  />
                  <StarButton
                    type="submit"
                    disabled={sending || isBlankChatText(draft)}
                    className="min-w-20 px-5 sm:min-w-24 sm:px-6"
                  >
                    {sending ? "发送中" : <Send className="h-5 w-5" />}
                  </StarButton>
                </form>
              </StarPanel>

              <AvatarStage
                personaName={persona!.name}
                source={getAvatarDisplaySource(avatarConfig)}
                mouthActive={isAvatarMouthActive(messages, playingMessageId)}
                motionIntent={avatarMotionIntent}
                className="md:min-h-[37rem]"
                subtitle={persona!.short_bio || "这颗星星正在慢慢收集TA的故事。"}
              />
            </div>
          </div>
        ) : null}
      </main>
    </StarShell>
  );
}

async function loadChat(personaId: string): Promise<{
  persona: PersonaRead;
  conversation: ConversationRead;
  messages: MessageRead[];
  avatarConfig: AvatarConfigResponse | null;
  voiceConfig: VoiceConfigResponse | null;
}> {
  const persona = await getPersona(personaId);
  const conversations = await listConversations(personaId, "chat");
  const conversation =
    conversations[0] ?? (await createConversation(personaId, `和${persona.name}的对话`, "chat"));
  const [messages, avatarConfig, voiceConfig] = await Promise.all([
    listMessages(conversation.id),
    getAvatarConfig(personaId).catch(() => null),
    getVoiceConfig(personaId).catch(() => null)
  ]);
  return { persona, conversation, messages, avatarConfig, voiceConfig };
}

function ModeButton({
  active,
  icon: Icon,
  onClick,
  children
}: {
  active: boolean;
  icon: typeof MessageCircle;
  onClick: () => void;
  children: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex min-h-12 items-center justify-center gap-2 rounded-xl px-2 py-3 text-xs font-bold transition sm:text-sm ${
        active
          ? "bg-gradient-to-r from-starPeach/75 to-starGold/55 text-starCream shadow-[0_0_24px_rgba(255,210,138,0.22)]"
          : "text-starMist/58 hover:text-starCream"
      }`}
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span className="leading-tight">{children}</span>
    </button>
  );
}

function ChatSurface({
  messages,
  persona,
  playingMessageId,
  onAudioPlay,
  onAudioStop
}: {
  messages: MessageRead[];
  persona: PersonaRead;
  playingMessageId: string | null;
  onAudioPlay: (messageId: string) => void;
  onAudioStop: (messageId: string) => void;
}) {
  return (
    <div className="min-h-full">
      {messages.length === 0 ? (
        <div className="grid min-h-[23rem] place-items-center text-center">
          <div>
            <Star className="mx-auto h-12 w-12 fill-current text-starGold" />
            <p className="mt-4 text-sm font-semibold leading-7 text-starMist/70">
              现在可以和{persona.name}说话了。
              <br />
              可以从一句“我今天很想你”开始。
            </p>
          </div>
        </div>
      ) : (
        <div className="grid gap-5">
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              personaName={persona.name}
              isPlaying={playingMessageId === message.id}
              onAudioPlay={onAudioPlay}
              onAudioStop={onAudioStop}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function GestureSurface({
  personaName,
  onMotionIntentChange,
  onVoice
}: {
  personaName: string;
  onMotionIntentChange: (intent: MotionIntent) => void;
  onVoice: () => void;
}) {
  const [cameraState, setCameraState] = useState<"idle" | "starting" | "running" | "error">(
    "idle"
  );
  const [statusText, setStatusText] = useState("点击后开启摄像头，本地识别手势。");
  const [lastSignal, setLastSignal] = useState<GestureSignal>("none");
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recognizerRef = useRef<GestureRecognizerInstance | null>(null);
  const frameRef = useRef<number | null>(null);
  const handXHistoryRef = useRef<number[]>([]);
  const lastSignalRef = useRef<GestureSignal | null>(null);
  const lastTriggeredAtRef = useRef(0);
  const presenceStartedAtRef = useRef<number | null>(null);

  const stopGestureCamera = useCallback(
    (updateState = true) => {
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
        frameRef.current = null;
      }
      recognizerRef.current?.close?.();
      recognizerRef.current = null;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
      handXHistoryRef.current = [];
      presenceStartedAtRef.current = null;
      if (updateState) {
        setCameraState("idle");
        setStatusText("摄像头已停止。");
        onMotionIntentChange("idle");
      }
    },
    [onMotionIntentChange]
  );

  useEffect(() => {
    return () => {
      stopGestureCamera(false);
    };
  }, [stopGestureCamera]);

  async function startGestureCamera() {
    if (cameraState === "starting" || cameraState === "running") {
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraState("error");
      setStatusText("当前浏览器不支持摄像头访问，请换用支持 getUserMedia 的浏览器。");
      return;
    }

    setCameraState("starting");
    setStatusText("正在打开摄像头并加载手势识别模型...");
    setLastSignal("none");
    handXHistoryRef.current = [];
    lastSignalRef.current = null;
    lastTriggeredAtRef.current = 0;
    presenceStartedAtRef.current = null;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user" },
        audio: false
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      recognizerRef.current = await createGestureRecognizer();
      setCameraState("running");
      setStatusText("摄像头已开启，本地识别，不上传摄像头画面。");
      onMotionIntentChange("attention");
      frameRef.current = requestAnimationFrame(processGestureFrame);
    } catch (caught) {
      stopGestureCamera(false);
      setCameraState("error");
      const denied =
        caught instanceof DOMException && caught.name === "NotAllowedError";
      setStatusText(
        denied
          ? "摄像头权限未开启，请允许浏览器摄像头权限后重试。"
          : caught instanceof Error
            ? caught.message
            : "无法开启视频手势互动。"
      );
    }
  }

  function processGestureFrame(nowMs: number) {
    const video = videoRef.current;
    const recognizer = recognizerRef.current;
    if (!video || !recognizer) {
      return;
    }

    if (video.readyState >= 2) {
      const result = recognizer.recognizeForVideo(video, nowMs);
      const signal = gestureSignalFromRecognizerResult(result, handXHistoryRef.current);
      if (signal) {
        triggerGestureSignal(signal, nowMs);
        presenceStartedAtRef.current = nowMs;
      } else {
        const presenceStartedAt = presenceStartedAtRef.current ?? nowMs;
        presenceStartedAtRef.current = presenceStartedAt;
        if (nowMs - presenceStartedAt > 2000) {
          triggerGestureSignal("presence", nowMs);
        }
      }
    }

    frameRef.current = requestAnimationFrame(processGestureFrame);
  }

  function triggerGestureSignal(signal: GestureSignal, nowMs: number) {
    if (
      !acceptGestureSignal({
        signal,
        lastSignal: lastSignalRef.current,
        nowMs,
        lastTriggeredAtMs: lastTriggeredAtRef.current
      })
    ) {
      return;
    }

    lastSignalRef.current = signal;
    lastTriggeredAtRef.current = nowMs;
    setLastSignal(signal);
    setStatusText(`${gestureStatusLabel(signal)}，数字人已给出动作反馈。`);
    onMotionIntentChange(motionIntentForGesture(signal));
  }

  const isCameraRunning = cameraState === "running";

  return (
    <div className="grid min-h-[25rem] place-items-center p-4 text-center sm:p-6">
      <div className="w-full max-w-2xl">
        <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-black/26 shadow-[0_18px_54px_rgba(0,0,0,0.28)]">
          <video
            ref={videoRef}
            className={`aspect-video w-full object-cover ${isCameraRunning ? "block" : "hidden"}`}
            autoPlay
            muted
            playsInline
          />
          {!isCameraRunning ? (
            <div className="grid aspect-video place-items-center bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.26),_rgba(9,12,42,0.88))]">
              <div>
                <div className="mx-auto grid h-20 w-20 place-items-center rounded-3xl bg-violet-400/20 text-violet-100 shadow-[0_0_42px_rgba(181,128,255,0.32)]">
                  {cameraState === "starting" ? (
                    <LoaderCircle className="h-10 w-10 animate-spin" aria-hidden="true" />
                  ) : (
                    <Video className="h-10 w-10" aria-hidden="true" />
                  )}
                </div>
                <p className="mt-4 text-xs font-bold text-starMist/60">
                  本地识别，不上传摄像头画面
                </p>
              </div>
            </div>
          ) : null}
        </div>
        <h2 className="mt-5 font-serif text-2xl font-bold text-starGold">视频手势互动</h2>
        <p className="mt-3 text-sm font-semibold leading-7 text-starMist/68">
          面向摄像头停留、挥手、张开手掌或握拳，{personaName}会用 GLB 动作或基础动作回应。
        </p>
        <div className="mt-4 grid gap-3 text-left sm:grid-cols-2">
          <div className="rounded-2xl border border-white/8 bg-white/6 p-4">
            <p className="text-xs font-bold text-starMist/46">识别状态</p>
            <p className="mt-2 text-sm font-bold leading-6 text-starCream">{statusText}</p>
          </div>
          <div className="rounded-2xl border border-white/8 bg-white/6 p-4">
            <p className="text-xs font-bold text-starMist/46">最近手势</p>
            <p className="mt-2 text-sm font-bold leading-6 text-starGold">
              {gestureStatusLabel(lastSignal)}
            </p>
          </div>
        </div>
        <p className="mt-3 text-xs font-semibold leading-6 text-starMist/52">
          如果当前 GLB 不含对应动画，会自动使用整体转身、点头或轻摆作为基础反馈。
        </p>
        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:justify-center">
          <button
            type="button"
            onClick={() => {
              if (isCameraRunning) {
                stopGestureCamera();
              } else {
                void startGestureCamera();
              }
            }}
            disabled={cameraState === "starting"}
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full border border-starGold/24 bg-starGold/12 px-5 py-3 text-sm font-bold text-starCream transition hover:bg-starGold/18 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isCameraRunning ? (
              <CameraOff className="h-4 w-4" aria-hidden="true" />
            ) : cameraState === "starting" ? (
              <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Camera className="h-4 w-4" aria-hidden="true" />
            )}
            {isCameraRunning ? "停止摄像头" : "开始摄像头"}
          </button>
          <button
            type="button"
            onClick={onVoice}
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full border border-starGold/24 bg-starGold/12 px-5 py-3 text-sm font-bold text-starCream transition hover:bg-starGold/18"
          >
            进入语音对话
            <Mic2 className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}

type VoiceStep = "idle" | "recording" | "uploading" | "thinking";

function VoiceSurface({
  personaId,
  personaName,
  conversation,
  voiceConfig,
  voiceReplyAudio,
  busy,
  onBusyChange,
  onError,
  onVoiceMessageSent,
  onAudioPlay,
  onAudioStop
}: {
  personaId: string;
  personaName: string;
  conversation: ConversationRead;
  voiceConfig: VoiceConfigResponse | null;
  voiceReplyAudio: { messageId: string; audioUrl: string } | null;
  busy: boolean;
  onBusyChange: (busy: boolean) => void;
  onError: (message: string | null) => void;
  onVoiceMessageSent: (reply: MessageRead) => Promise<void>;
  onAudioPlay: (messageId: string) => void;
  onAudioStop: (messageId: string) => void;
}) {
  const [voiceStep, setVoiceStep] = useState<VoiceStep>("idle");
  const [recording, setRecording] = useState(false);
  const [autoplayNotice, setAutoplayNotice] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const voiceReplyAudioRef = useRef<HTMLAudioElement | null>(null);
  const isVoiceReady = hasChatReadyVoiceConfig(voiceConfig);

  useEffect(() => {
    return () => {
      const recorder = mediaRecorderRef.current;
      if (recorder) {
        recorder.ondataavailable = null;
        recorder.onstop = null;
        if (recorder.state === "recording") {
          recorder.stop();
        }
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
      onBusyChange(false);
    };
  }, [onBusyChange]);

  useEffect(() => {
    if (!voiceReplyAudio) {
      return;
    }

    setAutoplayNotice(null);
    const audio = voiceReplyAudioRef.current;
    if (!audio) {
      return;
    }
    audio.currentTime = 0;
    void audio.play().catch(() => {
      setAutoplayNotice("已生成语音回复，可点击播放。");
    });
  }, [voiceReplyAudio]);

  async function startRecording() {
    if (!isVoiceReady || busy) {
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      onError("当前浏览器不支持语音录制，请换用支持麦克风录音的浏览器。");
      return;
    }

    onError(null);
    onBusyChange(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      streamRef.current = stream;
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      recorder.onstop = () => {
        void handleRecordedAudio(mimeType || "audio/webm");
      };
      recorder.start();
      setRecording(true);
      setVoiceStep("recording");
    } catch (caught) {
      onBusyChange(false);
      setVoiceStep("idle");
      onError(caught instanceof Error ? caught.message : "无法访问麦克风，请允许浏览器麦克风权限后重试。");
      stopRecordingStream();
    }
  }

  function stopRecording() {
    const recorder = mediaRecorderRef.current;
    if (!recording || !recorder || recorder.state !== "recording") {
      return;
    }
    setRecording(false);
    setVoiceStep("uploading");
    recorder.stop();
  }

  async function handleRecordedAudio(mimeType: string) {
    try {
      const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
      if (audioBlob.size === 0) {
        throw new Error("没有录到声音，请重新录制。");
      }

      const voiceFile = new File([audioBlob], `voice-message-${Date.now()}.webm`, {
        type: mimeType
      });
      setVoiceStep("uploading");
      const materials = await uploadMaterials(personaId, {
        files: [voiceFile],
        user_description: "聊天页语音对话录音"
      });
      const audioMaterial = materials.find((material) => material.file_type === "audio");
      if (!audioMaterial) {
        throw new Error("录音上传后没有生成可用音频资料。");
      }

      setVoiceStep("thinking");
      const reply = await sendVoiceMessage(conversation.id, {
        source_material_id: audioMaterial.id
      });
      await onVoiceMessageSent(reply);
      setVoiceStep("idle");
    } catch (caught) {
      setVoiceStep("idle");
      onError(caught instanceof Error ? caught.message : "无法完成语音对话。");
    } finally {
      audioChunksRef.current = [];
      mediaRecorderRef.current = null;
      stopRecordingStream();
      onBusyChange(false);
    }
  }

  function stopRecordingStream() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }

  const statusText =
    voiceStep === "recording"
      ? "正在录音，再次点击结束"
      : voiceStep === "uploading"
        ? "正在上传录音..."
        : voiceStep === "thinking"
          ? "正在识别语音并生成回复..."
          : `点击后开始和${personaName}语音对话`;

  if (!isVoiceReady) {
    return (
      <div className="grid min-h-[25rem] place-items-center p-6 text-center">
        <div className="max-w-md">
          <div className="mx-auto grid h-20 w-20 place-items-center rounded-3xl bg-starGold/16 text-starGold shadow-[0_0_42px_rgba(255,190,109,0.32)]">
            <Mic2 className="h-10 w-10" aria-hidden="true" />
          </div>
          <h2 className="mt-5 font-serif text-2xl font-bold text-starGold">语音对话</h2>
          <p className="mt-3 text-sm font-semibold leading-7 text-starMist/68">
            需要先为{personaName}配置默认 TTS 或模拟音色，才能开启语音输入和语音回复。
          </p>
          <Link
            href={ROUTES.personaVoice(personaId)}
            className="mt-5 inline-flex items-center justify-center rounded-full border border-starGold/24 bg-starGold/12 px-5 py-3 text-sm font-bold text-starCream transition hover:bg-starGold/18"
          >
            去声音设置配置 TTS
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="grid min-h-[25rem] place-items-center p-6 text-center">
      <div className="w-full max-w-md">
        <div className="mx-auto grid h-20 w-20 place-items-center rounded-3xl bg-starGold/16 text-starGold shadow-[0_0_42px_rgba(255,190,109,0.32)]">
          <Mic2 className="h-10 w-10" aria-hidden="true" />
        </div>
        <h2 className="mt-5 font-serif text-2xl font-bold text-starGold">语音对话</h2>
        <p className="mt-3 rounded-2xl border border-white/8 bg-white/6 px-4 py-3 text-xs font-bold leading-6 text-starMist/68">
          当前语音来源：{voiceSourceLabel(voiceConfig?.selected_voice_model, voiceConfig?.tts_model)}
        </p>
        <button
          type="button"
          onClick={recording ? stopRecording : startRecording}
          disabled={busy && !recording}
          className="mt-5 inline-flex min-h-14 w-full items-center justify-center gap-2 rounded-full border border-starGold/28 bg-starGold/16 px-5 py-3 text-sm font-bold text-starCream transition hover:bg-starGold/22 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {voiceStep === "uploading" || voiceStep === "thinking" ? (
            <LoaderCircle className="h-5 w-5 animate-spin" aria-hidden="true" />
          ) : (
            <Mic2 className="h-5 w-5" aria-hidden="true" />
          )}
          {recording ? "结束语音输入" : "语音输入"}
        </button>
        <p className="mt-3 text-xs font-semibold leading-6 text-starMist/58">{statusText}</p>
        {voiceReplyAudio ? (
          <div className="mt-5 rounded-2xl border border-white/8 bg-white/6 p-3 text-left">
            <p className="mb-2 inline-flex items-center gap-2 text-xs font-bold text-starGold">
              <Volume2 className="h-3.5 w-3.5" aria-hidden="true" />
              TTS 语音回复
            </p>
            <audio
              ref={voiceReplyAudioRef}
              className="w-full"
              controls
              src={voiceReplyAudio.audioUrl}
              onPlay={() => onAudioPlay(voiceReplyAudio.messageId)}
              onPause={() => onAudioStop(voiceReplyAudio.messageId)}
              onEnded={() => onAudioStop(voiceReplyAudio.messageId)}
            >
              <track kind="captions" />
            </audio>
            {autoplayNotice ? (
              <p className="mt-2 text-xs font-semibold text-starMist/52">{autoplayNotice}</p>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  personaName,
  isPlaying,
  onAudioPlay,
  onAudioStop
}: {
  message: MessageRead;
  personaName: string;
  isPlaying: boolean;
  onAudioPlay: (messageId: string) => void;
  onAudioStop: (messageId: string) => void;
}) {
  const isPersona = message.role === "persona";
  return (
    <article className={`flex gap-3 ${isPersona ? "justify-start" : "justify-end"}`}>
      {isPersona ? (
        <span className="mt-1 grid h-11 w-11 shrink-0 place-items-center rounded-full bg-starGold/18 text-starGold">
          <Star className="h-6 w-6 fill-current" />
        </span>
      ) : null}
      <div className={`max-w-[78%] ${isPersona ? "" : "text-right"}`}>
        <p className="mb-2 text-xs font-bold text-starMist/46">
          {isPersona ? personaMessageLabel(personaName) : "我"}
        </p>
        <div
          className={`rounded-2xl px-5 py-4 text-left text-sm font-semibold leading-7 shadow-[0_12px_30px_rgba(0,0,0,0.18)] ${
            isPersona
              ? "bg-indigo-200/10 text-starMist/82"
              : "bg-violet-400/22 text-starCream"
          }`}
        >
          {isPendingPersonaThinking(message) ? (
            <span className="inline-flex items-center gap-2">
              <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
              {message.content}
            </span>
          ) : (
            message.content
          )}
        </div>
        {isPersona && hasPlayableAudio(message) ? (
          <div className="mt-3 rounded-2xl border border-white/8 bg-white/6 p-3">
            <p className="mb-2 inline-flex items-center gap-2 text-xs font-bold text-starGold">
              <Volume2 className="h-3.5 w-3.5" aria-hidden="true" />
              {isPlaying ? "正在播放语音回复" : "语音回复"}
            </p>
            <audio
              className="w-full"
              controls
              src={message.audio_url ?? undefined}
              onPlay={() => onAudioPlay(message.id)}
              onPause={() => onAudioStop(message.id)}
              onEnded={() => onAudioStop(message.id)}
            >
              <track kind="captions" />
            </audio>
          </div>
        ) : null}
        <time className="mt-2 block text-xs text-starMist/34">{formatDate(message.created_at)}</time>
      </div>
    </article>
  );
}

function Notice({ text }: { text: string }) {
  return <StarPanel className="mx-auto mt-8 max-w-3xl p-5 text-center text-starMist/72">{text}</StarPanel>;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}
