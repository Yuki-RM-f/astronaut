"use client";

import { useParams, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Flower2,
  Heart,
  History,
  MessageSquareText,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
  Utensils
} from "lucide-react";
import { PageTitle, StarNav, StarPanel, StarShell } from "@/src/components/StarSite";
import { ensureDemoSession } from "@/src/lib/auth";
import {
  confirmMemory,
  deleteMemory,
  listMemories,
  memoryCategoryLabel,
  MemoryRead,
  selectDimensionActionTargets,
  updateMemory
} from "@/src/lib/memories";
import {
  auditEventLabel,
  auditSeverityLabel,
  conflictStatusLabel,
  formatRelevanceScore,
  getAuditDashboard,
  getMemoryHistory,
  listAuditLogs,
  listConflicts,
  resolveConflict,
  searchAuditMemories,
  AuditDashboardResponse,
  AuditLogRead,
  MemoryConflictRead,
  MemoryHistoryResponse,
  ResolveConflictStatus,
  SearchResultItem
} from "@/src/lib/audit";
import { ROUTES } from "@/src/lib/routes";

type PageState = "checking" | "loading" | "ready" | "error";

const COMPLETE_REVIEW_BUSY_ID = "__complete_review__";

type CustomDimension = {
  id: string;
  title: string;
  items: string[];
  confirmed: boolean;
};

const CATEGORY_VIEW = [
  { key: "basic_fact", title: "基础信息", icon: Flower2, color: "text-rose-200" },
  { key: "relationship", title: "人物关系", icon: Users, color: "text-amber-200" },
  { key: "preference", title: "兴趣偏好", icon: Heart, color: "text-pink-200" },
  { key: "habit", title: "生活习惯", icon: Utensils, color: "text-violet-200" },
  { key: "expression_style", title: "表达习惯", icon: MessageSquareText, color: "text-rose-200" },
  { key: "shared_event", title: "共同经历", icon: MessageSquareText, color: "text-amber-100" }
] as const;

async function loadAuditData(personaId: string) {
  const [dashboard, logs, conflicts] = await Promise.all([
    getAuditDashboard(personaId),
    listAuditLogs(personaId, { limit: 12 }),
    listConflicts(personaId)
  ]);
  return {
    dashboard,
    logs: logs.items,
    conflicts: conflicts.items
  };
}

export default function PersonaMemoriesPage() {
  const router = useRouter();
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<PageState>("checking");
  const [memories, setMemories] = useState<MemoryRead[]>([]);
  const [customDimensions, setCustomDimensions] = useState<CustomDimension[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [dashboard, setDashboard] = useState<AuditDashboardResponse | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogRead[]>([]);
  const [conflicts, setConflicts] = useState<MemoryConflictRead[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [memoryHistory, setMemoryHistory] = useState<MemoryHistoryResponse | null>(null);
  const [auditBusyId, setAuditBusyId] = useState<string | null>(null);

  useEffect(() => {
    if (!personaId) {
      setError("缺少人物 ID。");
      setState("error");
      return;
    }

    setCustomDimensions(readCustomDimensions(personaId));

    let isCurrent = true;
    setState("loading");
    ensureDemoSession()
      .then(() => Promise.all([listMemories(personaId), loadAuditData(personaId)]))
      .then(([items, auditData]) => {
        if (!isCurrent) {
          return;
        }
        setMemories(items);
        setDashboard(auditData.dashboard);
        setAuditLogs(auditData.logs);
        setConflicts(auditData.conflicts);
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
  }, [personaId]);

  async function refresh() {
    if (!personaId) {
      return;
    }
    const [items, auditData] = await Promise.all([
      listMemories(personaId),
      loadAuditData(personaId)
    ]);
    setMemories(items);
    setDashboard(auditData.dashboard);
    setAuditLogs(auditData.logs);
    setConflicts(auditData.conflicts);
  }

  async function runMemoryAction(
    memory: MemoryRead,
    action: () => Promise<unknown>,
    message: string
  ) {
    setBusyId(memory.id);
    setError(null);
    setNotice(null);
    try {
      await action();
      await refresh();
      setNotice(message);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "操作失败。");
    } finally {
      setBusyId(null);
    }
  }

  async function runMemoryBatchAction(
    ids: string[],
    action: (id: string) => Promise<unknown>,
    message: string,
    busyKey: string
  ) {
    if (ids.length === 0) {
      setNotice("暂无可操作记忆。");
      return;
    }

    setBusyId(busyKey);
    setError(null);
    setNotice(null);
    try {
      await Promise.all(ids.map((id) => action(id)));
      await refresh();
      setNotice(message);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "操作失败。");
    } finally {
      setBusyId(null);
    }
  }

  async function handleSearch() {
    if (!personaId) {
      return;
    }
    setAuditBusyId("search");
    setError(null);
    setNotice(null);
    try {
      const results = await searchAuditMemories(personaId, searchQuery, 6);
      setSearchResults(results.items);
      const auditData = await loadAuditData(personaId);
      setDashboard(auditData.dashboard);
      setAuditLogs(auditData.logs);
      setConflicts(auditData.conflicts);
      setNotice(results.items.length > 0 ? "已完成语义搜索。" : "未找到匹配记忆。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法完成语义搜索。");
    } finally {
      setAuditBusyId(null);
    }
  }

  async function handleOpenHistory(memoryId: string) {
    setAuditBusyId(`history:${memoryId}`);
    setError(null);
    try {
      setMemoryHistory(await getMemoryHistory(memoryId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法加载记忆历史。");
    } finally {
      setAuditBusyId(null);
    }
  }

  async function handleResolveConflict(
    conflict: MemoryConflictRead,
    resolutionStatus: ResolveConflictStatus
  ) {
    if (!personaId) {
      return;
    }
    setAuditBusyId(`conflict:${conflict.id}:${resolutionStatus}`);
    setError(null);
    setNotice(null);
    try {
      await resolveConflict(personaId, conflict.id, resolutionStatus);
      const auditData = await loadAuditData(personaId);
      setDashboard(auditData.dashboard);
      setAuditLogs(auditData.logs);
      setConflicts(auditData.conflicts);
      setMemoryHistory(await getMemoryHistory(conflict.memory_id_a));
      setNotice("冲突状态已更新。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法处理记忆冲突。");
    } finally {
      setAuditBusyId(null);
    }
  }

  function saveCustomDimensions(nextDimensions: CustomDimension[]) {
    setCustomDimensions(nextDimensions);
    if (personaId) {
      writeCustomDimensions(personaId, nextDimensions);
    }
  }

  function handleCreateCustomDimension(title: string, items: string[]) {
    const nextDimension: CustomDimension = {
      id: `custom-${Date.now()}`,
      title,
      items,
      confirmed: false
    };
    saveCustomDimensions([...customDimensions, nextDimension]);
    setIsAdding(false);
    setNotice("新维度已添加。");
  }

  function handleUpdateCustomDimension(id: string, title: string, items: string[]) {
    saveCustomDimensions(
      customDimensions.map((dimension) =>
        dimension.id === id ? { ...dimension, title, items, confirmed: false } : dimension
      )
    );
    setNotice("维度已更新。");
  }

  function handleDeleteCustomDimension(id: string) {
    saveCustomDimensions(customDimensions.filter((dimension) => dimension.id !== id));
    setNotice("维度已删除。");
  }

  function handleConfirmCustomDimension(id: string) {
    saveCustomDimensions(
      customDimensions.map((dimension) =>
        dimension.id === id ? { ...dimension, confirmed: true } : dimension
      )
    );
    setNotice("维度已确认。");
  }

  async function handleCompleteReview() {
    setBusyId(COMPLETE_REVIEW_BUSY_ID);
    setError(null);
    setNotice(null);
    try {
      const pendingMemories = memories.filter(
        (memory) =>
          !["confirmed", "corrected", "rejected", "disabled"].includes(memory.status)
      );
      await Promise.all(pendingMemories.map((memory) => confirmMemory(memory.id)));
      const confirmedDimensions = customDimensions.map((dimension) => ({
        ...dimension,
        confirmed: true
      }));
      saveCustomDimensions(confirmedDimensions);
      await refresh();
      setNotice("审核已完成，星星已点亮。");
      if (personaId) {
        router.push(ROUTES.personaChat(personaId));
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法完成审核。");
    } finally {
      setBusyId(null);
    }
  }

  const trust = calculateTrust(memories);

  return (
    <StarShell>
      <StarNav />
      <main className="mx-auto w-full max-w-7xl px-5 pb-10 sm:px-8 lg:px-10">
        <PageTitle
          title="记忆解析与审核"
          subtitle="在同一片星空里审核记忆、查看来源、处理冲突，并确认这些片段是否足以支撑TA的人格画像。"
        />

        {state === "loading" || state === "checking" ? <Notice text="正在读取记忆星图..." /> : null}
        {state === "error" ? <Notice text={error ?? "无法加载记忆。"} /> : null}

        {state === "ready" ? (
          <div className="mt-6 grid gap-4">
            <TrustBanner
              trust={trust}
              onRefresh={() => void refresh()}
              onAddDimension={() => setIsAdding(true)}
            />

            {error ? <Alert tone="error" text={error} /> : null}
            {notice ? <Alert tone="success" text={notice} /> : null}

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {CATEGORY_VIEW.map((category) => (
                <MemoryDimensionCard
                  key={category.key}
                  busyKey={`${category.key}:batch`}
                  title={category.title}
                  icon={category.icon}
                  color={category.color}
                  memories={memories.filter((memory) => memory.category === category.key)}
                  fallback={sampleItems(category.key)}
                  busyId={busyId}
                  onConfirm={(ids) =>
                    void runMemoryBatchAction(
                      ids,
                      confirmMemory,
                      "该维度记忆已确认。",
                      `${category.key}:batch`
                    )
                  }
                  onDelete={(ids) =>
                    void runMemoryBatchAction(
                      ids,
                      deleteMemory,
                      "该维度记忆已删除。",
                      `${category.key}:batch`
                    )
                  }
                  onUpdate={(memory, content) =>
                    runMemoryAction(
                      memory,
                      () => updateMemory(memory.id, { content }),
                      "记忆已更新。"
                    )
                  }
                />
              ))}

              {customDimensions.map((dimension) => (
                <CustomDimensionCard
                  key={dimension.id}
                  dimension={dimension}
                  onUpdate={handleUpdateCustomDimension}
                  onDelete={handleDeleteCustomDimension}
                  onConfirm={handleConfirmCustomDimension}
                />
              ))}

              {isAdding ? (
                <CustomDimensionEditor
                  onCreate={handleCreateCustomDimension}
                  onCancel={() => setIsAdding(false)}
                />
              ) : null}
            </section>

            <div className="flex justify-center pb-2 pt-3">
              <button
                type="button"
                disabled={busyId === COMPLETE_REVIEW_BUSY_ID}
                onClick={() => void handleCompleteReview()}
                className="group inline-flex w-full max-w-[46rem] items-center justify-center gap-4 rounded-full border border-starGold/45 bg-[linear-gradient(180deg,#ffd4a1_0%,#f3a95f_100%)] px-8 py-5 text-xl font-black text-violet-950 shadow-[0_0_28px_rgba(255,184,105,0.56),inset_0_1px_0_rgba(255,255,255,0.55)] transition hover:-translate-y-0.5 hover:shadow-[0_0_38px_rgba(255,198,121,0.72),inset_0_1px_0_rgba(255,255,255,0.65)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {busyId === COMPLETE_REVIEW_BUSY_ID ? "正在点亮星星..." : "完成审核，点亮星星"}
                <Sparkles className="h-5 w-5 fill-current transition group-hover:scale-110" />
              </button>
            </div>

            <section className="grid gap-4 pt-2">
              <AuditDashboardPanel dashboard={dashboard} memories={memories} logs={auditLogs} />

              <div className="grid gap-4 lg:grid-cols-[1.12fr_0.88fr]">
                <AuditSearchPanel
                  query={searchQuery}
                  results={searchResults}
                  busy={auditBusyId === "search"}
                  onQueryChange={setSearchQuery}
                  onSearch={() => void handleSearch()}
                  onOpenHistory={(memoryId) => void handleOpenHistory(memoryId)}
                />
                <ConflictCenter
                  conflicts={conflicts}
                  busyId={auditBusyId}
                  onOpenHistory={(memoryId) => void handleOpenHistory(memoryId)}
                  onResolve={(conflict, status) =>
                    void handleResolveConflict(conflict, status)
                  }
                />
              </div>

              <AuditTimeline
                logs={auditLogs}
                history={memoryHistory}
                busyId={auditBusyId}
                onClearHistory={() => setMemoryHistory(null)}
              />
            </section>
          </div>
        ) : null}
      </main>
    </StarShell>
  );
}

function TrustBanner({
  trust,
  onRefresh,
  onAddDimension
}: {
  trust: number;
  onRefresh: () => void;
  onAddDimension: () => void;
}) {
  return (
    <StarPanel className="overflow-hidden p-0">
      <div className="grid min-h-[8.6rem] md:grid-cols-[0.48fr_0.52fr]">
        <div className="relative grid place-items-center border-b border-white/8 px-6 py-5 md:border-b-0 md:border-r">
          <div className="relative text-center">
            <p className="text-sm font-bold text-starGold">记忆可信度</p>
            <div className="relative mt-1 inline-flex items-end gap-1 text-starGold">
              <span className="absolute left-1/2 top-1/2 h-12 w-44 -translate-x-1/2 -translate-y-1/2 rotate-[-10deg] rounded-full border border-starGold/32" />
              <span className="relative font-serif text-7xl font-bold leading-none">{trust}</span>
              <span className="relative pb-2 text-4xl font-bold">%</span>
              <Sparkles className="relative mb-5 h-5 w-5" aria-hidden="true" />
            </div>
          </div>
        </div>
        <div className="flex flex-col items-center justify-center px-6 py-5 text-center md:items-start md:text-left">
          <p className="max-w-md text-sm font-bold leading-7 text-starMist/78">
            基于你提供的回忆，AI已提取关键信息。请为TA完善星谱，让TA的星星更加闪亮。
          </p>
          <div className="mt-4 flex flex-wrap justify-center gap-3 md:justify-start">
            <button
              type="button"
              onClick={onRefresh}
              className="rounded-xl border border-violet-200/18 bg-violet-400/14 px-7 py-2.5 text-sm font-bold text-violet-100 transition hover:bg-violet-400/22"
            >
              重新解析
            </button>
            <button
              type="button"
              onClick={onAddDimension}
              className="inline-flex items-center gap-2 rounded-xl border border-starGold/30 bg-starGold/12 px-7 py-2.5 text-sm font-bold text-starCream transition hover:bg-starGold/18"
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              新增维度
            </button>
          </div>
        </div>
      </div>
    </StarPanel>
  );
}

function AuditDashboardPanel({
  dashboard,
  memories,
  logs
}: {
  dashboard: AuditDashboardResponse | null;
  memories: MemoryRead[];
  logs: AuditLogRead[];
}) {
  const pendingCount =
    dashboard?.pending_review_count ??
    memories.filter((memory) => memory.status === "pending_review").length;
  const openConflicts = dashboard?.open_conflict_count ?? 0;
  const healthScore = dashboard?.health_score ?? calculateTrust(memories);
  const latestEvent = logs[0];

  return (
    <StarPanel className="p-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <AuditMetric
          icon={ShieldCheck}
          label="档案健康分"
          value={`${healthScore}`}
          detail="越高代表记忆越稳定"
        />
        <AuditMetric
          icon={Sparkles}
          label="待审核"
          value={`${pendingCount}`}
          detail="继续点亮记忆星点"
        />
        <AuditMetric
          icon={AlertTriangle}
          label="开放冲突"
          value={`${openConflicts}`}
          detail={openConflicts > 0 ? "建议先处理" : "当前稳定"}
        />
        <AuditMetric
          icon={Activity}
          label="最近事件"
          value={latestEvent ? auditEventLabel(latestEvent.event_type) : "暂无"}
          detail={latestEvent ? formatAuditTime(latestEvent.created_at) : "等待审计写入"}
        />
      </div>
      <div className="mt-3 rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-3 text-xs font-semibold leading-6 text-starMist/68">
        来源覆盖：{sourceCoverageText(dashboard?.source_coverage ?? {})}
      </div>
    </StarPanel>
  );
}

function AuditMetric({
  icon: Icon,
  label,
  value,
  detail
}: {
  icon: typeof Flower2;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="flex min-h-[5.4rem] items-center gap-3 rounded-2xl border border-white/8 bg-white/[0.05] px-4 py-3">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-starGold/12 text-starGold">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-bold text-starMist/62">{label}</p>
        <p className="truncate text-lg font-black text-starCream">{value}</p>
        <p className="truncate text-xs font-semibold text-starMist/54">{detail}</p>
      </div>
    </div>
  );
}

function AuditSearchPanel({
  query,
  results,
  busy,
  onQueryChange,
  onSearch,
  onOpenHistory
}: {
  query: string;
  results: SearchResultItem[];
  busy: boolean;
  onQueryChange: (value: string) => void;
  onSearch: () => void;
  onOpenHistory: (memoryId: string) => void;
}) {
  return (
    <StarPanel className="p-4">
      <div className="flex items-center gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-full bg-violet-300/14 text-violet-100">
          <Search className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <h2 className="font-serif text-xl font-bold text-starGold">语义搜索</h2>
          <p className="text-xs font-semibold text-starMist/58">检索记忆标题、内容和来源摘录。</p>
        </div>
      </div>
      <form
        className="mt-4 flex flex-col gap-3 sm:flex-row"
        onSubmit={(event) => {
          event.preventDefault();
          onSearch();
        }}
      >
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          className="star-input min-h-[2.8rem] flex-1 text-sm"
          placeholder="输入关键词，例如：馄饨、生日、慢慢来"
        />
        <button
          type="submit"
          disabled={busy || !query.trim()}
          className="rounded-xl border border-starGold/26 bg-starGold/14 px-5 py-2 text-sm font-bold text-starCream transition hover:bg-starGold/22 disabled:cursor-not-allowed disabled:opacity-45"
        >
          {busy ? "搜索中" : "搜索"}
        </button>
      </form>

      <div className="mt-4 divide-y divide-white/8">
        {results.length === 0 ? (
          <p className="py-4 text-sm font-semibold text-starMist/58">暂无搜索结果。</p>
        ) : (
          results.slice(0, 5).map((result) => (
            <button
              key={result.memory.id}
              type="button"
              onClick={() => onOpenHistory(result.memory.id)}
              className="grid w-full gap-1 py-3 text-left transition hover:text-starGold"
            >
              <span className="flex flex-wrap items-center gap-2 text-sm font-black text-starCream">
                {result.memory.title}
                <span className="rounded-full bg-starGold/12 px-2 py-0.5 text-xs text-starGold">
                  {formatRelevanceScore(result.relevance_score)}
                </span>
                <span className="rounded-full bg-white/8 px-2 py-0.5 text-xs text-starMist/70">
                  {memoryCategoryLabel(result.memory.category)}
                </span>
              </span>
              <span className="line-clamp-2 text-xs font-semibold leading-5 text-starMist/62">
                {result.source_excerpt ?? result.memory.content}
              </span>
            </button>
          ))
        )}
      </div>
    </StarPanel>
  );
}

function ConflictCenter({
  conflicts,
  busyId,
  onOpenHistory,
  onResolve
}: {
  conflicts: MemoryConflictRead[];
  busyId: string | null;
  onOpenHistory: (memoryId: string) => void;
  onResolve: (conflict: MemoryConflictRead, status: ResolveConflictStatus) => void;
}) {
  const sortedConflicts = [...conflicts].sort((left, right) => {
    if (left.resolution_status === right.resolution_status) {
      return left.created_at < right.created_at ? 1 : -1;
    }
    return left.resolution_status === "open" ? -1 : 1;
  });

  return (
    <StarPanel className="p-4">
      <div className="flex items-center gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-full bg-rose-300/14 text-rose-100">
          <AlertTriangle className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <h2 className="font-serif text-xl font-bold text-starGold">冲突中心</h2>
          <p className="text-xs font-semibold text-starMist/58">处理互相矛盾的记忆线索。</p>
        </div>
      </div>

      <div className="mt-4 divide-y divide-white/8">
        {sortedConflicts.length === 0 ? (
          <p className="py-4 text-sm font-semibold text-starMist/58">暂无开放冲突。</p>
        ) : (
          sortedConflicts.slice(0, 5).map((conflict) => {
            const isOpen = conflict.resolution_status === "open";
            return (
              <div key={conflict.id} className="grid gap-3 py-3">
                <button
                  type="button"
                  onClick={() => onOpenHistory(conflict.memory_id_a)}
                  className="grid gap-1 text-left"
                >
                  <span className="text-sm font-black text-starCream">
                    {conflict.memory_title_a ?? "记忆 A"} / {conflict.memory_title_b ?? "记忆 B"}
                  </span>
                  <span className="text-xs font-semibold leading-5 text-starMist/62">
                    {conflict.conflict_description}
                  </span>
                  <span className="text-xs font-bold text-starGold">
                    {conflictStatusLabel(conflict.resolution_status)}
                  </span>
                </button>
                {isOpen ? (
                  <div className="grid gap-2 sm:grid-cols-2">
                    <button
                      type="button"
                      disabled={busyId === `conflict:${conflict.id}:resolved_by_user`}
                      onClick={() => onResolve(conflict, "resolved_by_user")}
                      className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-300/16 px-3 py-2 text-xs font-black text-emerald-100 transition hover:bg-emerald-300/24 disabled:opacity-45"
                    >
                      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                      已处理
                    </button>
                    <button
                      type="button"
                      disabled={busyId === `conflict:${conflict.id}:dismissed`}
                      onClick={() => onResolve(conflict, "dismissed")}
                      className="rounded-lg bg-white/8 px-3 py-2 text-xs font-black text-starMist transition hover:bg-white/12 disabled:opacity-45"
                    >
                      忽略
                    </button>
                  </div>
                ) : null}
              </div>
            );
          })
        )}
      </div>
    </StarPanel>
  );
}

function AuditTimeline({
  logs,
  history,
  busyId,
  onClearHistory
}: {
  logs: AuditLogRead[];
  history: MemoryHistoryResponse | null;
  busyId: string | null;
  onClearHistory: () => void;
}) {
  const items = history?.events ?? logs;
  return (
    <StarPanel className="p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-full bg-white/10 text-starGold">
            {history ? (
              <History className="h-5 w-5" aria-hidden="true" />
            ) : (
              <Clock3 className="h-5 w-5" aria-hidden="true" />
            )}
          </span>
          <div>
            <h2 className="font-serif text-xl font-bold text-starGold">
              {history ? "记忆历史" : "最近事件"}
            </h2>
            <p className="text-xs font-semibold text-starMist/58">
              {history ? `memory_id: ${history.memory_id}` : "展示最近审计写入。"}
            </p>
          </div>
        </div>
        {history ? (
          <button
            type="button"
            onClick={onClearHistory}
            className="rounded-lg border border-white/10 px-3 py-2 text-xs font-bold text-starMist/72 transition hover:text-starGold"
          >
            返回最近事件
          </button>
        ) : null}
      </div>

      <div className="mt-4 divide-y divide-white/8">
        {busyId?.startsWith("history:") ? (
          <p className="py-4 text-sm font-semibold text-starMist/58">正在读取历史...</p>
        ) : null}
        {items.length === 0 ? (
          <p className="py-4 text-sm font-semibold text-starMist/58">暂无审计事件。</p>
        ) : (
          items.slice(0, 8).map((log) => (
            <div key={log.id} className="grid gap-1 py-3 sm:grid-cols-[10rem_1fr_auto] sm:items-center">
              <span className="text-xs font-semibold text-starMist/56">
                {formatAuditTime(log.created_at)}
              </span>
              <span className="text-sm font-black text-starCream">
                {auditEventLabel(log.event_type)}
              </span>
              <span className="text-xs font-bold text-starGold">
                {auditSeverityLabel(log.severity)}
              </span>
              {log.action ? (
                <span className="text-xs font-semibold leading-5 text-starMist/58 sm:col-span-3">
                  {log.action}
                </span>
              ) : null}
            </div>
          ))
        )}
      </div>
    </StarPanel>
  );
}

function MemoryDimensionCard({
  busyKey,
  title,
  icon: Icon,
  color,
  memories,
  fallback,
  busyId,
  onConfirm,
  onDelete,
  onUpdate
}: {
  busyKey: string;
  title: string;
  icon: typeof Flower2;
  color: string;
  memories: MemoryRead[];
  fallback: string[];
  busyId: string | null;
  onConfirm: (ids: string[]) => void;
  onDelete: (ids: string[]) => void;
  onUpdate: (memory: MemoryRead, content: string) => void;
}) {
  const first = memories[0];
  const items = memories.length > 0 ? memories.map((memory) => memory.content) : fallback;
  const isBusy = busyId === busyKey;
  const confirmTargets = selectDimensionActionTargets(memories, "confirm");
  const deleteTargets = selectDimensionActionTargets(memories, "delete");
  const [isEditing, setIsEditing] = useState(false);
  const [draftItems, setDraftItems] = useState(items.join("\n"));

  useEffect(() => {
    if (!isEditing) {
      setDraftItems(items.join("\n"));
    }
  }, [isEditing, items]);

  function handleConfirm() {
    if (!first) {
      return;
    }
    if (isEditing) {
      const nextContent = normalizeItems(draftItems).join("\n");
      onUpdate(first, nextContent || first.content);
      setIsEditing(false);
      return;
    }
    onConfirm(confirmTargets);
  }

  return (
    <DimensionShell title={title} icon={Icon} color={color}>
      {isEditing && first ? (
        <textarea
          value={draftItems}
          onChange={(event) => setDraftItems(event.target.value)}
          className="star-input mt-4 min-h-[5.2rem] resize-none text-sm"
        />
      ) : (
        <DimensionItems items={items} />
      )}

      <DimensionActions
        editDisabled={!first || isBusy}
        deleteDisabled={deleteTargets.length === 0 || isBusy}
        confirmDisabled={(isEditing ? !first : confirmTargets.length === 0) || isBusy}
        onEdit={() => first && setIsEditing(true)}
        onDelete={() => onDelete(deleteTargets)}
        onConfirm={handleConfirm}
      />
    </DimensionShell>
  );
}

function CustomDimensionCard({
  dimension,
  onUpdate,
  onDelete,
  onConfirm
}: {
  dimension: CustomDimension;
  onUpdate: (id: string, title: string, items: string[]) => void;
  onDelete: (id: string) => void;
  onConfirm: (id: string) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [draftTitle, setDraftTitle] = useState(dimension.title);
  const [draftItems, setDraftItems] = useState(dimension.items.join("\n"));

  useEffect(() => {
    if (!isEditing) {
      setDraftTitle(dimension.title);
      setDraftItems(dimension.items.join("\n"));
    }
  }, [dimension.items, dimension.title, isEditing]);

  function handleConfirm() {
    if (isEditing) {
      const title = draftTitle.trim() || dimension.title;
      const items = normalizeItems(draftItems);
      onUpdate(dimension.id, title, items.length > 0 ? items : dimension.items);
      setIsEditing(false);
      return;
    }
    onConfirm(dimension.id);
  }

  return (
    <DimensionShell
      title={dimension.title}
      icon={MessageSquareText}
      color={dimension.confirmed ? "text-emerald-200" : "text-starGold"}
    >
      {isEditing ? (
        <div className="mt-4 grid gap-3">
          <input
            value={draftTitle}
            onChange={(event) => setDraftTitle(event.target.value)}
            className="star-input text-sm"
            placeholder="维度名称"
          />
          <textarea
            value={draftItems}
            onChange={(event) => setDraftItems(event.target.value)}
            className="star-input min-h-[5.2rem] resize-none text-sm"
            placeholder="每行一条记忆"
          />
        </div>
      ) : (
        <DimensionItems items={dimension.items} />
      )}

      <DimensionActions
        editDisabled={false}
        deleteDisabled={false}
        confirmDisabled={false}
        onEdit={() => setIsEditing(true)}
        onDelete={() => onDelete(dimension.id)}
        onConfirm={handleConfirm}
      />
    </DimensionShell>
  );
}

function CustomDimensionEditor({
  onCreate,
  onCancel
}: {
  onCreate: (title: string, items: string[]) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState("");
  const [items, setItems] = useState("");

  function handleConfirm() {
    const normalizedTitle = title.trim();
    const normalizedItems = normalizeItems(items);
    if (!normalizedTitle || normalizedItems.length === 0) {
      return;
    }
    onCreate(normalizedTitle, normalizedItems);
  }

  return (
    <DimensionShell title="新增维度" icon={Plus} color="text-starGold">
      <div className="mt-4 grid gap-3">
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="star-input text-sm"
          placeholder="例如：重要纪念日"
        />
        <textarea
          value={items}
          onChange={(event) => setItems(event.target.value)}
          className="star-input min-h-[5.2rem] resize-none text-sm"
          placeholder="每行一条记忆"
        />
      </div>
      <DimensionActions
        editDisabled={false}
        deleteDisabled={false}
        confirmDisabled={!title.trim() || normalizeItems(items).length === 0}
        editLabel="编辑"
        onEdit={onCancel}
        onDelete={onCancel}
        onConfirm={handleConfirm}
      />
    </DimensionShell>
  );
}

function DimensionShell({
  title,
  icon: Icon,
  color,
  children
}: {
  title: string;
  icon: typeof Flower2;
  color: string;
  children: ReactNode;
}) {
  return (
    <StarPanel className="flex min-h-[9.4rem] flex-col p-4">
      <div className="flex items-center gap-3">
        <span className={`grid h-9 w-9 place-items-center rounded-full bg-white/10 ${color}`}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <h2 className="font-serif text-xl font-bold text-starGold">{title}</h2>
      </div>
      {children}
    </StarPanel>
  );
}

function DimensionItems({ items }: { items: string[] }) {
  return (
    <ul className="mt-4 min-h-[4.2rem] flex-1 space-y-2 text-sm font-semibold leading-6 text-starMist/78">
      {items.slice(0, 3).map((item, index) => (
        <li key={`${item}-${index}`} className="flex gap-2">
          <span className="text-starGold">•</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function DimensionActions({
  editDisabled,
  deleteDisabled,
  confirmDisabled,
  editLabel = "编辑",
  onEdit,
  onDelete,
  onConfirm
}: {
  editDisabled: boolean;
  deleteDisabled: boolean;
  confirmDisabled: boolean;
  editLabel?: string;
  onEdit: () => void;
  onDelete: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="mt-4 grid grid-cols-3 gap-2">
      <ActionButton tone="edit" disabled={editDisabled} onClick={onEdit}>
        {editLabel}
      </ActionButton>
      <ActionButton tone="delete" disabled={deleteDisabled} onClick={onDelete}>
        删除
      </ActionButton>
      <ActionButton tone="confirm" disabled={confirmDisabled} onClick={onConfirm}>
        确认
      </ActionButton>
    </div>
  );
}

function ActionButton({
  children,
  disabled,
  tone,
  onClick
}: {
  children: string;
  disabled: boolean;
  tone: "edit" | "delete" | "confirm";
  onClick: () => void;
}) {
  const toneClass = {
    edit: "bg-amber-300/18 text-amber-100 hover:bg-amber-300/28",
    delete: "bg-rose-400/18 text-rose-100 hover:bg-rose-400/28",
    confirm: "bg-emerald-300/20 text-emerald-100 hover:bg-emerald-300/28"
  }[tone];

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`rounded-lg px-3 py-2 text-sm font-bold transition disabled:cursor-not-allowed disabled:opacity-35 ${toneClass}`}
    >
      {children}
    </button>
  );
}

function Notice({ text }: { text: string }) {
  return <StarPanel className="mx-auto mt-8 max-w-3xl p-5 text-center text-starMist/72">{text}</StarPanel>;
}

function Alert({ tone, text }: { tone: "error" | "success"; text: string }) {
  return (
    <div
      className={`rounded-2xl border p-4 text-center text-sm font-semibold ${
        tone === "error"
          ? "border-rose-300/20 bg-rose-500/15 text-rose-100"
          : "border-emerald-200/20 bg-emerald-400/12 text-emerald-100"
      }`}
    >
      {text}
    </div>
  );
}

function calculateTrust(memories: MemoryRead[]) {
  if (memories.length === 0) {
    return 78;
  }
  const total = memories.reduce((sum, memory) => sum + memory.confidence_score, 0);
  return Math.max(1, Math.round(total / memories.length));
}

function formatAuditTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function sourceCoverageText(coverage: Record<string, number>) {
  const entries = Object.entries(coverage).filter(([, count]) => count > 0);
  if (entries.length === 0) {
    return "暂无来源";
  }
  return entries
    .map(([sourceType, count]) => `${sourceTypeLabel(sourceType)} ${count}`)
    .join(" / ");
}

function sourceTypeLabel(value: string) {
  return (
    {
      manual: "手动",
      text: "文本",
      image: "图片",
      audio: "音频",
      video: "视频",
      unknown: "未知"
    }[value] ?? value
  );
}

function sampleItems(category: string) {
  const samples: Record<string, string[]> = {
    basic_fact: ["1900年5月12日出生", "男性", "曾在上海生活"],
    relationship: ["我的哥哥，像朋友一样支持我", "很疼爱家人，责任心很强"],
    preference: ["喜欢音乐，尤其是民谣", "热爱旅行，喜欢自然风景", "喜欢摄影，记录生活"],
    habit: ["作息规律，早睡早起", "喜欢喝温水，不爱喝冷饮", "房间总是整理得很整洁"],
    expression_style: ["说话温和，很少大声说话", "喜欢用行动表达关心", "常说“没事，别担心”"],
    shared_event: ["2018年一起去云南旅行", "一起看过很多场日出", "每次见面都聊很久很久"]
  };
  return samples[category] ?? ["暂无提取内容"];
}

function normalizeItems(value: string) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function storageKey(personaId: string) {
  return `star_custom_memory_dimensions:${personaId}`;
}

function readCustomDimensions(personaId: string): CustomDimension[] {
  if (typeof window === "undefined") {
    return [];
  }

  const rawValue = window.localStorage.getItem(storageKey(personaId));
  if (!rawValue) {
    return [];
  }

  try {
    const parsed = JSON.parse(rawValue);
    return Array.isArray(parsed) ? parsed.filter(isCustomDimension) : [];
  } catch {
    return [];
  }
}

function writeCustomDimensions(personaId: string, dimensions: CustomDimension[]) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(storageKey(personaId), JSON.stringify(dimensions));
}

function isCustomDimension(value: unknown): value is CustomDimension {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Partial<CustomDimension>;
  return (
    typeof record.id === "string" &&
    typeof record.title === "string" &&
    Array.isArray(record.items) &&
    record.items.every((item) => typeof item === "string") &&
    typeof record.confirmed === "boolean"
  );
}
