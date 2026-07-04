"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  Archive,
  BookOpen,
  Hand,
  Heart,
  HeartHandshake,
  MessageCircle,
  Mic2,
  Send,
  Sparkles,
  Star,
  Video,
  Volume2
} from "lucide-react";
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
  ConversationRead,
  createConversation,
  isBlankChatText,
  listConversations,
  listMessages,
  MessageRead,
  sendMessage
} from "@/src/lib/chat";
import { getPersona, PersonaRead } from "@/src/lib/persona";
import {
  createStory,
  listStories,
  MemoryStoryRead,
  storySourceSummary
} from "@/src/lib/stories";

type PageState = "checking" | "loading" | "ready" | "error";
type InteractionMode = "text" | "gesture" | "voice";
type ExperienceKind = "archive" | "regret" | "wish";

const INTERACTION_MODES: Array<{
  id: InteractionMode;
  label: string;
  icon: typeof MessageCircle;
}> = [
  { id: "text", label: "文字对话", icon: MessageCircle },
  { id: "gesture", label: "视频手势互动", icon: Hand },
  { id: "voice", label: "语音对话", icon: Mic2 }
];

const EXPERIENCE_CARDS: Array<{
  kind: ExperienceKind;
  title: string;
  description: string;
  icon: typeof Archive;
  prompt: string;
  actionLabel: string;
}> = [
  {
    kind: "archive",
    title: "记忆档案馆",
    description:
      "让TA回忆你们的某个故事，模型识别用户上传的信息，找到特别的几段故事来生成回忆型文本进行讲述。",
    icon: Archive,
    prompt: "共同回忆",
    actionLabel: "生成一段回忆"
  },
  {
    kind: "regret",
    title: "遗憾对话室",
    description: "对TA说出你来不及说的话，让未完成的心意被温柔接住。",
    icon: MessageCircle,
    prompt: "我有一些来不及说的话，想现在慢慢告诉你。",
    actionLabel: "开始说给TA听"
  },
  {
    kind: "wish",
    title: "心愿延续系统",
    description: "完成TA未完成的愿望，把思念落成下一步可以继续做的事。",
    icon: HeartHandshake,
    prompt: "你还有没有未完成的心愿？我想替你继续完成一点。",
    actionLabel: "记录一个心愿"
  }
];

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
  const [stories, setStories] = useState<MemoryStoryRead[]>([]);
  const [featuredStory, setFeaturedStory] = useState<MemoryStoryRead | null>(null);
  const [avatarConfig, setAvatarConfig] = useState<AvatarConfigResponse | null>(null);
  const [mode, setMode] = useState<InteractionMode>("text");
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [storyBusy, setStoryBusy] = useState(false);

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
        setStories(loaded.stories);
        setFeaturedStory(loaded.stories[0] ?? null);
        setAvatarConfig(loaded.avatarConfig);
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

  async function refreshMessages(currentConversation: ConversationRead) {
    setMessages(await listMessages(currentConversation.id));
  }

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!conversation || isBlankChatText(draft)) {
      return;
    }

    setSending(true);
    setError(null);
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

  async function handleExperience(kind: ExperienceKind, prompt: string) {
    setError(null);
    if (kind === "archive" && personaId) {
      setStoryBusy(true);
      try {
        const story = await createStory(personaId, prompt);
        setFeaturedStory(story);
        setStories((currentStories) => [story, ...currentStories.filter((item) => item.id !== story.id)]);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "无法生成回忆故事。");
      } finally {
        setStoryBusy(false);
      }
      return;
    }

    setMode("text");
    setDraft(prompt);
  }

  return (
    <StarShell>
      <StarNav />
      <main className="mx-auto w-full max-w-7xl px-5 pb-10 sm:px-8 lg:px-10">
        <section className="relative overflow-hidden pt-1">
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
          <div className="relative z-10 mt-6">
            <div className="grid gap-5 lg:grid-cols-[minmax(0,0.68fr)_minmax(22rem,0.32fr)]">
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

                <div className="grid min-h-[30rem] gap-0 xl:grid-cols-[minmax(0,1fr)_17rem]">
                  <div className="min-h-[25rem]">
                    {mode === "text" ? (
                      <ChatSurface messages={messages} persona={persona} />
                    ) : null}
                    {mode === "gesture" ? (
                      <GestureSurface personaName={persona.name} onVoice={() => setMode("voice")} />
                    ) : null}
                    {mode === "voice" ? <VoiceSurface personaName={persona.name} /> : null}
                  </div>
                  <MemoryStoryPanel
                    story={featuredStory}
                    storyCount={stories.length}
                    isBusy={storyBusy}
                    personaName={persona.name}
                    onGenerate={() => void handleExperience("archive", "共同回忆")}
                  />
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
                    placeholder={`今天想和${persona.name}说些什么？`}
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
                personaName={persona.name}
                source={getAvatarDisplaySource(avatarConfig)}
                className="lg:min-h-[37rem]"
                subtitle={
                  featuredStory
                    ? `当前记忆焦点：${featuredStory.theme} · ${storySourceSummary(featuredStory)}`
                    : persona.short_bio || "这颗星星正在慢慢收集TA的故事。"
                }
              />
            </div>

            <section className="relative z-10 mt-5 grid gap-4 md:grid-cols-3">
              {EXPERIENCE_CARDS.map((card) => (
                <ExperienceCard
                  key={card.title}
                  icon={card.icon}
                  title={card.title}
                  description={card.description}
                  actionLabel={storyBusy && card.kind === "archive" ? "正在生成..." : card.actionLabel}
                  disabled={storyBusy && card.kind === "archive"}
                  onClick={() => void handleExperience(card.kind, card.prompt)}
                />
              ))}
            </section>
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
  stories: MemoryStoryRead[];
  avatarConfig: AvatarConfigResponse | null;
}> {
  const persona = await getPersona(personaId);
  const conversations = await listConversations(personaId);
  const conversation =
    conversations[0] ?? (await createConversation(personaId, `和${persona.name}的对话`));
  const [messages, stories, avatarConfig] = await Promise.all([
    listMessages(conversation.id),
    listStories(personaId).catch(() => []),
    getAvatarConfig(personaId).catch(() => null)
  ]);
  return { persona, conversation, messages, stories, avatarConfig };
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
  persona
}: {
  messages: MessageRead[];
  persona: PersonaRead;
}) {
  return (
    <div className="max-h-[35rem] min-h-[25rem] overflow-y-auto p-4 sm:p-5">
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
            <MessageBubble key={message.id} message={message} personaName={persona.name} />
          ))}
        </div>
      )}
    </div>
  );
}

function GestureSurface({
  personaName,
  onVoice
}: {
  personaName: string;
  onVoice: () => void;
}) {
  return (
    <div className="grid min-h-[25rem] place-items-center p-6 text-center">
      <div className="max-w-md">
        <div className="mx-auto grid h-20 w-20 place-items-center rounded-3xl bg-violet-400/20 text-violet-100 shadow-[0_0_42px_rgba(181,128,255,0.32)]">
          <Video className="h-10 w-10" aria-hidden="true" />
        </div>
        <h2 className="mt-5 font-serif text-2xl font-bold text-starGold">视频手势互动</h2>
        <p className="mt-3 text-sm font-semibold leading-7 text-starMist/68">
          这里会用于和{personaName}进行视频手势互动。识别到你的停留、挥手或点头后，下一步进入语音对话。
        </p>
        <button
          type="button"
          onClick={onVoice}
          className="mt-5 inline-flex items-center justify-center gap-2 rounded-full border border-starGold/24 bg-starGold/12 px-5 py-3 text-sm font-bold text-starCream transition hover:bg-starGold/18"
        >
          进入语音对话
          <Mic2 className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}

function VoiceSurface({ personaName }: { personaName: string }) {
  return (
    <div className="grid min-h-[25rem] place-items-center p-6 text-center">
      <div className="max-w-md">
        <div className="mx-auto grid h-20 w-20 place-items-center rounded-3xl bg-starGold/16 text-starGold shadow-[0_0_42px_rgba(255,190,109,0.32)]">
          <Mic2 className="h-10 w-10" aria-hidden="true" />
        </div>
        <h2 className="mt-5 font-serif text-2xl font-bold text-starGold">语音对话</h2>
        <p className="mt-3 text-sm font-semibold leading-7 text-starMist/68">
          这里会用于和{personaName}进行语音对话。可以先用文字输入，系统会持续保留语音互动入口。
        </p>
      </div>
    </div>
  );
}

function MessageBubble({ message, personaName }: { message: MessageRead; personaName: string }) {
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
          {isPersona ? `${personaName}的星星` : "我"}
        </p>
        <div
          className={`rounded-2xl px-5 py-4 text-left text-sm font-semibold leading-7 shadow-[0_12px_30px_rgba(0,0,0,0.18)] ${
            isPersona
              ? "bg-indigo-200/10 text-starMist/82"
              : "bg-violet-400/22 text-starCream"
          }`}
        >
          {message.content}
        </div>
        <time className="mt-2 block text-xs text-starMist/34">{formatDate(message.created_at)}</time>
      </div>
    </article>
  );
}

function MemoryStoryPanel({
  story,
  storyCount,
  isBusy,
  personaName,
  onGenerate
}: {
  story: MemoryStoryRead | null;
  storyCount: number;
  isBusy: boolean;
  personaName: string;
  onGenerate: () => void;
}) {
  return (
    <aside className="border-t border-white/8 bg-indigo-950/18 p-4 xl:border-l xl:border-t-0">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-bold text-starGold">共同回忆</p>
        <span className="rounded-full bg-starGold/12 px-3 py-1 text-xs font-bold text-starMist/68">
          {storyCount} 段
        </span>
      </div>
      <div className="mt-3 aspect-video overflow-hidden rounded-2xl bg-[url('/memory-space/family-album.jpg')] bg-cover bg-center shadow-[0_16px_38px_rgba(0,0,0,0.22)]" />
      {story ? (
        <div className="mt-4">
          <h2 className="font-serif text-xl font-bold text-starGold">{story.title}</h2>
          <p className="mt-2 line-clamp-6 text-sm font-semibold leading-7 text-starMist/76">
            {story.content}
          </p>
          <p className="mt-3 text-xs font-semibold leading-5 text-starMist/48">
            来源：{storySourceSummary(story)}
          </p>
          {story.audio_url ? (
            <p className="mt-3 inline-flex items-center gap-2 rounded-full bg-starGold/12 px-3 py-1 text-xs font-bold text-starGold">
              <Volume2 className="h-3.5 w-3.5" aria-hidden="true" />
              已生成语音讲述
            </p>
          ) : null}
        </div>
      ) : (
        <p className="mt-4 text-sm font-semibold leading-7 text-starMist/66">
          还没有生成回忆故事。点击“记忆档案馆”，让{personaName}从已审核记忆里讲一段给你听。
        </p>
      )}
      <button
        type="button"
        disabled={isBusy}
        onClick={onGenerate}
        className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-full border border-starGold/24 bg-starGold/12 px-4 py-3 text-sm font-bold text-starCream transition hover:bg-starGold/18 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Sparkles className="h-4 w-4" aria-hidden="true" />
        {isBusy ? "正在生成..." : "让TA讲一段回忆"}
      </button>
    </aside>
  );
}

function ExperienceCard({
  icon: Icon,
  title,
  description,
  actionLabel,
  disabled,
  onClick
}: {
  icon: typeof BookOpen;
  title: string;
  description: string;
  actionLabel: string;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="group min-h-[9.2rem] rounded-3xl border border-starGold/12 bg-indigo-950/32 p-5 text-left shadow-[0_18px_44px_rgba(0,0,0,0.24)] backdrop-blur transition hover:-translate-y-1 hover:border-starGold/28 hover:bg-indigo-900/36 disabled:cursor-not-allowed disabled:opacity-60"
    >
      <div className="flex items-start gap-4">
        <span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-starGold/14 text-starGold shadow-[0_0_30px_rgba(255,190,109,0.24)]">
          <Icon className="h-8 w-8" aria-hidden="true" />
        </span>
        <div>
          <h2 className="font-serif text-xl font-bold text-starGold">{title}</h2>
          <p className="mt-2 text-sm font-semibold leading-6 text-starMist/66">{description}</p>
          <p className="mt-3 inline-flex items-center gap-2 text-sm font-bold text-starCream">
            {actionLabel}
            <Heart className="h-4 w-4 text-starGold" aria-hidden="true" />
          </p>
        </div>
      </div>
    </button>
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
