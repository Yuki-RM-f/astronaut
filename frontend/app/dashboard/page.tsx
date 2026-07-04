"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Heart, Plus, Sparkles } from "lucide-react";
import { DemoEntry } from "@/src/components/DemoEntry";
import {
  GlassPanel,
  MemoryContainer,
  MemoryShell,
  MemoryTitle,
  PrimaryMemoryLink,
  SecondaryMemoryLink,
  StatPill
} from "@/src/components/MemorySpace";
import { getAuthToken } from "@/src/lib/auth";
import { listPersonas, personaTypeLabel, PersonaRead } from "@/src/lib/persona";
import { ROUTES } from "@/src/lib/routes";

type DashboardState = "checking" | "signedOut" | "loading" | "ready" | "error";

export default function DashboardPage() {
  const [state, setState] = useState<DashboardState>("checking");
  const [personas, setPersonas] = useState<PersonaRead[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getAuthToken()) {
      setState("signedOut");
      return;
    }

    let isCurrent = true;
    setState("loading");
    setError(null);

    listPersonas()
      .then((items) => {
        if (!isCurrent) {
          return;
        }
        setPersonas(items);
        setState("ready");
      })
      .catch((caught) => {
        if (!isCurrent) {
          return;
        }
        setError(caught instanceof Error ? caught.message : "无法加载人物列表。");
        setState("error");
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  return (
    <MemoryShell background="familyLivingRoom">
      <MemoryContainer>
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <MemoryTitle
            title="我的记忆空间"
            subtitle="这里保存你创建的人物、资料、可信记忆、人格档案和对话。选择一个空间继续整理，也可以先体验外婆示例。"
          />
          <PrimaryMemoryLink href={ROUTES.personasNew} className="w-fit">
            <Plus className="h-4 w-4" aria-hidden="true" />
            创建人物
          </PrimaryMemoryLink>
        </div>

        {state === "signedOut" ? <SignedOutState /> : null}
        {state === "loading" || state === "checking" ? (
          <DashboardNotice text="正在点亮你的记忆空间..." />
        ) : null}
        {state === "error" ? <DashboardNotice text={error ?? "无法加载人物列表。"} /> : null}
        {state === "ready" && personas.length === 0 ? <EmptyState /> : null}
        {state === "ready" && personas.length > 0 ? <PersonaGrid personas={personas} /> : null}
      </MemoryContainer>
    </MemoryShell>
  );
}

function SignedOutState() {
  return (
    <GlassPanel className="mt-8 max-w-3xl">
      <h2 className="font-serif text-3xl font-semibold text-memoryText">先从一个示例开始</h2>
      <p className="mt-3 max-w-2xl text-sm leading-7 text-memoryText/70">
        你可以免注册进入外婆示例，也可以登录已有账号查看自己的私有人物。
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        <DemoEntry label="立即体验示例" />
        <SecondaryMemoryLink href={ROUTES.login}>登录已有账号</SecondaryMemoryLink>
      </div>
    </GlassPanel>
  );
}

function DashboardNotice({ text }: { text: string }) {
  return (
    <GlassPanel className="mt-8 text-sm leading-7 text-memoryText/72">
      {text}
    </GlassPanel>
  );
}

function EmptyState() {
  return (
    <GlassPanel className="mt-8 max-w-3xl">
      <Sparkles className="h-8 w-8 text-memoryAccent" aria-hidden="true" />
      <h2 className="mt-4 font-serif text-3xl font-semibold text-memoryText">
        还没有属于你的记忆空间
      </h2>
      <p className="mt-3 max-w-2xl text-sm leading-7 text-memoryText/70">
        从关系、称呼、说话风格和禁止表达开始，先搭好一个能被资料和记忆支撑的人物。
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        <PrimaryMemoryLink href={ROUTES.personasNew}>创建第一个人物</PrimaryMemoryLink>
        <DemoEntry label="先体验示例" />
      </div>
    </GlassPanel>
  );
}

function PersonaGrid({ personas }: { personas: PersonaRead[] }) {
  return (
    <div className="mt-8 grid gap-5 md:grid-cols-2">
      {personas.map((persona) => (
        <Link
          key={persona.id}
          href={ROUTES.personaDetail(persona.id)}
          className="memory-card rounded-[2rem] border border-white/70 bg-white/74 p-5 text-memoryText shadow-soft backdrop-blur transition hover:-translate-y-1 hover:shadow-warm focus:outline-none focus:ring-4 focus:ring-memoryAccent/20"
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs font-semibold tracking-[0.08em] text-memoryAccent">
                {personaTypeLabel(persona.persona_type)}
              </p>
              <h2 className="mt-2 font-serif text-3xl font-semibold">{persona.name}</h2>
              <p className="mt-2 text-sm leading-7 text-memoryText/68">
                {persona.relationship_to_user}会称呼你为「{persona.user_nickname_by_persona}」。
              </p>
            </div>
            <span className="inline-flex w-fit items-center gap-2 rounded-full bg-memoryWarm px-3 py-2 text-sm font-semibold text-memoryAccent">
              <Heart className="h-4 w-4 fill-current" aria-hidden="true" />
              {persona.trust_score}%
            </span>
          </div>
          <dl className="mt-5 grid grid-cols-3 gap-3">
            <StatPill label="资料" value={persona.stats.materials_count} />
            <StatPill label="记忆" value={persona.stats.memories_count} />
            <StatPill label="对话" value={persona.stats.conversations_count} />
          </dl>
        </Link>
      ))}
    </div>
  );
}
