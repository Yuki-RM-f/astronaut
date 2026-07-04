"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { DemoEntry } from "@/src/components/DemoEntry";
import {
  GlassPanel,
  MemoryContainer,
  MemoryShell,
  MemoryTitle,
  StepRibbon
} from "@/src/components/MemorySpace";
import { getAuthToken } from "@/src/lib/auth";
import {
  canUseMemoryInConversation,
  confirmMemory,
  deleteMemory,
  disableMemory,
  listMemories,
  MEMORY_CATEGORY_OPTIONS,
  MEMORY_CONFIDENCE_OPTIONS,
  MEMORY_STATUS_OPTIONS,
  MemoryCategory,
  MemoryConfidenceLevel,
  MemoryRead,
  MemoryStatus,
  memoryCategoryLabel,
  memoryConfidenceLabel,
  memorySourceTypeLabel,
  memoryStatusLabel,
  rejectMemory,
  updateMemory
} from "@/src/lib/memories";
import { ROUTES } from "@/src/lib/routes";

type PageState = "checking" | "signedOut" | "loading" | "ready" | "error";
type MemoryFilter<T extends string> = "all" | T;

export default function PersonaMemoriesPage() {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<PageState>("checking");
  const [memories, setMemories] = useState<MemoryRead[]>([]);
  const [statusFilter, setStatusFilter] =
    useState<MemoryFilter<MemoryStatus>>("all");
  const [categoryFilter, setCategoryFilter] =
    useState<MemoryFilter<MemoryCategory>>("all");
  const [confidenceFilter, setConfidenceFilter] =
    useState<MemoryFilter<MemoryConfidenceLevel>>("all");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyMemoryId, setBusyMemoryId] = useState<string | null>(null);

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

    listMemories(personaId, {
      status: statusFilter === "all" ? undefined : statusFilter,
      category: categoryFilter === "all" ? undefined : categoryFilter,
      confidence_level: confidenceFilter === "all" ? undefined : confidenceFilter
    })
      .then((items) => {
        if (!isCurrent) {
          return;
        }
        setMemories(items);
        setState("ready");
      })
      .catch((caught) => {
        if (!isCurrent) {
          return;
        }
        setError(caught instanceof Error ? caught.message : "无法加载记忆。");
        setState("error");
      });

    return () => {
      isCurrent = false;
    };
  }, [personaId, statusFilter, categoryFilter, confidenceFilter]);

  async function refreshMemories() {
    if (!personaId) {
      return;
    }
    setMemories(
      await listMemories(personaId, {
        status: statusFilter === "all" ? undefined : statusFilter,
        category: categoryFilter === "all" ? undefined : categoryFilter,
        confidence_level: confidenceFilter === "all" ? undefined : confidenceFilter
      })
    );
  }

  async function runMemoryAction(
    memory: MemoryRead,
    action: () => Promise<MemoryRead | void>,
    successMessage: string
  ) {
    setError(null);
    setNotice(null);
    setBusyMemoryId(memory.id);
    try {
      await action();
      await refreshMemories();
      setNotice(successMessage);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法更新记忆。");
    } finally {
      setBusyMemoryId(null);
    }
  }

  const stats = buildStats(memories);

  return (
    <MemoryShell background="memoryStringLights">
      <MemoryContainer>
      <div className="flex flex-wrap items-center gap-3 text-sm font-semibold text-memoryAccent">
        <Link href={personaId ? ROUTES.personaDetail(personaId) : ROUTES.dashboard}>
          返回记忆空间
        </Link>
        {personaId ? <Link href={ROUTES.personaUploads(personaId)}>上传资料</Link> : null}
        {personaId ? <Link href={ROUTES.personaJobs(personaId)}>查看任务</Link> : null}
      </div>

      <div className="mt-6 grid gap-5">
        <MemoryTitle
          title="资料解析与审核"
          subtitle="这些记忆会影响后续人格档案、可信度和文本对话。只有已确认或已修正的记忆会进入对话检索。"
        />
        <StepRibbon activeIndex={2} />
      </div>

      {state === "signedOut" ? <SignedOutState /> : null}
      {state === "loading" || state === "checking" ? <Notice text="正在加载记忆..." /> : null}
      {state === "error" ? <Notice text={error ?? "无法加载记忆。"} /> : null}

      {state === "ready" ? (
        <div className="mt-8 grid gap-6">
          <section className="grid gap-3 md:grid-cols-4">
            <StatCard label="全部" value={stats.total} />
            <StatCard label="待审核" value={stats.pending} />
            <StatCard label="高置信" value={stats.high} />
            <StatCard label="低置信" value={stats.low} />
          </section>

          <GlassPanel>
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h2 className="font-serif text-2xl font-semibold text-memoryText">筛选记忆</h2>
                <p className="mt-2 text-sm leading-7 text-memoryText/70">
                  按审核状态、记忆分类和置信度缩小范围。
                </p>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <FilterSelect
                  label="状态"
                  value={statusFilter}
                  options={MEMORY_STATUS_OPTIONS}
                  onChange={(value) => setStatusFilter(value as MemoryFilter<MemoryStatus>)}
                />
                <FilterSelect
                  label="分类"
                  value={categoryFilter}
                  options={MEMORY_CATEGORY_OPTIONS}
                  onChange={(value) => setCategoryFilter(value as MemoryFilter<MemoryCategory>)}
                />
                <FilterSelect
                  label="置信度"
                  value={confidenceFilter}
                  options={MEMORY_CONFIDENCE_OPTIONS}
                  onChange={(value) =>
                    setConfidenceFilter(value as MemoryFilter<MemoryConfidenceLevel>)
                  }
                />
              </div>
            </div>
          </GlassPanel>

          {error ? <Alert tone="error" text={error} /> : null}
          {notice ? <Alert tone="success" text={notice} /> : null}

          <GlassPanel>
            <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="font-serif text-2xl font-semibold text-memoryText">记忆卡片</h2>
                <p className="mt-2 text-sm leading-7 text-memoryText/70">
                  确认准确内容，修正不准确内容，或停用不应进入后续对话的记忆。
                </p>
              </div>
              <span className="text-sm font-semibold text-memoryText/60">
                {memories.length} 条
              </span>
            </div>

            {memories.length === 0 ? (
              <p className="mt-6 rounded-2xl bg-memoryPaper/75 p-4 text-sm text-memoryText/70">
                当前筛选下没有记忆。可以先上传资料，等待 mock 解析生成记忆卡片。
              </p>
            ) : (
              <div className="mt-6 grid gap-3">
                {memories.map((memory) => (
                  <MemoryCard
                    key={memory.id}
                    memory={memory}
                    busy={busyMemoryId === memory.id}
                    onConfirm={(selectedMemory) =>
                      runMemoryAction(
                        selectedMemory,
                        () => confirmMemory(selectedMemory.id),
                        "记忆已确认。"
                      )
                    }
                    onReject={(selectedMemory) =>
                      runMemoryAction(
                        selectedMemory,
                        () => rejectMemory(selectedMemory.id),
                        "记忆已拒绝。"
                      )
                    }
                    onDisable={(selectedMemory) =>
                      runMemoryAction(
                        selectedMemory,
                        () => disableMemory(selectedMemory.id),
                        "记忆已停用。"
                      )
                    }
                    onDelete={(selectedMemory) =>
                      runMemoryAction(
                        selectedMemory,
                        () => deleteMemory(selectedMemory.id),
                        "记忆已删除。"
                      )
                    }
                    onUpdate={(selectedMemory, title, content) =>
                      runMemoryAction(
                        selectedMemory,
                        () => updateMemory(selectedMemory.id, { title, content }),
                        "记忆修正已保存。"
                      )
                    }
                  />
                ))}
              </div>
            )}
          </GlassPanel>
        </div>
      ) : null}
      </MemoryContainer>
    </MemoryShell>
  );
}

function SignedOutState() {
  return (
    <GlassPanel className="mt-8 max-w-3xl">
      <h2 className="font-serif text-2xl font-semibold text-memoryText">需要先进入记忆空间</h2>
      <p className="mt-2 max-w-2xl text-sm leading-7 text-memoryText/70">
        可以免注册体验外婆示例，或登录已有账号审核私有记忆。
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

function MemoryCard({
  memory,
  busy,
  onConfirm,
  onReject,
  onDisable,
  onDelete,
  onUpdate
}: {
  memory: MemoryRead;
  busy: boolean;
  onConfirm: (memory: MemoryRead) => void;
  onReject: (memory: MemoryRead) => void;
  onDisable: (memory: MemoryRead) => void;
  onDelete: (memory: MemoryRead) => void;
  onUpdate: (memory: MemoryRead, title: string, content: string) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [title, setTitle] = useState(memory.title);
  const [content, setContent] = useState(memory.content);

  useEffect(() => {
    if (!isEditing) {
      setTitle(memory.title);
      setContent(memory.content);
    }
  }, [isEditing, memory.content, memory.title]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onUpdate(memory, title, content);
    setIsEditing(false);
  }

  return (
    <article className="paper-note rounded-2xl border border-memoryLine/60 bg-memoryPaper/90 p-5 shadow-soft">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          {isEditing ? (
            <form className="grid gap-3" onSubmit={handleSubmit}>
              <label className="grid gap-2 text-sm font-semibold text-memoryText">
                标题
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  className={inputClass}
                  required
                />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-memoryText">
                内容
                <textarea
                  value={content}
                  onChange={(event) => setContent(event.target.value)}
                  className={`${inputClass} min-h-28 resize-y`}
                  required
                />
              </label>
              <div className="flex flex-wrap gap-2">
                <button type="submit" disabled={busy} className={primaryButtonClass}>
                  保存修正
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => setIsEditing(false)}
                  className={secondaryButtonClass}
                >
                  取消
                </button>
              </div>
            </form>
          ) : (
            <>
              <div className="flex flex-wrap items-start gap-2">
                <h3 className="text-base font-semibold text-memoryText">{memory.title}</h3>
                <span className="rounded-full bg-white/85 px-3 py-1 text-xs font-semibold text-memoryAccent">
                  {memoryStatusLabel(memory.status)}
                </span>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-memoryText/75">
                {memory.content}
              </p>
              <dl className="mt-4 grid gap-3 text-xs text-memoryText/60 md:grid-cols-3">
                <Stat label="分类" value={memoryCategoryLabel(memory.category)} />
                <Stat
                  label="置信度"
                  value={`${memoryConfidenceLabel(memory.confidence_level)} (${memory.confidence_score}/100)`}
                />
                <Stat
                  label="对话可用"
                  value={
                    canUseMemoryInConversation(memory.status)
                      ? "会进入后续对话"
                      : "不会进入后续对话"
                  }
                />
                <Stat label="来源类型" value={memorySourceTypeLabel(memory.source_type)} />
                <Stat
                  label="资料 ID"
                  value={memory.source_material_id ?? "未关联"}
                />
                <Stat label="更新时间" value={formatDate(memory.updated_at)} />
              </dl>
              <div className="mt-4 rounded-2xl bg-white/72 p-3">
                <p className="text-xs font-semibold tracking-[0.08em] text-memoryAccent">
                  来源摘录
                </p>
                <p className="mt-2 text-sm leading-6 text-memoryText/70">
                  {memory.source_quote || "暂无来源摘录。"}
                </p>
                <p className="mt-2 text-xs text-memoryText/50">
                  {memory.source_location || "暂无来源位置。"}
                </p>
              </div>
            </>
          )}
        </div>

        {!isEditing ? (
          <div className="flex flex-wrap gap-2 lg:max-w-52">
            <button
              type="button"
              disabled={busy}
              onClick={() => onConfirm(memory)}
              className={secondaryButtonClass}
            >
              确认
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => setIsEditing(true)}
              className={secondaryButtonClass}
            >
              修正
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => onReject(memory)}
              className={secondaryButtonClass}
            >
              拒绝
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => onDisable(memory)}
              className={secondaryButtonClass}
            >
              停用
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => onDelete(memory)}
              className={dangerButtonClass}
            >
              删除
            </button>
          </div>
        ) : null}
      </div>
    </article>
  );
}

function FilterSelect<T extends string>({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: MemoryFilter<T>;
  options: readonly { value: T; label: string }[];
  onChange: (value: MemoryFilter<T>) => void;
}) {
  return (
    <label className="grid gap-2 text-sm font-semibold text-memoryText">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as MemoryFilter<T>)}
        className={inputClass}
      >
        <option value="all">全部</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[1.5rem] border border-white/70 bg-white/74 p-4 text-memoryText shadow-soft backdrop-blur">
      <dt className="text-sm font-semibold text-memoryText/60">{label}</dt>
      <dd className="mt-2 text-3xl font-semibold text-memoryAccent">{value}</dd>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-medium">{label}</dt>
      <dd className="mt-1 break-words text-memoryText">{value}</dd>
    </div>
  );
}

function Alert({ tone, text }: { tone: "error" | "success"; text: string }) {
  const className =
    tone === "error"
      ? "border-red-200 bg-red-50 text-red-700"
      : "border-memoryAccent/25 bg-memoryWarm/70 text-memoryAccentDark";

  return <div className={`rounded-lg border p-4 text-sm ${className}`}>{text}</div>;
}

function Notice({ text }: { text: string }) {
  return (
    <GlassPanel className="mt-8 text-sm leading-7 text-memoryText/72">
      {text}
    </GlassPanel>
  );
}

function buildStats(memories: MemoryRead[]) {
  return {
    total: memories.length,
    pending: memories.filter((memory) => memory.status === "pending_review").length,
    high: memories.filter((memory) => memory.confidence_level === "high").length,
    low: memories.filter((memory) => memory.confidence_level === "low").length
  };
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

const inputClass =
  "rounded-2xl border border-memoryLine/80 bg-white/74 px-4 py-3 text-sm text-memoryText outline-none transition focus:border-memoryAccent focus:ring-4 focus:ring-memoryAccent/20";

const primaryButtonClass =
  "memory-button rounded-2xl bg-memoryAccent px-4 py-2.5 text-sm font-semibold text-white shadow-warm transition hover:bg-memoryAccentDark focus:outline-none focus:ring-4 focus:ring-memoryAccent/25 disabled:cursor-not-allowed disabled:bg-memoryText/30";

const secondaryButtonClass =
  "rounded-2xl border border-memoryLine/80 bg-white/72 px-3 py-2 text-sm font-semibold text-memoryText shadow-soft transition hover:border-memoryAccent hover:text-memoryAccent disabled:cursor-not-allowed disabled:border-memoryLine/40 disabled:text-memoryText/35";

const dangerButtonClass =
  "rounded-2xl border border-red-200 bg-white/72 px-3 py-2 text-sm font-semibold text-red-700 transition hover:border-red-300 hover:bg-red-50 disabled:cursor-not-allowed disabled:border-memoryLine/40 disabled:text-memoryText/35";
