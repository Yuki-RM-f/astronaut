"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Send, Sparkles, Star, Volume2 } from "lucide-react";
import { AvatarStage } from "@/src/components/AvatarStage";
import { ConversationWorkspace, ChatComposer } from "@/src/components/ConversationWorkspace";
import { PersonaBackLink } from "@/src/components/PersonaBackLink";
import {
  PageTitle,
  StarNav,
  StarPanel,
  StarShell
} from "@/src/components/StarSite";
import { ensureDemoSession } from "@/src/lib/auth";
import {
  AvatarConfigResponse,
  getAvatarConfig,
  getAvatarDisplaySource
} from "@/src/lib/avatar";
import {
  ConversationRead,
  createConversation,
  hasPlayableAudio,
  isAvatarMouthActive,
  isBlankChatText,
  listConversations,
  listMessages,
  MessageRead,
  sendMessage
} from "@/src/lib/chat";
import {
  getGuidedExperienceConfig,
  GuidedMemoryCandidate,
  guidedExperienceContextKind,
  guidedExperienceConversationKind,
  GuidedExperienceKind,
  loadGuidedMemoryCandidates
} from "@/src/lib/guided-experiences";
import { getPersona, PersonaRead } from "@/src/lib/persona";

type PageState = "checking" | "loading" | "ready" | "error";

export function GuidedExperiencePage({ kind }: { kind: GuidedExperienceKind }) {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<PageState>("checking");
  const [persona, setPersona] = useState<PersonaRead | null>(null);
  const [conversation, setConversation] = useState<ConversationRead | null>(null);
  const [messages, setMessages] = useState<MessageRead[]>([]);
  const [guidedCandidates, setGuidedCandidates] = useState<GuidedMemoryCandidate[]>([]);
  const [selectedGuidedMemoryIds, setSelectedGuidedMemoryIds] = useState<string[]>([]);
  const [avatarConfig, setAvatarConfig] = useState<AvatarConfigResponse | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);

  useEffect(() => {
    if (!personaId) {
      setError("缺少人物 ID。");
      setState("error");
      return;
    }

    let isCurrent = true;
    setState("loading");
    ensureDemoSession()
      .then(() => loadGuidedExperience(personaId, kind))
      .then((loaded) => {
        if (!isCurrent) {
          return;
        }
        setPersona(loaded.persona);
        setConversation(loaded.conversation);
        setMessages(loaded.messages);
        setGuidedCandidates(loaded.guidedCandidates);
        setAvatarConfig(loaded.avatarConfig);
        setState("ready");
      })
      .catch((caught) => {
        if (!isCurrent) {
          return;
        }
        setError(caught instanceof Error ? caught.message : "无法加载页面。");
        setState("error");
      });

    return () => {
      isCurrent = false;
    };
  }, [kind, personaId]);

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!conversation || isBlankChatText(draft)) {
      return;
    }

    setSending(true);
    setError(null);
    try {
      await sendMessage(conversation.id, draft, selectedGuidedMemoryIds);
      setDraft("");
      setSelectedGuidedMemoryIds([]);
      setMessages(await listMessages(conversation.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法发送消息。");
    } finally {
      setSending(false);
    }
  }

  const config = getGuidedExperienceConfig(kind, persona?.name ?? "TA");
  const showGuidedCandidates = guidedCandidates.length > 0 && messages.length === 0;

  return (
    <StarShell>
      <StarNav />
      <main className="mx-auto w-full max-w-7xl px-5 pb-10 sm:px-8 lg:px-10">
        {personaId ? <PersonaBackLink personaId={personaId} /> : null}

        <PageTitle
          className="[&>p]:hidden sm:[&>p]:block"
          title={config.title}
          subtitle={`${config.eyebrow}。${config.persistenceNotice}`}
        />

        {state === "loading" || state === "checking" ? <Notice text="正在连接这颗星星..." /> : null}
        {state === "error" ? <Notice text={error ?? "无法加载页面。"} /> : null}

        {state === "ready" && persona && conversation ? (
          <div className="mt-6 grid gap-4">
            <ConversationWorkspace
              modeBar={
                <div>
                  <h2 className="font-serif text-2xl font-bold text-starGold">{config.title}</h2>
                  <p className="mt-2 text-sm font-semibold leading-7 text-starMist/70">
                    {config.emptyState}
                  </p>
                </div>
              }
              scrollKey={`${messages.length}:${sending}`}
              composer={
                <ChatComposer
                  value={draft}
                  onValueChange={setDraft}
                  onSubmit={handleSend}
                  placeholder={config.inputPlaceholder}
                  disabled={sending || isBlankChatText(draft)}
                  submitLabel={sending ? "发送中" : config.submitLabel}
                />
              }
              avatar={
                <AvatarStage
                  personaName={persona.name}
                  source={getAvatarDisplaySource(avatarConfig)}
                  mouthActive={isAvatarMouthActive(messages, playingMessageId)}
                  className="lg:min-h-[37rem]"
                  subtitle={config.openingMessage}
                />
              }
            >
              {error ? (
                <p className="mb-4 rounded-2xl border border-rose-300/20 bg-rose-500/15 p-3 text-sm font-semibold text-rose-100">
                  {error}
                </p>
              ) : null}
              <div className="grid gap-5">
                {showGuidedCandidates ? (
                  <GuidedCandidatePanel
                    candidates={guidedCandidates}
                    kind={kind}
                    onSelect={(candidate) => {
                      setDraft(candidate.suggested_user_message);
                      setSelectedGuidedMemoryIds([candidate.memory_card_id]);
                    }}
                  />
                ) : (
                  <OpeningBubble personaName={persona.name} text={config.openingMessage} />
                )}
                {messages.map((message) => (
                  <GuidedMessageBubble
                    key={message.id}
                    message={message}
                    personaName={persona.name}
                    isPlaying={playingMessageId === message.id}
                    onAudioPlay={setPlayingMessageId}
                    onAudioStop={(messageId) =>
                      setPlayingMessageId((currentId) =>
                        currentId === messageId ? null : currentId
                      )
                    }
                  />
                ))}
              </div>
            </ConversationWorkspace>
          </div>
        ) : null}

        {false && state === "ready" && persona && conversation ? (
          <div className="mt-6 grid gap-5 md:grid-cols-[minmax(0,0.66fr)_minmax(20rem,0.34fr)]">
            <StarPanel className="overflow-hidden p-0">
              <div className="border-b border-white/8 bg-indigo-950/24 p-5">
                <h2 className="font-serif text-3xl font-bold text-starGold">
                  {config.title}
                </h2>
                <p className="mt-2 text-sm font-semibold leading-7 text-starMist/70">
                  {config.emptyState}
                </p>
              </div>

              <div className="max-h-[35rem] min-h-[25rem] overflow-y-auto p-4 sm:p-5">
                <div className="grid gap-5">
                  <OpeningBubble personaName={persona!.name} text={config.openingMessage} />
                  {messages.map((message) => (
                    <GuidedMessageBubble
                      key={message.id}
                      message={message}
                      personaName={persona!.name}
                      isPlaying={playingMessageId === message.id}
                      onAudioPlay={setPlayingMessageId}
                      onAudioStop={(messageId) =>
                        setPlayingMessageId((currentId) =>
                          currentId === messageId ? null : currentId
                        )
                      }
                    />
                  ))}
                </div>
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
                  placeholder={config.inputPlaceholder}
                />
                <button
                  type="submit"
                  disabled={sending || isBlankChatText(draft)}
                  className="inline-flex min-w-24 items-center justify-center gap-2 rounded-full bg-starGold px-5 text-sm font-bold text-violet-950 transition hover:bg-starPeach disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {sending ? "发送中" : config.submitLabel}
                  <Send className="h-4 w-4" aria-hidden="true" />
                </button>
              </form>
            </StarPanel>

            <AvatarStage
              personaName={persona!.name}
              source={getAvatarDisplaySource(avatarConfig)}
              mouthActive={isAvatarMouthActive(messages, playingMessageId)}
              className="md:min-h-[37rem]"
              subtitle={config.openingMessage}
            />
          </div>
        ) : null}
      </main>
    </StarShell>
  );
}

async function loadGuidedExperience(
  personaId: string,
  kind: GuidedExperienceKind
): Promise<{
  persona: PersonaRead;
  conversation: ConversationRead;
  messages: MessageRead[];
  guidedCandidates: GuidedMemoryCandidate[];
  avatarConfig: AvatarConfigResponse | null;
}> {
  const persona = await getPersona(personaId);
  const conversationKind = guidedExperienceConversationKind(kind);
  const contextKind = guidedExperienceContextKind(kind);
  const conversations = await listConversations(personaId, conversationKind, contextKind);
  const title = kind === "regrets" ? `和${persona.name}的遗憾对话` : `和${persona.name}的心愿对话`;
  const conversation =
    conversations[0] ??
    (await createConversation(personaId, title, conversationKind, contextKind));
  const [messages, avatarConfig, guidedCandidateResponse] = await Promise.all([
    listMessages(conversation.id),
    getAvatarConfig(personaId).catch(() => null),
    loadGuidedMemoryCandidates(personaId, kind).catch(() => ({
      kind,
      items: [],
      empty_reason: null
    }))
  ]);
  return { persona, conversation, messages, guidedCandidates: guidedCandidateResponse.items, avatarConfig };
}

function GuidedCandidatePanel({
  candidates,
  kind,
  onSelect
}: {
  candidates: GuidedMemoryCandidate[];
  kind: GuidedExperienceKind;
  onSelect: (candidate: GuidedMemoryCandidate) => void;
}) {
  const label = kind === "wishes" ? "记忆里的心愿线索" : "记忆里的遗憾线索";
  return (
    <section className="rounded-3xl border border-starGold/20 bg-starGold/10 p-4 sm:p-5">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-starGold/80">
        {label}
      </p>
      <p className="mt-2 text-sm font-semibold leading-7 text-starMist/76">
        我先从已审核记忆里找到了这些可能相关的线索。选择一条后，你可以再决定怎么说给 TA 听。
      </p>
      <div className="mt-4 grid gap-3">
        {candidates.map((candidate) => (
          <button
            key={candidate.memory_card_id}
            type="button"
            onClick={() => onSelect(candidate)}
            className="rounded-2xl border border-white/10 bg-indigo-950/28 p-4 text-left transition hover:border-starGold/45 hover:bg-starGold/12"
          >
            <span className="text-sm font-bold text-starCream">{candidate.title}</span>
            <span className="mt-2 block text-sm font-semibold leading-7 text-starMist/76">
              {candidate.summary}
            </span>
            {candidate.source_location ? (
              <span className="mt-3 block text-xs font-bold text-starMist/44">
                来源：{candidate.source_location}
              </span>
            ) : null}
          </button>
        ))}
      </div>
    </section>
  );
}

function OpeningBubble({ personaName, text }: { personaName: string; text: string }) {
  return (
    <article className="flex gap-3 justify-start">
      <span className="mt-1 grid h-11 w-11 shrink-0 place-items-center rounded-full bg-starGold/18 text-starGold">
        <Sparkles className="h-6 w-6" aria-hidden="true" />
      </span>
      <div className="max-w-[82%]">
        <p className="mb-2 text-xs font-bold text-starMist/46">{personaName}先问你</p>
        <div className="rounded-2xl bg-indigo-200/10 px-5 py-4 text-left text-sm font-semibold leading-7 text-starMist/82 shadow-[0_12px_30px_rgba(0,0,0,0.18)]">
          {text}
        </div>
      </div>
    </article>
  );
}

function GuidedMessageBubble({
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
          {isPersona ? `${personaName}的星星` : "我"}
        </p>
        <div
          className={`rounded-2xl px-5 py-4 text-left text-sm font-semibold leading-7 shadow-[0_12px_30px_rgba(0,0,0,0.18)] ${
            isPersona ? "bg-indigo-200/10 text-starMist/82" : "bg-violet-400/22 text-starCream"
          }`}
        >
          {message.content}
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
      </div>
    </article>
  );
}

function Notice({ text }: { text: string }) {
  return <StarPanel className="mx-auto mt-8 max-w-3xl p-5 text-center text-starMist/72">{text}</StarPanel>;
}
