"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  BookOpenText,
  MessageCircle,
  Mic2,
  ScrollText,
  Sparkles,
  UploadCloud,
  UserRound
} from "lucide-react";
import { DemoEntry } from "@/src/components/DemoEntry";
import {
  AiReminder,
  GlassPanel,
  MemoryActionCard,
  MemoryContainer,
  MemoryShell,
  MemoryTitle,
  PaperNote,
  PhotoStack,
  StatPill,
  TrustBadge,
  VoiceWave
} from "@/src/components/MemorySpace";
import { MEMORY_SPACE_ACTIONS } from "@/src/lib/memory-space";
import { getAuthToken } from "@/src/lib/auth";
import { getPersona, personaTypeLabel, PersonaRead } from "@/src/lib/persona";
import {
  getPersonaProfile,
  PersonaProfileRead,
  primaryUploadSuggestion,
  trustLevelForScore,
  trustLevelLabel
} from "@/src/lib/profile";
import { ROUTES } from "@/src/lib/routes";

type DetailState = "checking" | "signedOut" | "loading" | "ready" | "error";

export default function PersonaDetailPage() {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<DetailState>("checking");
  const [persona, setPersona] = useState<PersonaRead | null>(null);
  const [profile, setProfile] = useState<PersonaProfileRead | null>(null);
  const [error, setError] = useState<string | null>(null);

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

    Promise.all([getPersona(personaId), getPersonaProfile(personaId)])
      .then(([loadedPersona, loadedProfile]) => {
        if (!isCurrent) {
          return;
        }
        setPersona(loadedPersona);
        setProfile(loadedProfile);
        setState("ready");
      })
      .catch((caught) => {
        if (!isCurrent) {
          return;
        }
        setError(caught instanceof Error ? caught.message : "无法加载人物。");
        setState("error");
      });

    return () => {
      isCurrent = false;
    };
  }, [personaId]);

  return (
    <MemoryShell background="grandmotherTea">
      <MemoryContainer>
        <Link href={ROUTES.dashboard} className="text-sm font-semibold text-memoryAccent">
          返回记忆空间列表
        </Link>

        {state === "signedOut" ? <SignedOutState /> : null}
        {state === "loading" || state === "checking" ? (
          <Notice text="正在打开记忆空间..." />
        ) : null}
        {state === "error" ? <Notice text={error ?? "无法加载人物。"} /> : null}
        {state === "ready" && persona ? (
          <MemorySpace persona={persona} profile={profile} />
        ) : null}
      </MemoryContainer>
    </MemoryShell>
  );
}

function SignedOutState() {
  return (
    <GlassPanel className="mt-8 max-w-3xl">
      <h1 className="font-serif text-3xl font-semibold text-memoryText">
        需要一个可访问的记忆空间
      </h1>
      <p className="mt-3 max-w-2xl text-sm leading-7 text-memoryText/70">
        你可以免注册打开外婆示例，或登录已有账号查看私有人物。
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
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

function Notice({ text }: { text: string }) {
  return (
    <GlassPanel className="mt-8 text-sm leading-7 text-memoryText/72">
      {text}
    </GlassPanel>
  );
}

function MemorySpace({
  persona,
  profile
}: {
  persona: PersonaRead;
  profile: PersonaProfileRead | null;
}) {
  const trustScore = profile?.trust_score ?? persona.trust_score;
  const trustLevel = profile?.trust_level ?? trustLevelForScore(trustScore);
  const uploadSuggestion = profile ? primaryUploadSuggestion(profile.suggestions) : null;

  return (
    <div className="mt-8 grid gap-7">
      <section className="grid gap-7 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
        <div>
          <MemoryTitle
            title={`${persona.name}的记忆空间`}
            subtitle={`${personaTypeLabel(persona.persona_type)} · ${statusLabel(persona.status)}。这里收纳 TA 的资料、可信记忆、人格档案和可对话的陪伴。`}
          >
            <div className="mt-6">
              <AiReminder />
            </div>
          </MemoryTitle>
          <p className="mt-6 max-w-2xl text-sm leading-7 text-memoryText/74">
            {persona.short_bio}
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link
              href={ROUTES.personaChat(persona.id)}
              className="memory-button inline-flex items-center justify-center gap-2 rounded-2xl bg-memoryAccent px-5 py-3 text-sm font-semibold text-white shadow-warm transition hover:bg-memoryAccentDark focus:outline-none focus:ring-4 focus:ring-memoryAccent/25"
            >
              <MessageCircle className="h-4 w-4" aria-hidden="true" />
              开始对话
            </Link>
            <Link
              href={ROUTES.personaUploads(persona.id)}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-memoryLine/80 bg-white/72 px-5 py-3 text-sm font-semibold text-memoryText shadow-soft backdrop-blur transition hover:border-memoryAccent/45 hover:text-memoryAccent"
            >
              <UploadCloud className="h-4 w-4" aria-hidden="true" />
              补充资料
            </Link>
          </div>
        </div>

        <div className="relative min-h-[30rem]">
          <PhotoStack
            primary="grandmotherTea"
            secondary="familyAlbum"
            className="mx-auto max-w-xl"
          />
          <div className="absolute right-2 top-0">
            <TrustBadge score={trustScore} label={trustLevelLabel(trustLevel)} />
          </div>
          <div className="absolute bottom-4 left-0">
            <VoiceWave label={`${persona.name}的声音`} />
          </div>
        </div>
      </section>

      <GlassPanel className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <MemoryActionCard
          href={ROUTES.personaChat(persona.id)}
          title={MEMORY_SPACE_ACTIONS.chat.title}
          text="从一句想念开始，查看回复依据。"
          icon={MessageCircle}
          primary
        />
        <MemoryActionCard
          href={ROUTES.personaUploads(persona.id)}
          title={MEMORY_SPACE_ACTIONS.upload.title}
          text="把新的故事、照片或声音放进资料盒。"
          icon={UploadCloud}
        />
        <MemoryActionCard
          href={ROUTES.personaMemories(persona.id)}
          title={MEMORY_SPACE_ACTIONS.memories.title}
          text="确认、修正或停用资料整理出的记忆。"
          icon={ScrollText}
        />
        <MemoryActionCard
          href={ROUTES.personaProfile(persona.id)}
          title={MEMORY_SPACE_ACTIONS.profile.title}
          text="查看习惯、关系、表达方式和可信度。"
          icon={UserRound}
        />
        <MemoryActionCard
          href={ROUTES.personaAvatar(persona.id)}
          title={MEMORY_SPACE_ACTIONS.avatar.title}
          text="选择纪念形象，查看 mock 头像/半身预览。"
          icon={Sparkles}
        />
      </GlassPanel>

      <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
        <GlassPanel>
          <h2 className="font-serif text-2xl font-semibold text-memoryText">人格设定</h2>
          <dl className="mt-5 grid gap-4">
            <DetailRow label="你们的关系" value={persona.relationship_to_user} />
            <DetailRow label="TA 对你的称呼" value={persona.user_nickname_by_persona} />
            <DetailRow label="说话风格" value={persona.speaking_style} />
            <DetailRow label="情绪方式" value={persona.emotional_style} />
            <DetailRow label="禁止表达" value={persona.forbidden_expressions} />
          </dl>
        </GlassPanel>

        <aside className="grid gap-5">
          <GlassPanel>
            <h2 className="font-serif text-2xl font-semibold text-memoryText">当前状态</h2>
            <dl className="mt-5 grid grid-cols-3 gap-3">
              <StatPill label="资料" value={persona.stats.materials_count} />
              <StatPill label="记忆" value={persona.stats.memories_count} />
              <StatPill label="对话" value={persona.stats.conversations_count} />
            </dl>
            <Link
              href={ROUTES.personaJobs(persona.id)}
              className="mt-5 inline-flex items-center gap-2 rounded-2xl border border-memoryLine/80 bg-white/72 px-4 py-2.5 text-sm font-semibold text-memoryText"
            >
              <BookOpenText className="h-4 w-4" aria-hidden="true" />
              查看资料整理任务
            </Link>
          </GlassPanel>
          <PaperNote>
            <h2 className="text-lg font-semibold text-memoryText">资料建议</h2>
            <p className="mt-3 text-sm leading-7 text-memoryText/72">
              {uploadSuggestion ??
                "继续补充有来源的共同经历、口头禅和生活习惯，可以让后续对话更稳定。"}
            </p>
          </PaperNote>
          <GlassPanel>
            <div className="flex items-start gap-3">
              <Sparkles className="mt-1 h-5 w-5 shrink-0 text-memoryAccent" />
              <p className="text-sm leading-7 text-memoryText/70">
                当前体验仍使用 deterministic mock provider。浏览器录音、mock 语音播放和 mock 3D 头像/半身预览已接入；真实 OCR/ASR/LLM、真实音色质量、真实 3D provider、对话页数字人联动和导出尚未实现。
              </p>
            </div>
          </GlassPanel>
          <MemoryActionCard
            href={ROUTES.personaVoice(persona.id)}
            title={MEMORY_SPACE_ACTIONS.voice.title}
            text="选择默认 TTS、创建音色样本并试听回复。"
            icon={Mic2}
          />
        </aside>
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="rounded-2xl border border-memoryLine/60 bg-white/55 p-4">
      <dt className="text-sm font-semibold text-memoryText/58">{label}</dt>
      <dd className="mt-2 whitespace-pre-wrap text-sm leading-7 text-memoryText">
        {value || "未设置"}
      </dd>
    </div>
  );
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    deceased: "已故",
    living: "在世",
    public: "公众人物",
    fictional: "虚拟角色"
  };

  return labels[status] ?? status;
}
