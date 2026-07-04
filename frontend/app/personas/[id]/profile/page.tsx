"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  PageTitle,
  StarNav,
  StarPanel,
  StarShell
} from "@/src/components/StarSite";
import { ensureDemoSession } from "@/src/lib/auth";
import {
  getPersonaProfile,
  PersonaProfileRead,
  PersonaProfileUpdate,
  ProfileDimension,
  ProfileDimensionEntry,
  PROFILE_DIMENSION_OPTIONS,
  ProfileValue,
  profileDimensionLabel,
  recalculateTrust,
  regeneratePersonaProfile,
  trustComponentLabel,
  trustLevelForScore,
  trustLevelLabel,
  updatePersonaProfile
} from "@/src/lib/profile";
import { ROUTES } from "@/src/lib/routes";

type PageState = "loading" | "ready" | "error";
type BusyAction = "save" | "regenerate" | "trust" | null;
type DimensionDrafts = Record<ProfileDimension, string>;

export default function PersonaProfilePage() {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<PageState>("loading");
  const [profile, setProfile] = useState<PersonaProfileRead | null>(null);
  const [summaryDraft, setSummaryDraft] = useState("");
  const [dimensionDrafts, setDimensionDrafts] = useState<DimensionDrafts>(
    createEmptyDimensionDrafts()
  );
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<BusyAction>(null);

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
      .then(() => getPersonaProfile(personaId))
      .then((loadedProfile) => {
        if (!isCurrent) {
          return;
        }
        applyProfile(loadedProfile);
        setState("ready");
      })
      .catch((caught) => {
        if (!isCurrent) {
          return;
        }
        setError(caught instanceof Error ? caught.message : "无法加载人格档案。");
        setState("error");
      });

    return () => {
      isCurrent = false;
    };
  }, [personaId]);

  function applyProfile(nextProfile: PersonaProfileRead) {
    setProfile(nextProfile);
    setSummaryDraft(nextProfile.profile_summary ?? "");
    setDimensionDrafts(buildDimensionDrafts(nextProfile));
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!personaId || !profile) {
      return;
    }

    setError(null);
    setNotice(null);

    let payload: PersonaProfileUpdate;
    try {
      payload = buildUpdatePayload(profile, summaryDraft, dimensionDrafts);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "档案 JSON 格式不正确。");
      return;
    }

    if (Object.keys(payload).length === 0) {
      setNotice("没有需要保存的改动。");
      return;
    }

    setBusyAction("save");
    try {
      applyProfile(await updatePersonaProfile(personaId, payload));
      setNotice("人格档案已保存。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法保存人格档案。");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleRegenerate() {
    if (!personaId) {
      return;
    }

    setError(null);
    setNotice(null);
    setBusyAction("regenerate");
    try {
      applyProfile(await regeneratePersonaProfile(personaId));
      setNotice("已根据已审核记忆重生成人格档案。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法重生成人格档案。");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleRecalculateTrust() {
    if (!personaId) {
      return;
    }

    setError(null);
    setNotice(null);
    setBusyAction("trust");
    try {
      applyProfile(await recalculateTrust(personaId));
      setNotice("可信度已重新计算。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法重新计算可信度。");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <StarShell>
      <StarNav />
      <main className="mx-auto w-full max-w-7xl px-5 pb-12 sm:px-8 lg:px-10">
        <div className="flex flex-wrap items-center gap-3 text-sm font-bold text-starGold">
          <Link href={personaId ? ROUTES.personaDetail(personaId) : ROUTES.dashboard}>
            返回星星
          </Link>
          {personaId ? <Link href={ROUTES.personaMemories(personaId)}>审核记忆</Link> : null}
          {personaId ? <Link href={ROUTES.personaUploads(personaId)}>上传资料</Link> : null}
        </div>

        <PageTitle
          className="mt-6"
          title="人格档案与可信度"
          subtitle="档案来自已确认和已修正的记忆。文本对话会读取档案摘要和可追溯记忆。"
        />

        {state === "loading" ? <Notice text="正在加载人格档案..." /> : null}
        {state === "error" ? <Notice text={error ?? "无法加载人格档案。"} /> : null}

        {state === "ready" && profile ? (
          <form className="mt-8 grid gap-6" onSubmit={handleSave}>
            <section className="grid gap-4 md:grid-cols-3">
              <TrustCard profile={profile} />
              <StatCard
                label="可信等级"
                value={trustLevelLabel(profile.trust_level || trustLevelForScore(profile.trust_score))}
              />
              <StatCard label="更新时间" value={formatDate(profile.updated_at)} />
            </section>

            <StarPanel className="p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <h2 className="font-serif text-2xl font-bold text-starGold">可信度组成</h2>
                  <p className="mt-2 max-w-3xl text-sm font-semibold leading-7 text-starMist/70">
                    这些是当前规则下的可解释输入，不是真实模型质量评分。
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busyAction !== null}
                    onClick={handleRegenerate}
                    className={secondaryButtonClass}
                  >
                    {busyAction === "regenerate" ? "正在生成..." : "从已审核记忆重生成"}
                  </button>
                  <button
                    type="button"
                    disabled={busyAction !== null}
                    onClick={handleRecalculateTrust}
                    className={secondaryButtonClass}
                  >
                    {busyAction === "trust" ? "正在计算..." : "重新计算可信度"}
                  </button>
                </div>
              </div>

              <div className="mt-5 grid gap-3 lg:grid-cols-2">
                {profile.components.map((component) => (
                  <article
                    key={component.name}
                    className="rounded-2xl border border-white/8 bg-white/6 p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="text-sm font-bold text-starCream">
                        {trustComponentLabel(component.name)}
                      </h3>
                      <span className="rounded-full bg-starGold/12 px-3 py-1 text-xs font-bold text-starGold">
                        {component.score}/100
                      </span>
                    </div>
                    <dl className="mt-3 grid gap-2 text-xs text-starMist/60 md:grid-cols-2">
                      <SmallStat label="权重" value={`${Math.round(component.weight * 100)}%`} />
                      <SmallStat
                        label="加权分"
                        value={component.weighted_score.toFixed(2)}
                      />
                    </dl>
                    <p className="mt-3 text-sm font-semibold leading-7 text-starMist/70">
                      {component.evidence}
                    </p>
                  </article>
                ))}
              </div>
            </StarPanel>

            <StarPanel className="p-5">
              <h2 className="font-serif text-2xl font-bold text-starGold">补充资料建议</h2>
              {profile.suggestions.length === 0 ? (
                <p className="mt-4 rounded-2xl border border-white/8 bg-white/6 p-4 text-sm font-semibold text-starMist/70">
                  当前可信度报告没有返回新的补充建议。
                </p>
              ) : (
                <ul className="mt-4 grid gap-2 text-sm font-semibold leading-7 text-starMist/70">
                  {profile.suggestions.map((suggestion) => (
                    <li key={suggestion} className="rounded-2xl border border-white/8 bg-white/6 px-4 py-3">
                      {suggestion}
                    </li>
                  ))}
                </ul>
              )}
            </StarPanel>

            {error ? <Alert tone="error" text={error} /> : null}
            {notice ? <Alert tone="success" text={notice} /> : null}

            <StarPanel className="p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <h2 className="font-serif text-2xl font-bold text-starGold">档案摘要</h2>
                  <p className="mt-2 max-w-3xl text-sm font-semibold leading-7 text-starMist/70">
                    摘要应保持克制，只描述已有资料和审核记忆支持的内容。
                  </p>
                </div>
                <button type="submit" disabled={busyAction !== null} className={primaryButtonClass}>
                  {busyAction === "save" ? "正在保存..." : "保存档案"}
                </button>
              </div>
              <label className="mt-5 grid gap-2 text-sm font-bold text-starMist/78">
                档案摘要
                <textarea
                  value={summaryDraft}
                  onChange={(event) => setSummaryDraft(event.target.value)}
                  className={`${inputClass} min-h-32 resize-y`}
                  placeholder="用几句话概括已审核记忆支持的人格画像。"
                />
              </label>
            </StarPanel>

            <section className="grid gap-4">
              {PROFILE_DIMENSION_OPTIONS.map((option) => (
                <DimensionSection
                  key={option.value}
                  dimension={option.value}
                  value={profile[option.value]}
                  sourceMemoryIds={profile.source_memory_ids[option.value] ?? []}
                  draft={dimensionDrafts[option.value]}
                  onDraftChange={(value) =>
                    setDimensionDrafts((current) => ({
                      ...current,
                      [option.value]: value
                    }))
                  }
                />
              ))}
            </section>
          </form>
        ) : null}
      </main>
    </StarShell>
  );
}

function TrustCard({ profile }: { profile: PersonaProfileRead }) {
  const level = profile.trust_level || trustLevelForScore(profile.trust_score);
  return (
    <StarPanel className="p-5">
      <dt className="text-sm font-bold text-starMist/60">可信度</dt>
      <dd className="mt-2 flex items-end gap-1 text-starGold">
        <span className="font-serif text-5xl font-bold leading-none">{profile.trust_score}</span>
        <span className="pb-1 text-2xl font-bold">%</span>
      </dd>
      <p className="mt-2 text-sm font-bold text-starMist/70">{trustLevelLabel(level)}</p>
    </StarPanel>
  );
}

function DimensionSection({
  dimension,
  value,
  sourceMemoryIds,
  draft,
  onDraftChange
}: {
  dimension: ProfileDimension;
  value: ProfileValue;
  sourceMemoryIds: string[];
  draft: string;
  onDraftChange: (value: string) => void;
}) {
  return (
    <StarPanel className="p-5">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="font-serif text-2xl font-bold text-starGold">
            {profileDimensionLabel(dimension)}
          </h2>
          <p className="mt-2 text-sm font-semibold leading-7 text-starMist/70">
            {sourceMemoryIds.length > 0
              ? `${sourceMemoryIds.length} 条来源记忆：${sourceMemoryIds.join("、")}`
              : "这个维度暂未关联来源记忆。"}
          </p>
        </div>
      </div>

      <DimensionPreview value={value} />

      <label className="mt-5 grid gap-2 text-sm font-bold text-starMist/78">
        JSON 值
        <textarea
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          className={`${inputClass} min-h-44 resize-y font-mono`}
        />
      </label>
    </StarPanel>
  );
}

function DimensionPreview({ value }: { value: ProfileValue }) {
  if (Array.isArray(value) && value.length > 0 && value.every(isProfileEntry)) {
    return (
      <div className="mt-4 grid gap-3">
        {value.map((entry) => (
          <div
            key={entry.memory_id}
            className="rounded-2xl border border-white/8 bg-white/6 p-4"
          >
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-bold text-starCream">{entry.title}</h3>
              <span className="rounded-full bg-starGold/12 px-3 py-1 text-xs font-bold text-starGold">
                {entry.status}
              </span>
            </div>
            <p className="mt-2 whitespace-pre-wrap text-sm font-semibold leading-7 text-starMist/75">
              {entry.content}
            </p>
            <dl className="mt-3 grid gap-2 text-xs text-starMist/60 md:grid-cols-3">
              <SmallStat label="记忆 ID" value={entry.memory_id} />
              <SmallStat label="分类" value={entry.category} />
              <SmallStat label="置信度" value={entry.confidence_level} />
            </dl>
          </div>
        ))}
      </div>
    );
  }

  if (Array.isArray(value) && value.length === 0) {
    return (
      <p className="mt-4 rounded-2xl border border-white/8 bg-white/6 p-4 text-sm font-semibold text-starMist/70">
        这个维度暂时没有条目。
      </p>
    );
  }

  return (
    <pre className="mt-4 overflow-auto rounded-2xl border border-white/8 bg-black/18 p-4 text-xs leading-5 text-starMist/72">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <StarPanel className="p-5">
      <dt className="text-sm font-bold text-starMist/60">{label}</dt>
      <dd className="mt-2 text-2xl font-bold text-starGold">{value}</dd>
    </StarPanel>
  );
}

function SmallStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-bold">{label}</dt>
      <dd className="mt-1 break-words text-starCream">{value}</dd>
    </div>
  );
}

function Alert({ tone, text }: { tone: "error" | "success"; text: string }) {
  return (
    <div
      className={`rounded-2xl border p-4 text-sm font-bold ${
        tone === "error"
          ? "border-rose-300/20 bg-rose-500/15 text-rose-100"
          : "border-emerald-200/20 bg-emerald-400/12 text-emerald-100"
      }`}
    >
      {text}
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

function createEmptyDimensionDrafts(): DimensionDrafts {
  const drafts = {} as DimensionDrafts;
  for (const option of PROFILE_DIMENSION_OPTIONS) {
    drafts[option.value] = "[]";
  }
  return drafts;
}

function buildDimensionDrafts(profile: PersonaProfileRead): DimensionDrafts {
  const drafts = {} as DimensionDrafts;
  for (const option of PROFILE_DIMENSION_OPTIONS) {
    drafts[option.value] = JSON.stringify(profile[option.value], null, 2);
  }
  return drafts;
}

function buildUpdatePayload(
  profile: PersonaProfileRead,
  summaryDraft: string,
  dimensionDrafts: DimensionDrafts
): PersonaProfileUpdate {
  const payload: PersonaProfileUpdate = {};
  const nextSummary = summaryDraft.trim();

  if (nextSummary !== (profile.profile_summary ?? "")) {
    payload.profile_summary = nextSummary;
  }

  for (const option of PROFILE_DIMENSION_OPTIONS) {
    const dimension = option.value;
    const parsed = parseDimensionDraft(dimension, dimensionDrafts[dimension]);
    if (JSON.stringify(parsed) !== JSON.stringify(profile[dimension])) {
      payload[dimension] = parsed;
    }
  }

  return payload;
}

function parseDimensionDraft(
  dimension: ProfileDimension,
  value: string
): ProfileValue {
  let parsed: unknown;
  try {
    parsed = JSON.parse(value.trim() || "[]");
  } catch {
    throw new Error(`${profileDimensionLabel(dimension)} 必须是有效 JSON。`);
  }

  if (!isProfileValue(parsed)) {
    throw new Error(`${profileDimensionLabel(dimension)} 必须是 JSON 对象或数组。`);
  }

  return parsed;
}

function isProfileValue(value: unknown): value is ProfileValue {
  return typeof value === "object" && value !== null;
}

function isProfileEntry(value: unknown): value is ProfileDimensionEntry {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const entry = value as Record<string, unknown>;
  return (
    typeof entry.memory_id === "string" &&
    typeof entry.title === "string" &&
    typeof entry.content === "string" &&
    typeof entry.category === "string" &&
    typeof entry.confidence_level === "string" &&
    typeof entry.status === "string"
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

const inputClass = "star-input text-sm";
const primaryButtonClass = "star-button min-w-28 disabled:opacity-60";
const secondaryButtonClass =
  "rounded-full border border-starGold/22 bg-starGold/10 px-4 py-2.5 text-sm font-bold text-starCream transition hover:bg-starGold/16 disabled:cursor-not-allowed disabled:opacity-35";
