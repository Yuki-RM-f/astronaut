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
  Star,
  UploadCloud,
  UserRound,
  type LucideIcon
} from "lucide-react";
import {
  PageTitle,
  PlanetStar,
  StarNav,
  StarPanel,
  StarShell
} from "@/src/components/StarSite";
import { ensureDemoSession } from "@/src/lib/auth";
import { getPersona, personaTypeLabel, PersonaRead } from "@/src/lib/persona";
import {
  getPersonaProfile,
  PersonaProfileRead,
  primaryUploadSuggestion,
  trustLevelForScore,
  trustLevelLabel
} from "@/src/lib/profile";
import { ROUTES } from "@/src/lib/routes";

type DetailState = "loading" | "ready" | "error";

export default function PersonaDetailPage() {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<DetailState>("loading");
  const [persona, setPersona] = useState<PersonaRead | null>(null);
  const [profile, setProfile] = useState<PersonaProfileRead | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!personaId) {
      setError("缺少人物 ID。");
      setState("error");
      return;
    }

    let isCurrent = true;
    setState("loading");
    setError(null);

    ensureDemoSession()
      .then(() => Promise.all([getPersona(personaId), getPersonaProfile(personaId)]))
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
    <StarShell>
      <StarNav />
      <main className="mx-auto w-full max-w-7xl px-5 pb-12 sm:px-8 lg:px-10">
        <Link href={ROUTES.dashboard} className="text-sm font-bold text-starGold">
          返回我的星空
        </Link>

        {state === "loading" ? <Notice text="正在打开这颗星星..." /> : null}
        {state === "error" ? <Notice text={error ?? "无法加载人物。"} /> : null}
        {state === "ready" && persona ? (
          <PersonaSpace persona={persona} profile={profile} />
        ) : null}
      </main>
    </StarShell>
  );
}

function PersonaSpace({
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
    <div className="mt-7 grid gap-6">
      <section className="relative grid gap-7 lg:grid-cols-[minmax(0,0.9fr)_minmax(18rem,0.5fr)] lg:items-center">
        <div>
          <PageTitle
            className="text-left"
            title={`${persona.name}的星星`}
            subtitle={`${personaTypeLabel(persona.persona_type)} · ${statusLabel(persona.status)}。这里收纳 TA 的资料、可信记忆、人格档案和可对话的陪伴。`}
          />
          <p className="mt-6 max-w-2xl text-sm font-semibold leading-7 text-starMist/74">
            {persona.short_bio}
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link href={ROUTES.personaChat(persona.id)} className="star-button gap-2">
              <MessageCircle className="h-4 w-4" aria-hidden="true" />
              开始对话
            </Link>
            <Link
              href={ROUTES.personaUploads(persona.id)}
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full border border-starGold/24 bg-starGold/12 px-6 text-sm font-bold text-starCream transition hover:bg-starGold/18"
            >
              <UploadCloud className="h-4 w-4" aria-hidden="true" />
              补充资料
            </Link>
          </div>
        </div>

        <StarPanel className="relative min-h-[20rem] overflow-hidden p-6">
          <div className="pointer-events-none absolute -right-16 -top-16 opacity-80">
            <PlanetStar />
          </div>
          <div className="relative z-10">
            <p className="text-sm font-bold text-starGold">可信度</p>
            <div className="mt-3 flex items-end gap-2 text-starGold">
              <span className="font-serif text-7xl font-bold leading-none">{trustScore}</span>
              <span className="pb-2 text-3xl font-bold">%</span>
            </div>
            <p className="mt-3 text-sm font-semibold text-starMist/70">
              {trustLevelLabel(trustLevel)}
            </p>
            <dl className="mt-6 grid grid-cols-3 gap-3">
              <Stat label="资料" value={persona.stats.materials_count} />
              <Stat label="记忆" value={persona.stats.memories_count} />
              <Stat label="对话" value={persona.stats.conversations_count} />
            </dl>
          </div>
        </StarPanel>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <ActionCard
          href={ROUTES.personaChat(persona.id)}
          title="星星对话"
          text="文字对话、视频手势互动、语音对话和三个体验入口。"
          icon={MessageCircle}
        />
        <ActionCard
          href={ROUTES.personaMemories(persona.id)}
          title="记忆审核"
          text="确认、修正、停用资料整理出的记忆，点亮星星。"
          icon={ScrollText}
        />
        <ActionCard
          href={ROUTES.personaUploads(persona.id)}
          title="资料上传"
          text="上传照片、视频、声音、文字，或手动补充回忆。"
          icon={UploadCloud}
        />
        <ActionCard
          href={ROUTES.personaProfile(persona.id)}
          title="人格档案"
          text="查看关系、习惯、表达方式和可信度组成。"
          icon={UserRound}
        />
        <ActionCard
          href={ROUTES.personaVoice(persona.id)}
          title="声音"
          text="选择默认 TTS、创建音色样本并试听回复。"
          icon={Mic2}
        />
        <ActionCard
          href={ROUTES.personaAvatar(persona.id)}
          title="3D 形象"
          text="选择纪念形象，查看 mock 头像/半身预览。"
          icon={Sparkles}
        />
        <ActionCard
          href={ROUTES.personaJobs(persona.id)}
          title="资料任务"
          text="查看资料解析、记忆抽取和语音合成任务。"
          icon={BookOpenText}
        />
      </section>

      <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <StarPanel className="p-6">
          <h2 className="font-serif text-2xl font-bold text-starGold">人格设定</h2>
          <dl className="mt-5 grid gap-4 md:grid-cols-2">
            <DetailRow label="年龄" value={formatAge(persona.age)} />
            <DetailRow label="你们的关系" value={persona.relationship_to_user} />
            <DetailRow label="TA 对你的称呼" value={persona.user_nickname_by_persona} />
            <DetailRow label="说话风格" value={persona.speaking_style} />
            <DetailRow label="情绪方式" value={persona.emotional_style} />
            <DetailRow label="禁止表达" value={persona.forbidden_expressions} />
          </dl>
        </StarPanel>

        <StarPanel className="p-6">
          <p className="inline-flex items-center gap-2 text-sm font-bold text-starGold">
            <Star className="h-4 w-4 fill-current" aria-hidden="true" />
            资料建议
          </p>
          <p className="mt-4 text-sm font-semibold leading-7 text-starMist/72">
            {uploadSuggestion ??
              "继续补充有来源的共同经历、口头禅和生活习惯，可以让后续对话更稳定。"}
          </p>
        </StarPanel>
      </div>
    </div>
  );
}

function ActionCard({
  href,
  title,
  text,
  icon: Icon
}: {
  href: string;
  title: string;
  text: string;
  icon: LucideIcon;
}) {
  return (
    <Link
      href={href}
      className="group rounded-[1.5rem] border border-starGold/14 bg-indigo-950/36 p-5 shadow-[0_16px_44px_rgba(0,0,0,0.24)] backdrop-blur transition hover:-translate-y-1 hover:border-starGold/32"
    >
      <span className="grid h-12 w-12 place-items-center rounded-2xl bg-starGold/14 text-starGold">
        <Icon className="h-6 w-6" aria-hidden="true" />
      </span>
      <h2 className="mt-4 font-serif text-xl font-bold text-starGold">{title}</h2>
      <p className="mt-2 text-sm font-semibold leading-6 text-starMist/66">{text}</p>
    </Link>
  );
}

function DetailRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/6 p-4">
      <dt className="text-sm font-bold text-starMist/54">{label}</dt>
      <dd className="mt-2 whitespace-pre-wrap text-sm font-semibold leading-7 text-starCream">
        {value || "未设置"}
      </dd>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/6 p-3">
      <dt className="text-xs font-bold text-starMist/52">{label}</dt>
      <dd className="mt-1 text-2xl font-bold text-starCream">{value}</dd>
    </div>
  );
}

function Notice({ text }: { text: string }) {
  return (
    <StarPanel className="mt-8 p-5 text-sm font-semibold leading-7 text-starMist/72">
      {text}
    </StarPanel>
  );
}

function formatAge(age: number | null): string {
  return age === null ? "未设置" : `${age} 岁`;
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
