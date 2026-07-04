"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Plus, Sparkles, Star, Trash2 } from "lucide-react";
import {
  PageTitle,
  PlanetStar,
  StarNav,
  StarPanel,
  StarShell
} from "@/src/components/StarSite";
import { ensureDemoSession } from "@/src/lib/auth";
import {
  deletePersona,
  listPersonas,
  personaTypeLabel,
  PersonaRead
} from "@/src/lib/persona";
import { ROUTES } from "@/src/lib/routes";

type DashboardState = "loading" | "ready" | "error";

export default function DashboardPage() {
  const [state, setState] = useState<DashboardState>("loading");
  const [personas, setPersonas] = useState<PersonaRead[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deletingPersonaId, setDeletingPersonaId] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;
    setState("loading");
    setError(null);

    ensureDemoSession()
      .then(() => listPersonas())
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

  async function handleDeletePersona(persona: PersonaRead) {
    const confirmed = window.confirm(
      `确定删除「${persona.name}」这颗星星吗？相关资料、记忆和对话入口会一并移除。`
    );
    if (!confirmed) {
      return;
    }

    setDeleteError(null);
    setDeletingPersonaId(persona.id);
    try {
      await deletePersona(persona.id);
      setPersonas((current) => current.filter((item) => item.id !== persona.id));
    } catch (caught) {
      setDeleteError(caught instanceof Error ? caught.message : "无法删除星星。");
    } finally {
      setDeletingPersonaId(null);
    }
  }

  return (
    <StarShell>
      <StarNav />
      <main className="mx-auto w-full max-w-7xl px-5 pb-12 sm:px-8 lg:px-10">
        <section className="relative overflow-hidden">
          <div className="pointer-events-none absolute -right-24 -top-20 hidden opacity-80 lg:block">
            <PlanetStar />
          </div>
          <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <PageTitle
              className="text-left"
              title="我的星空"
              subtitle="这里保存你创建的星星、资料、可信记忆、档案摘要和对话入口。"
            />
            <Link href={ROUTES.personasNew} className="star-button w-fit gap-2">
              <Plus className="h-4 w-4" aria-hidden="true" />
              创建星星
            </Link>
          </div>
        </section>

        {state === "loading" ? <Notice text="正在点亮你的星空..." /> : null}
        {state === "error" ? <Notice text={error ?? "无法加载人物列表。"} /> : null}
        {deleteError ? <Notice text={deleteError} /> : null}
        {state === "ready" && personas.length === 0 ? <EmptyState /> : null}
        {state === "ready" && personas.length > 0 ? (
          <PersonaGrid
            deletingPersonaId={deletingPersonaId}
            personas={personas}
            onDelete={handleDeletePersona}
          />
        ) : null}
      </main>
    </StarShell>
  );
}

function Notice({ text }: { text: string }) {
  return (
    <StarPanel className="mt-8 p-5 text-sm font-semibold leading-7 text-starMist/72">
      {text}
    </StarPanel>
  );
}

function EmptyState() {
  return (
    <StarPanel className="mt-8 max-w-3xl p-7">
      <Sparkles className="h-8 w-8 text-starGold" aria-hidden="true" />
      <h2 className="mt-4 font-serif text-3xl font-bold text-starGold">
        还没有属于你的星星
      </h2>
      <p className="mt-3 max-w-2xl text-sm font-semibold leading-7 text-starMist/72">
        从关系、称呼、年龄和一段想说的话开始，先搭好一颗能被资料和记忆支撑的星星。
      </p>
      <Link href={ROUTES.personasNew} className="star-button mt-6 w-fit gap-2">
        <Star className="h-4 w-4 fill-current" aria-hidden="true" />
        创建第一颗星星
      </Link>
    </StarPanel>
  );
}

function PersonaGrid({
  deletingPersonaId,
  personas,
  onDelete
}: {
  deletingPersonaId: string | null;
  personas: PersonaRead[];
  onDelete: (persona: PersonaRead) => void;
}) {
  return (
    <section className="mt-8 grid gap-5 md:grid-cols-2">
      {personas.map((persona) => (
        <article
          key={persona.id}
          className="group rounded-[1.75rem] border border-starGold/14 bg-indigo-950/36 p-5 shadow-[0_18px_52px_rgba(0,0,0,0.26)] backdrop-blur transition hover:-translate-y-1 hover:border-starGold/32 hover:bg-indigo-900/42"
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <Link href={ROUTES.personaDetail(persona.id)} className="min-w-0 flex-1">
              <p className="inline-flex items-center gap-2 text-xs font-bold tracking-[0.08em] text-starGold">
                <Star className="h-3.5 w-3.5 fill-current" aria-hidden="true" />
                {personaTypeLabel(persona.persona_type)}
              </p>
              <h2 className="mt-2 font-serif text-3xl font-bold text-starCream">
                {persona.name}
              </h2>
              <p className="mt-2 text-sm font-semibold leading-7 text-starMist/68">
                {persona.relationship_to_user}会称呼你为「{persona.user_nickname_by_persona}」。
              </p>
            </Link>
            <div className="flex w-fit flex-col items-start gap-3 sm:items-end">
              <span className="inline-flex w-fit items-center gap-2 rounded-full bg-starGold/14 px-3 py-2 text-sm font-bold text-starGold">
                <Star className="h-4 w-4 fill-current" aria-hidden="true" />
                已创建
              </span>
              <Link
                href={ROUTES.personaDetail(persona.id)}
                aria-label={`进入星星 ${persona.name}`}
                className="inline-flex min-h-10 items-center gap-2 rounded-full border border-starGold/28 bg-starGold/14 px-4 py-2 text-sm font-bold text-starCream transition hover:bg-starGold/22"
              >
                进入星星
                <Sparkles className="h-4 w-4" aria-hidden="true" />
              </Link>
              <button
                type="button"
                aria-label={`删除星星 ${persona.name}`}
                disabled={deletingPersonaId === persona.id}
                onClick={() => onDelete(persona)}
                className="inline-flex min-h-10 items-center gap-2 rounded-full border border-rose-200/24 bg-rose-400/10 px-3 py-2 text-sm font-bold text-rose-100 transition hover:border-rose-200/44 hover:bg-rose-400/18 disabled:cursor-not-allowed disabled:opacity-55"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                {deletingPersonaId === persona.id ? "删除中..." : "删除星星"}
              </button>
            </div>
          </div>
          <Link href={ROUTES.personaDetail(persona.id)} className="mt-5 block">
            <dl className="grid grid-cols-3 gap-3">
              <Stat label="资料" value={persona.stats.materials_count} />
              <Stat label="记忆" value={persona.stats.memories_count} />
              <Stat label="对话" value={persona.stats.conversations_count} />
            </dl>
          </Link>
        </article>
      ))}
    </section>
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
