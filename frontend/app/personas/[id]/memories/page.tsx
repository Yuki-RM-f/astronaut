"use client";

import { useParams, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  Flower2,
  Heart,
  MessageSquareText,
  Plus,
  Sparkles,
  Users,
  Utensils
} from "lucide-react";
import { DemoEntry } from "@/src/components/DemoEntry";
import { PageTitle, StarNav, StarPanel, StarShell } from "@/src/components/StarSite";
import { getAuthToken } from "@/src/lib/auth";
import {
  confirmMemory,
  deleteMemory,
  listMemories,
  MemoryRead,
  updateMemory
} from "@/src/lib/memories";
import { ROUTES } from "@/src/lib/routes";

type PageState = "checking" | "signedOut" | "loading" | "ready" | "error";

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

    setCustomDimensions(readCustomDimensions(personaId));

    let isCurrent = true;
    setState("loading");
    listMemories(personaId)
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
  }, [personaId]);

  async function refresh() {
    if (!personaId) {
      return;
    }
    setMemories(await listMemories(personaId));
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
          subtitle="AI已整理出TA的回忆要点，请确认并补充，让星星更加闪亮。"
        />

        {state === "signedOut" ? <SignedOut /> : null}
        {state === "loading" || state === "checking" ? <Notice text="正在读取记忆星图..." /> : null}
        {state === "error" ? <Notice text={error ?? "无法加载记忆。"} /> : null}

        {state === "ready" ? (
          <div className="mt-6 grid gap-4">
            <TrustBanner trust={trust} onRefresh={() => void refresh()} />

            {error ? <Alert tone="error" text={error} /> : null}
            {notice ? <Alert tone="success" text={notice} /> : null}

            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setIsAdding(true)}
                className="inline-flex items-center gap-2 rounded-xl border border-starGold/24 bg-starGold/12 px-4 py-2 text-sm font-bold text-starCream transition hover:bg-starGold/18"
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
                新增维度
              </button>
            </div>

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {CATEGORY_VIEW.map((category) => (
                <MemoryDimensionCard
                  key={category.key}
                  title={category.title}
                  icon={category.icon}
                  color={category.color}
                  memories={memories.filter((memory) => memory.category === category.key)}
                  fallback={sampleItems(category.key)}
                  busyId={busyId}
                  onConfirm={(memory) =>
                    runMemoryAction(memory, () => confirmMemory(memory.id), "记忆已确认。")
                  }
                  onDelete={(memory) =>
                    runMemoryAction(memory, () => deleteMemory(memory.id), "记忆已删除。")
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
          </div>
        ) : null}
      </main>
    </StarShell>
  );
}

function TrustBanner({ trust, onRefresh }: { trust: number; onRefresh: () => void }) {
  return (
    <StarPanel className="overflow-hidden p-0">
      <div className="grid min-h-[7.6rem] md:grid-cols-[0.48fr_0.52fr]">
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
          <button
            type="button"
            onClick={onRefresh}
            className="mt-3 rounded-lg border border-starGold/22 bg-starGold/10 px-7 py-2 text-sm font-bold text-starCream transition hover:bg-starGold/16"
          >
            重新解析
          </button>
        </div>
      </div>
    </StarPanel>
  );
}

function MemoryDimensionCard({
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
  title: string;
  icon: typeof Flower2;
  color: string;
  memories: MemoryRead[];
  fallback: string[];
  busyId: string | null;
  onConfirm: (memory: MemoryRead) => void;
  onDelete: (memory: MemoryRead) => void;
  onUpdate: (memory: MemoryRead, content: string) => void;
}) {
  const first = memories[0];
  const items = memories.length > 0 ? memories.map((memory) => memory.content) : fallback;
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
    onConfirm(first);
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
        disabled={!first || busyId === first.id}
        onEdit={() => first && setIsEditing(true)}
        onDelete={() => first && onDelete(first)}
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
        disabled={false}
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
        disabled={false}
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
  disabled,
  editLabel = "编辑",
  onEdit,
  onDelete,
  onConfirm
}: {
  disabled: boolean;
  editLabel?: string;
  onEdit: () => void;
  onDelete: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="mt-4 grid grid-cols-3 gap-2">
      <ActionButton tone="edit" disabled={disabled} onClick={onEdit}>
        {editLabel}
      </ActionButton>
      <ActionButton tone="delete" disabled={disabled} onClick={onDelete}>
        删除
      </ActionButton>
      <ActionButton tone="confirm" disabled={disabled} onClick={onConfirm}>
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

function SignedOut() {
  return (
    <StarPanel className="mx-auto mt-8 max-w-3xl p-6 text-center">
      <p className="text-sm leading-7 text-starMist/72">
        当前会以本地访客身份查看记忆审核，也可以进入演示星星。
      </p>
      <div className="mt-5 flex justify-center">
        <DemoEntry
          label="体验演示星星"
          className="star-button"
          errorClassName="mt-3 text-sm text-rose-200"
        />
      </div>
    </StarPanel>
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
