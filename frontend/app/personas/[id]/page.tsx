"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  BookOpenText,
  HeartHandshake,
  MessageCircle,
  Mic2,
  ScrollText,
  Sparkles,
  Star,
  UploadCloud,
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
import { listMemories, MemoryRead } from "@/src/lib/memories";
import {
  getPersonaWorkspaceNavGroups,
  type PersonaWorkspaceNavGroup,
  type PersonaWorkspaceNavKey
} from "@/src/lib/memory-space";
import { getPersona, personaTypeLabel, PersonaRead } from "@/src/lib/persona";
import {
  getPersonaProfile,
  PersonaProfileRead,
  primaryUploadSuggestion
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
  const [pendingReviewCount, setPendingReviewCount] = useState(0);
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
      .then(() =>
        Promise.all([getPersona(personaId), getPersonaProfile(personaId), listMemories(personaId)])
      )
      .then(([loadedPersona, loadedProfile, loadedMemories]) => {
        if (!isCurrent) {
          return;
        }
        setPersona(loadedPersona);
        setProfile(loadedProfile);
        setPendingReviewCount(countPendingReviewMemories(loadedMemories));
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
          <PersonaSpace
            persona={persona}
            profile={profile}
            pendingReviewCount={pendingReviewCount}
          />
        ) : null}
      </main>
    </StarShell>
  );
}

function PersonaSpace({
  persona,
  profile,
  pendingReviewCount
}: {
  persona: PersonaRead;
  profile: PersonaProfileRead | null;
  pendingReviewCount: number;
}) {
  const uploadSuggestion = profile ? primaryUploadSuggestion(profile.suggestions) : null;
  const profileSummary = profile ? profile.profile_summary?.trim() : "";
  const primaryAction = getPrimaryAction(persona, pendingReviewCount);
  const PrimaryIcon = primaryAction.icon;

  return (
    <div className="mt-7 grid gap-6">
      <section className="relative grid gap-7 lg:grid-cols-[minmax(0,0.9fr)_minmax(18rem,0.5fr)] lg:items-center">
        <div>
          <PageTitle
            className="text-left"
            title={`${persona.name}的星星`}
            subtitle={`${personaTypeLabel(persona.persona_type)} · ${statusLabel(persona.status)}。这里收纳 TA 的资料、记忆和可对话的陪伴。`}
          />
          <p className="mt-6 max-w-2xl text-sm font-semibold leading-7 text-starMist/74">
            {profileSummary || "档案摘要将在新的资料上传解析后自动生成。"}
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link href={primaryAction.href} className="star-button gap-2">
              <PrimaryIcon className="h-4 w-4" aria-hidden="true" />
              {primaryAction.label}
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
            <p className="text-sm font-bold text-starGold">资料概览</p>
            <h2 className="mt-3 font-serif text-4xl font-bold text-starGold">
              {persona.name}
            </h2>
            <p className="mt-3 text-sm font-semibold leading-7 text-starMist/70">
              审核入口在资料解析页，回忆讲述和搜索在记忆档案馆。
            </p>
            <div className="mt-5">
              <p className="text-sm font-bold text-starGold">基础信息</p>
              <dl className="mt-3 grid gap-3 sm:grid-cols-2">
                <OverviewFact label="年龄" value={formatAge(persona.age)} />
                <OverviewFact label="你们的关系" value={persona.relationship_to_user} />
                <OverviewFact label="TA 对你的称呼" value={persona.user_nickname_by_persona} />
              </dl>
            </div>
            <dl className="mt-6 grid grid-cols-3 gap-3">
              <Stat label="资料" value={persona.stats.materials_count} />
              <Stat label="记忆" value={persona.stats.memories_count} />
              <Stat label="对话" value={persona.stats.conversations_count} />
            </dl>
          </div>
        </StarPanel>
      </section>
      <section className="grid gap-4 lg:grid-cols-2">
        {getPersonaWorkspaceNavGroups(persona.id).slice(1).map((group) => (
          <WorkspaceGroup key={group.label} group={group} />
        ))}
      </section>

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
  );
}

function WorkspaceGroup({ group }: { group: PersonaWorkspaceNavGroup }) {
  return (
    <StarPanel className="p-5">
      <h2 className="font-serif text-2xl font-bold text-starGold">{group.label}</h2>
      <div className="mt-4 grid gap-3">
        {group.items.map((item) => {
          const Icon = workspaceIcon(item.key);
          return (
            <Link
              key={item.key}
              href={item.href}
              className="group flex min-h-[5.5rem] items-start gap-4 rounded-2xl border border-white/8 bg-white/[0.05] p-4 transition hover:border-starGold/28 hover:bg-starGold/10"
            >
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-starGold/14 text-starGold">
                <Icon className="h-5 w-5" aria-hidden="true" />
              </span>
              <span>
                <span className="block text-base font-black text-starCream group-hover:text-starGold">
                  {item.label}
                </span>
                <span className="mt-1 block text-sm font-semibold leading-6 text-starMist/62">
                  {item.description}
                </span>
              </span>
            </Link>
          );
        })}
      </div>
    </StarPanel>
  );
}

function OverviewFact({
  label,
  value,
  className = ""
}: {
  label: string;
  value: string | null;
  className?: string;
}) {
  return (
    <div className={`border-t border-white/10 pt-3 ${className}`}>
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

function countPendingReviewMemories(memories: MemoryRead[]): number {
  return memories.filter((memory) => memory.status === "pending_review").length;
}

function getPrimaryAction(persona: PersonaRead, pendingReviewCount: number) {
  if (persona.stats.materials_count === 0) {
    return {
      href: ROUTES.personaUploads(persona.id),
      label: "补充资料",
      description: "这颗星星还缺少可追溯资料。先上传文字、照片、声音或视频，再进入资料解析与审核。",
      icon: UploadCloud
    };
  }

  if (pendingReviewCount > 0) {
    return {
      href: ROUTES.personaUploads(persona.id),
      label: "审核资料",
      description: `还有 ${pendingReviewCount} 条记忆等待确认。先在资料解析页审核来源，再让后续对话使用这些内容。`,
      icon: UploadCloud
    };
  }

  return {
    href: ROUTES.personaChat(persona.id),
    label: "开始对话",
    description: "资料和记忆已具备基础支撑，可以进入对话、声音和 3D 互动体验。",
    icon: MessageCircle
  };
}

function workspaceIcon(key: PersonaWorkspaceNavKey): LucideIcon {
  const icons: Record<PersonaWorkspaceNavKey, LucideIcon> = {
    overview: Star,
    uploads: UploadCloud,
    jobs: BookOpenText,
    memories: ScrollText,
    chat: MessageCircle,
    regrets: MessageCircle,
    wishes: HeartHandshake,
    voice: Mic2,
    avatar: Sparkles
  };
  return icons[key];
}
