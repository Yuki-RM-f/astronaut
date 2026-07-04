"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileText,
  Flower2,
  Heart,
  ImageIcon,
  MessageSquareText,
  Mic,
  Pencil,
  Plus,
  ShieldCheck,
  Sparkles,
  Star,
  Trash2,
  Users,
  Utensils,
  Video
} from "lucide-react";
import {
  PageTitle,
  StarNav,
  StarPanel,
  StarShell,
  TwinkleLabel
} from "@/src/components/StarSite";
import { PersonaBackLink } from "@/src/components/PersonaBackLink";
import { UploadMemoryTile } from "@/src/components/UploadMemoryTile";
import { ensureDemoSession } from "@/src/lib/auth";
import { jobStatusLabel } from "@/src/lib/jobs";
import {
  confirmMemory,
  deleteMemory,
  listMemories,
  memoryStatusLabel,
  MemoryCategory,
  MemoryRead,
  updateMemory
} from "@/src/lib/memories";
import {
  createManualMaterial,
  describeSelectedUploadFiles,
  listMaterials,
  materialTypeLabel,
  SourceMaterialRead,
  uploadMaterials
} from "@/src/lib/materials";
import {
  getPersonaProfile,
  PersonaProfileRead,
  trustLevelForScore,
  trustLevelLabel
} from "@/src/lib/profile";
import { ROUTES } from "@/src/lib/routes";

type PageState = "loading" | "ready" | "error";
type UploadKind = "照片" | "视频" | "声音" | "文字";
type SubmitProgressKind = "file" | "manual";
type SubmitProgressStage =
  | "uploading_files"
  | "saving_manual"
  | "parsing"
  | "generating_document"
  | "refreshing"
  | "complete";

type SubmitProgress = {
  kind: SubmitProgressKind;
  stage: SubmitProgressStage;
};

type CustomDimension = {
  id: string;
  title: string;
  items: string[];
  confirmed: boolean;
};

const COMPLETE_REVIEW_BUSY_ID = "__complete_review__";
const MATERIAL_PREVIEW_COUNT = 2;

const CATEGORY_VIEW: Array<{
  key: MemoryCategory;
  title: string;
  icon: LucideIcon;
  color: string;
}> = [
  { key: "basic_fact", title: "基础信息", icon: Flower2, color: "text-rose-200" },
  { key: "relationship", title: "人物关系", icon: Users, color: "text-amber-200" },
  { key: "preference", title: "兴趣偏好", icon: Heart, color: "text-pink-200" },
  { key: "habit", title: "生活习惯", icon: Utensils, color: "text-violet-200" },
  { key: "expression_style", title: "表达习惯", icon: MessageSquareText, color: "text-rose-200" },
  { key: "shared_event", title: "共同经历", icon: MessageSquareText, color: "text-amber-100" }
];

const REVIEW_DONE_STATUSES = ["confirmed", "corrected", "rejected", "disabled"];
const BACKGROUND_PARSE_TERMINAL_STATUSES = ["succeeded", "failed", "canceled"];

const SUBMIT_PROGRESS_VIEW: Record<SubmitProgressStage, { label: string; value: number }> = {
  uploading_files: { label: "正在上传资料...", value: 18 },
  saving_manual: { label: "正在保存手动资料...", value: 18 },
  parsing: { label: "正在解析资料并抽取记忆...", value: 48 },
  generating_document: { label: "正在生成结构化记忆文档...", value: 72 },
  refreshing: { label: "正在刷新审核结果...", value: 88 },
  complete: { label: "资料已加入，解析结果已更新。", value: 100 }
};

function emptyUploads(): Record<UploadKind, File[]> {
  return {
    照片: [],
    视频: [],
    声音: [],
    文字: []
  };
}

export default function PersonaUploadsPage() {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<PageState>("loading");
  const [materials, setMaterials] = useState<SourceMaterialRead[]>([]);
  const [memories, setMemories] = useState<MemoryRead[]>([]);
  const [profile, setProfile] = useState<PersonaProfileRead | null>(null);
  const [customDimensions, setCustomDimensions] = useState<CustomDimension[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [uploads, setUploads] = useState<Record<UploadKind, File[]>>(emptyUploads);
  const [manualText, setManualText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [isAddingDimension, setIsAddingDimension] = useState(false);
  const [isMaterialsExpanded, setIsMaterialsExpanded] = useState(false);
  const [uploadTileKey, setUploadTileKey] = useState(0);
  const [submitProgress, setSubmitProgress] = useState<SubmitProgress | null>(null);
  const submitProgressTimers = useRef<Array<ReturnType<typeof setTimeout>>>([]);

  const structuredMemoryMd = useMemo(
    () => renderStructuredMemoryMd(memories, materials),
    [memories, materials]
  );
  const selectedUploadFiles = useMemo(() => describeSelectedUploadFiles(uploads), [uploads]);
  const hasMaterialOverflow = materials.length > MATERIAL_PREVIEW_COUNT;
  const visibleMaterials = useMemo(
    () =>
      hasMaterialOverflow && !isMaterialsExpanded
        ? materials.slice(0, MATERIAL_PREVIEW_COUNT)
        : materials,
    [hasMaterialOverflow, isMaterialsExpanded, materials]
  );

  useEffect(() => {
    if (!personaId) {
      setError("缺少人物 ID。");
      setState("error");
      return;
    }

    setCustomDimensions(readCustomDimensions(personaId));

    let isCurrent = true;
    setState("loading");
    setError(null);

    ensureDemoSession()
      .then(() => loadPageData(personaId))
      .then((data) => {
        if (!isCurrent) {
          return;
        }
        setMaterials(data.materials);
        setMemories(data.memories);
        applyProfile(data.profile);
        setState("ready");
      })
      .catch((caught) => {
        if (!isCurrent) {
          return;
        }
        setError(caught instanceof Error ? caught.message : "无法加载资料审核页。");
        setState("error");
      });

    return () => {
      isCurrent = false;
    };
  }, [personaId]);

  useEffect(
    () => () => {
      submitProgressTimers.current.forEach((timer) => clearTimeout(timer));
      submitProgressTimers.current = [];
    },
    []
  );

  async function refreshPageData() {
    if (!personaId) {
      return;
    }
    const data = await loadPageData(personaId);
    setMaterials(data.materials);
    setMemories(data.memories);
    applyProfile(data.profile);
  }

  function applyProfile(nextProfile: PersonaProfileRead) {
    setProfile(nextProfile);
  }

  function clearSubmitProgressTimers() {
    submitProgressTimers.current.forEach((timer) => clearTimeout(timer));
    submitProgressTimers.current = [];
  }

  function startSubmitProgress(kind: SubmitProgressKind) {
    clearSubmitProgressTimers();
    setSubmitProgress({
      kind,
      stage: kind === "file" ? "uploading_files" : "saving_manual"
    });
  }

  function moveSubmitProgress(kind: SubmitProgressKind, stage: SubmitProgressStage) {
    clearSubmitProgressTimers();
    setSubmitProgress({ kind, stage });
  }

  function finishSubmitProgress(kind: SubmitProgressKind) {
    moveSubmitProgress(kind, "complete");
    submitProgressTimers.current = [
      setTimeout(() => setSubmitProgress(null), 1200)
    ];
  }

  function stopSubmitProgress() {
    clearSubmitProgressTimers();
    setSubmitProgress(null);
  }

  async function pollMaterialJobs(jobIds: string[], kind: SubmitProgressKind) {
    if (!personaId || jobIds.length === 0) {
      await refreshPageData();
      finishSubmitProgress(kind);
      return;
    }

    const trackedJobIds = new Set(jobIds);
    const deadline = Date.now() + 120000;
    while (Date.now() < deadline) {
      const data = await loadPageData(personaId);
      setMaterials(data.materials);
      setMemories(data.memories);
      applyProfile(data.profile);

      const trackedJobs = data.materials
        .flatMap((material) => material.jobs)
        .filter((job) => trackedJobIds.has(job.id));
      if (
        trackedJobs.length > 0 &&
        trackedJobs.every((job) => BACKGROUND_PARSE_TERMINAL_STATUSES.includes(job.status))
      ) {
        moveSubmitProgress(kind, "refreshing");
        setNotice(
          trackedJobs.every((job) => job.status === "succeeded")
            ? "资料解析完成，审核卡片和结构化记忆文档已更新。"
            : "资料已处理完成，部分资料解析失败，请查看已有资料中的失败原因。"
        );
        finishSubmitProgress(kind);
        return;
      }

      moveSubmitProgress(kind, "parsing");
      await wait(1600);
    }

    stopSubmitProgress();
    setNotice("资料已加入，后台解析中；如果稍后仍未更新，可以刷新页面查看。");
  }

  async function handleFileUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);

    const files = Object.values(uploads).flat();
    if (!personaId || files.length === 0) {
      setError("请至少选择一个文本、图片、音频或视频文件。");
      return;
    }

    setIsSubmitting(true);
    startSubmitProgress("file");
    try {
      const created = await uploadMaterials(personaId, {
        files
      });
      const jobIds = materialJobIds(created);
      moveSubmitProgress("file", "parsing");
      await refreshPageData();
      setUploads(emptyUploads());
      setUploadTileKey((current) => current + 1);
      setNotice(`资料已加入，后台解析中。共 ${created.length} 条资料。`);
      void pollMaterialJobs(jobIds, "file");
    } catch (caught) {
      stopSubmitProgress();
      setError(caught instanceof Error ? caught.message : "无法上传资料。");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleManualCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);

    if (!personaId || manualText.trim().length === 0) {
      setError("请先填写手动资料内容。");
      return;
    }

    setIsSubmitting(true);
    startSubmitProgress("manual");
    try {
      const created = await createManualMaterial(personaId, {
        manual_text: manualText
      });
      const jobIds = materialJobIds([created]);
      moveSubmitProgress("manual", "parsing");
      await refreshPageData();
      setManualText("");
      setNotice("资料已加入，后台解析中。");
      void pollMaterialJobs(jobIds, "manual");
    } catch (caught) {
      stopSubmitProgress();
      setError(caught instanceof Error ? caught.message : "无法创建手动资料。");
    } finally {
      setIsSubmitting(false);
    }
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
      await refreshPageData();
      setNotice(message);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "操作失败。");
    } finally {
      setBusyId(null);
    }
  }

  function toggleMemoryImportance(memory: MemoryRead) {
    void runMemoryAction(
      memory,
      () => updateMemory(memory.id, { is_important: !memory.is_important }),
      memory.is_important ? "已取消重要标记。" : "已标记为重要。"
    );
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
      await refreshPageData();
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
    saveCustomDimensions([
      ...customDimensions,
      {
        id: `custom-${Date.now()}`,
        title,
        items,
        confirmed: false
      }
    ]);
    setIsAddingDimension(false);
    setNotice("自定义记忆维度已添加。");
  }

  function handleUpdateCustomDimension(id: string, title: string, items: string[]) {
    saveCustomDimensions(
      customDimensions.map((dimension) =>
        dimension.id === id ? { ...dimension, title, items, confirmed: false } : dimension
      )
    );
    setNotice("自定义记忆维度已更新。");
  }

  function handleDeleteCustomDimension(id: string) {
    saveCustomDimensions(customDimensions.filter((dimension) => dimension.id !== id));
    setNotice("自定义记忆维度已删除。");
  }

  function handleConfirmCustomDimension(id: string) {
    saveCustomDimensions(
      customDimensions.map((dimension) =>
        dimension.id === id ? { ...dimension, confirmed: true } : dimension
      )
    );
    setNotice("自定义记忆维度已确认。");
  }

  async function handleCompleteReview() {
    setBusyId(COMPLETE_REVIEW_BUSY_ID);
    setError(null);
    setNotice(null);
    try {
      const pendingMemories = memories.filter(
        (memory) => !REVIEW_DONE_STATUSES.includes(memory.status)
      );
      await Promise.all(pendingMemories.map((memory) => confirmMemory(memory.id)));
      saveCustomDimensions(
        customDimensions.map((dimension) => ({ ...dimension, confirmed: true }))
      );
      await refreshPageData();
      setNotice("审核已完成，星星已点亮。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法完成审核。");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <StarShell>
      <StarNav />
      <main className="mx-auto w-full max-w-7xl px-5 pb-12 sm:px-8 lg:px-10">
        {!personaId ? (
          <Link href={ROUTES.dashboard} className="text-sm font-bold text-starGold">
            返回我的星空
          </Link>
        ) : null}
        {personaId ? <PersonaBackLink personaId={personaId} /> : null}

        <PageTitle
          className="mt-6"
          title="资料解析与审核"
          subtitle="上传资料、查看解析整理结果，并确认可进入长期记忆的卡片。"
        />

        {state === "loading" ? <Notice text="正在加载资料解析结果..." /> : null}
        {state === "error" ? <Notice text={error ?? "无法加载资料审核页。"} /> : null}

        {state === "ready" ? (
          <div className="mt-8 grid gap-6">
            <TrustReviewPanel
              profile={profile}
              memories={memories}
              busy={busyId === COMPLETE_REVIEW_BUSY_ID}
              onComplete={() => void handleCompleteReview()}
              onAddDimension={() => setIsAddingDimension(true)}
            />

            <div className="order-1 grid gap-6 lg:grid-cols-2">
              <StarPanel className="p-5">
                <form onSubmit={handleFileUpload}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h2 className="font-serif text-2xl font-bold text-starGold">上传珍贵回忆</h2>
                    <span className="text-sm font-semibold text-starMist/54">
                      <TwinkleLabel>越多回忆，星星越明亮</TwinkleLabel>
                    </span>
                  </div>
                  <div key={uploadTileKey} className="mt-7 grid gap-4 sm:grid-cols-2">
                    <UploadMemoryTile
                      kind="照片"
                      label="上传照片"
                      icon={ImageIcon}
                      count={uploads["照片"].length}
                      accept="image/*"
                      onPick={(files) => setUploads((current) => ({ ...current, 照片: files }))}
                    />
                    <UploadMemoryTile
                      kind="视频"
                      label="上传视频"
                      icon={Video}
                      count={uploads["视频"].length}
                      accept="video/*"
                      onPick={(files) => setUploads((current) => ({ ...current, 视频: files }))}
                    />
                    <UploadMemoryTile
                      kind="声音"
                      label="上传音频"
                      icon={Mic}
                      count={uploads["声音"].length}
                      accept="audio/*"
                      onPick={(files) => setUploads((current) => ({ ...current, 声音: files }))}
                    />
                    <UploadMemoryTile
                      kind="文字"
                      label="记录文字"
                      icon={FileText}
                      count={uploads["文字"].length}
                      accept=".txt,.md,.pdf,.doc,.docx,text/plain"
                      onPick={(files) => setUploads((current) => ({ ...current, 文字: files }))}
                    />
                  </div>
                  {selectedUploadFiles.length > 0 ? (
                    <div className="mt-5 rounded-2xl border border-starGold/14 bg-indigo-950/24 p-4">
                      <h3 className="text-sm font-bold text-starGold">已选择待上传的回忆</h3>
                      <ul className="mt-3 grid gap-2">
                        {selectedUploadFiles.map((file, index) => (
                          <li
                            key={`${file.kind}-${file.name}-${index}`}
                            className="grid gap-2 rounded-xl border border-white/8 bg-white/[0.04] px-3 py-3 text-sm sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center"
                          >
                            <span className="w-fit rounded-full border border-starGold/18 bg-starGold/10 px-3 py-1 text-xs font-bold text-starGold">
                              {file.kind}
                            </span>
                            <span className="min-w-0 break-all font-semibold text-starCream">
                              {file.name}
                            </span>
                            <span className="text-xs font-semibold text-starMist/54 sm:text-right">
                              {file.typeLabel} · {file.sizeLabel}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  <button type="submit" disabled={isSubmitting} className={buttonClass}>
                    {isSubmitting ? "正在加入..." : "加入资料"}
                  </button>
                  {submitProgress?.kind === "file" ? (
                    <SubmitProgressBar progress={submitProgress} />
                  ) : null}
                </form>
              </StarPanel>

              <StarPanel className="p-5">
                <form onSubmit={handleManualCreate}>
                  <h2 className="font-serif text-2xl font-bold text-starGold">手动资料</h2>
                  <p className="mt-2 text-sm font-semibold leading-7 text-starMist/70">
                    直接写下一段记忆、口头禅、共同经历或背景说明。
                  </p>
                  <label className="mt-5 grid gap-2 text-sm font-bold text-starMist/78">
                    资料内容
                    <textarea
                      value={manualText}
                      onChange={(event) => setManualText(event.target.value)}
                      className={`${inputClass} min-h-40 resize-y`}
                      placeholder="例如：外婆喜欢给小铭包馄饨，也常说饭要趁热慢慢吃。"
                    />
                  </label>
                  <button type="submit" disabled={isSubmitting} className={buttonClass}>
                    {isSubmitting ? "正在创建..." : "保存手动资料"}
                  </button>
                  {submitProgress?.kind === "manual" ? (
                    <SubmitProgressBar progress={submitProgress} />
                  ) : null}
                </form>
              </StarPanel>
            </div>

            {error ? <Alert tone="error" text={error} /> : null}
            {notice ? <Alert tone="success" text={notice} /> : null}

            {structuredMemoryMd ? (
              <StarPanel className="p-5">
                <div className="flex items-center gap-3">
                  <ShieldCheck className="h-5 w-5 text-starGold" aria-hidden="true" />
                  <h2 className="font-serif text-2xl font-bold text-starGold">
                    结构化记忆文档
                  </h2>
                </div>
                <pre className="mt-4 max-h-[24rem] overflow-auto whitespace-pre-wrap rounded-2xl border border-white/8 bg-black/18 p-4 text-sm leading-7 text-starMist/76">
                  {structuredMemoryMd}
                </pre>
              </StarPanel>
            ) : null}

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {CATEGORY_VIEW.map((category) => (
                <MemoryDimensionCard
                  key={category.key}
                  title={category.title}
                  icon={category.icon}
                  color={category.color}
                  memories={memories.filter((memory) => memory.category === category.key)}
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
                  onToggleImportant={toggleMemoryImportance}
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

              {isAddingDimension ? (
                <CustomDimensionEditor
                  onCreate={handleCreateCustomDimension}
                  onCancel={() => setIsAddingDimension(false)}
                />
              ) : null}
            </section>

            <StarPanel className="p-5">
              <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div>
                  <h2 className="font-serif text-2xl font-bold text-starGold">已有资料</h2>
                  <p className="mt-2 text-sm font-semibold leading-7 text-starMist/70">
                    资料状态来自当前解析任务，解析产物会进入上方审核卡片。
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-sm font-bold text-starMist/60">{materials.length} 条</span>
                  {hasMaterialOverflow ? (
                    <button
                      type="button"
                      aria-expanded={isMaterialsExpanded}
                      aria-controls="existing-materials-list"
                      onClick={() => setIsMaterialsExpanded((current) => !current)}
                      className="inline-flex items-center gap-2 rounded-full border border-starGold/30 bg-starGold/10 px-4 py-2 text-sm font-bold text-starGold transition hover:bg-starGold/18"
                    >
                      {isMaterialsExpanded ? (
                        <>
                          收起资料
                          <ChevronUp className="h-4 w-4" aria-hidden="true" />
                        </>
                      ) : (
                        <>
                          展开全部 {materials.length} 条
                          <ChevronDown className="h-4 w-4" aria-hidden="true" />
                        </>
                      )}
                    </button>
                  ) : null}
                </div>
              </div>
              {materials.length === 0 ? (
                <p className="mt-6 rounded-2xl border border-white/8 bg-white/6 p-4 text-sm font-semibold text-starMist/70">
                  还没有资料。先上传文件或写一段手动资料。
                </p>
              ) : (
                <div id="existing-materials-list" className="mt-6 grid gap-3">
                  {visibleMaterials.map((material) => (
                    <MaterialCard key={material.id} material={material} />
                  ))}
                </div>
              )}
            </StarPanel>
          </div>
        ) : null}
      </main>
    </StarShell>
  );
}

async function loadPageData(personaId: string) {
  const [materials, memories, profile] = await Promise.all([
    listMaterials(personaId),
    listMemories(personaId),
    getPersonaProfile(personaId)
  ]);
  return { materials, memories, profile };
}

function SubmitProgressBar({ progress }: { progress: SubmitProgress }) {
  const view = SUBMIT_PROGRESS_VIEW[progress.stage];
  return (
    <div className="mt-4" aria-live="polite">
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={view.value}
        aria-label={view.label}
        className="h-3 overflow-hidden rounded-full border border-starGold/18 bg-indigo-950/60"
      >
        <div
          className="h-full rounded-full bg-[linear-gradient(90deg,#f6d78b_0%,#f3a95f_100%)] transition-[width] duration-500"
          style={{ width: `${view.value}%` }}
        />
      </div>
      <p className="mt-2 text-center text-sm font-bold text-starMist/72">{view.label}</p>
    </div>
  );
}

function TrustReviewPanel({
  profile,
  memories,
  busy,
  onComplete,
  onAddDimension
}: {
  profile: PersonaProfileRead | null;
  memories: MemoryRead[];
  busy: boolean;
  onComplete: () => void;
  onAddDimension: () => void;
}) {
  const score = profile?.trust_score ?? 0;
  const level = profile?.trust_level ?? trustLevelForScore(score);
  const pendingCount = memories.filter(
    (memory) => !REVIEW_DONE_STATUSES.includes(memory.status)
  ).length;

  return (
    <StarPanel className="order-2 p-5">
      <div className="grid gap-5 lg:grid-cols-[0.7fr_1fr] lg:items-center">
        <div>
          <p className="inline-flex items-center gap-2 text-sm font-bold text-starGold">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            记忆可信度
          </p>
          <div className="mt-3 flex items-end gap-2 text-starGold">
            <span className="font-serif text-6xl font-bold leading-none">{score}</span>
            <span className="pb-1 text-2xl font-bold">%</span>
          </div>
          <p className="mt-2 text-sm font-bold text-starMist/70">{trustLevelLabel(level)}</p>
        </div>
        <div className="grid gap-4">
          <p className="text-sm font-semibold leading-7 text-starMist/74">
            这个数值只来自上传资料后的结构化记忆文档生成结果。审核卡片会刷新档案和长期记忆，但不会单独计算第二套可信度。
          </p>
          {profile?.suggestions.length ? (
            <ul className="grid gap-2 text-sm font-semibold text-starMist/70">
              {profile.suggestions.slice(0, 3).map((suggestion) => (
                <li key={suggestion} className="rounded-xl border border-white/8 bg-white/6 px-3 py-2">
                  {suggestion}
                </li>
              ))}
            </ul>
          ) : null}
          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              disabled={busy}
              onClick={onComplete}
              className="group inline-flex min-h-12 flex-1 items-center justify-center gap-3 rounded-full border border-starGold/45 bg-[linear-gradient(180deg,#ffd4a1_0%,#f3a95f_100%)] px-6 text-sm font-black text-violet-950 shadow-[0_0_24px_rgba(255,184,105,0.42)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? "正在点亮星星..." : "完成审核，点亮星星"}
              <Sparkles className="h-4 w-4 fill-current" aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={onAddDimension}
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full border border-starGold/24 bg-starGold/12 px-5 text-sm font-bold text-starCream transition hover:bg-starGold/18"
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              添加维度
            </button>
          </div>
          <p className="text-xs font-semibold text-starMist/50">
            当前还有 {pendingCount} 张卡片等待确认、修正、拒绝或删除。
          </p>
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
  busyId,
  onConfirm,
  onDelete,
  onUpdate,
  onToggleImportant
}: {
  title: string;
  icon: LucideIcon;
  color: string;
  memories: MemoryRead[];
  busyId: string | null;
  onConfirm: (ids: string[]) => void;
  onDelete: (ids: string[]) => void;
  onUpdate: (memory: MemoryRead, content: string) => void;
  onToggleImportant: (memory: MemoryRead) => void;
}) {
  const [editingMemoryId, setEditingMemoryId] = useState<string | null>(null);
  const [draftContent, setDraftContent] = useState("");

  useEffect(() => {
    if (!editingMemoryId) {
      setDraftContent("");
      return;
    }
    const editingMemory = memories.find((memory) => memory.id === editingMemoryId);
    if (editingMemory) {
      setDraftContent(editingMemory.content);
    } else {
      setEditingMemoryId(null);
    }
  }, [editingMemoryId, memories]);

  return (
    <StarPanel className="flex min-h-[14rem] flex-col p-4">
      <div className="flex items-center gap-3">
        <span className={`grid h-9 w-9 place-items-center rounded-full bg-white/10 ${color}`}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <h2 className="font-serif text-xl font-bold text-starGold">{title}</h2>
          <p className="text-xs font-semibold text-starMist/50">{memories.length} 张卡片</p>
        </div>
      </div>

      {memories.length === 0 ? (
        <p className="mt-4 flex-1 rounded-2xl border border-white/8 bg-white/6 p-4 text-sm font-semibold text-starMist/58">
          暂无该分类解析结果。
        </p>
      ) : (
        <div className="mt-4 grid flex-1 gap-3">
          {memories.map((memory) => (
              <article key={memory.id} className="rounded-2xl border border-white/8 bg-white/6 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <h3 className="text-sm font-black text-starCream">{memory.title}</h3>
                    <span className="rounded-full bg-starGold/12 px-2 py-0.5 text-xs font-bold text-starGold">
                      {memoryStatusLabel(memory.status)}
                    </span>
                  </div>
                  <button
                    type="button"
                    title={memory.is_important ? "取消重要标记" : "标记为重要"}
                    aria-label={memory.is_important ? "取消重要标记" : "标记为重要"}
                    disabled={busyId === memory.id}
                    onClick={() => onToggleImportant(memory)}
                    className="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-starGold/18 bg-indigo-950/28 text-starGold transition hover:bg-starGold/14 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Star
                      className={`h-4 w-4 ${memory.is_important ? "fill-current" : ""}`}
                      aria-hidden="true"
                    />
                  </button>
                </div>
                {editingMemoryId === memory.id ? (
                  <textarea
                    value={draftContent}
                    onChange={(event) => setDraftContent(event.target.value)}
                    className="star-input mt-3 min-h-[7rem] resize-y text-sm"
                  />
                ) : (
                  <p className="mt-2 line-clamp-3 text-sm font-semibold leading-6 text-starMist/72">
                    {memory.content}
                  </p>
                )}
                <p className="mt-2 text-xs font-semibold leading-5 text-starMist/48">
                  {memory.source_quote ?? memory.source_location ?? "暂无来源摘录"}
                </p>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  <IconButton
                    label="编辑"
                    icon={Pencil}
                    disabled={busyId === memory.id}
                    onClick={() => {
                      setEditingMemoryId(memory.id);
                    }}
                  />
                  <IconButton
                    label="删除"
                    icon={Trash2}
                    disabled={busyId === memory.id}
                    tone="danger"
                    onClick={() => onDelete([memory.id])}
                  />
                  <IconButton
                    label={editingMemoryId === memory.id ? "保存" : "确认"}
                    icon={CheckCircle2}
                    disabled={
                      busyId === memory.id ||
                      (editingMemoryId !== memory.id &&
                        REVIEW_DONE_STATUSES.includes(memory.status))
                    }
                    tone="success"
                    onClick={() => {
                      if (editingMemoryId === memory.id) {
                        const nextContent = draftContent.trim();
                        onUpdate(memory, nextContent || memory.content);
                        setEditingMemoryId(null);
                        return;
                      }
                      onConfirm([memory.id]);
                    }}
                  />
                </div>
              </article>
            ))}
        </div>
      )}
    </StarPanel>
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
    <StarPanel className="flex min-h-[14rem] flex-col p-4">
      <div className="flex items-center gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-full bg-white/10 text-starGold">
          <MessageSquareText className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <h2 className="font-serif text-xl font-bold text-starGold">{dimension.title}</h2>
          <p className="text-xs font-semibold text-starMist/50">
            {dimension.confirmed ? "已确认" : "自定义维度"}
          </p>
        </div>
      </div>

      {isEditing ? (
        <div className="mt-4 grid flex-1 gap-3">
          <input
            value={draftTitle}
            onChange={(event) => setDraftTitle(event.target.value)}
            className="star-input text-sm"
            placeholder="维度名称"
          />
          <textarea
            value={draftItems}
            onChange={(event) => setDraftItems(event.target.value)}
            className="star-input min-h-[7rem] resize-y text-sm"
            placeholder="每行一条记忆"
          />
        </div>
      ) : (
        <ul className="mt-4 flex-1 space-y-2 text-sm font-semibold leading-6 text-starMist/76">
          {dimension.items.slice(0, 4).map((item, index) => (
            <li key={`${item}-${index}`} className="flex gap-2">
              <span className="text-starGold">•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 grid grid-cols-3 gap-2">
        <IconButton label="编辑" icon={Pencil} disabled={false} onClick={() => setIsEditing(true)} />
        <IconButton label="删除" icon={Trash2} disabled={false} tone="danger" onClick={() => onDelete(dimension.id)} />
        <IconButton label="确认" icon={CheckCircle2} disabled={false} tone="success" onClick={handleConfirm} />
      </div>
    </StarPanel>
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

  function handleCreate() {
    const normalizedTitle = title.trim();
    const normalizedItems = normalizeItems(items);
    if (!normalizedTitle || normalizedItems.length === 0) {
      return;
    }
    onCreate(normalizedTitle, normalizedItems);
  }

  return (
    <StarPanel className="flex min-h-[14rem] flex-col p-4">
      <h2 className="font-serif text-xl font-bold text-starGold">新增维度</h2>
      <div className="mt-4 grid flex-1 gap-3">
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="star-input text-sm"
          placeholder="例如：重要纪念日"
        />
        <textarea
          value={items}
          onChange={(event) => setItems(event.target.value)}
          className="star-input min-h-[7rem] resize-y text-sm"
          placeholder="每行一条记忆"
        />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg bg-white/8 px-3 py-2 text-sm font-bold text-starMist transition hover:bg-white/12"
        >
          取消
        </button>
        <button
          type="button"
          disabled={!title.trim() || normalizeItems(items).length === 0}
          onClick={handleCreate}
          className="rounded-lg bg-emerald-300/20 px-3 py-2 text-sm font-bold text-emerald-100 transition hover:bg-emerald-300/28 disabled:cursor-not-allowed disabled:opacity-35"
        >
          添加
        </button>
      </div>
    </StarPanel>
  );
}

function IconButton({
  label,
  icon: Icon,
  disabled,
  tone = "default",
  onClick
}: {
  label: string;
  icon: LucideIcon;
  disabled: boolean;
  tone?: "default" | "danger" | "success";
  onClick: () => void;
}) {
  const toneClass = {
    default: "bg-amber-300/18 text-amber-100 hover:bg-amber-300/28",
    danger: "bg-rose-400/18 text-rose-100 hover:bg-rose-400/28",
    success: "bg-emerald-300/20 text-emerald-100 hover:bg-emerald-300/28"
  }[tone];

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-bold transition disabled:cursor-not-allowed disabled:opacity-35 ${toneClass}`}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
      {label}
    </button>
  );
}

function MaterialCard({ material }: { material: SourceMaterialRead }) {
  const title = material.file_name || "手动资料";
  const detail = material.manual_text || material.user_description || "暂无说明。";
  const jobError = materialJobError(material);
  const statusForUser = materialStatusForUser(material);

  return (
    <article className="rounded-2xl border border-white/8 bg-white/6 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-bold text-starCream">{title}</p>
          <p className="mt-1 text-xs font-bold tracking-[0.08em] text-starGold">
            {materialTypeLabel(material.file_type)}
          </p>
        </div>
        <span className="rounded-full bg-starGold/12 px-3 py-1 text-xs font-bold text-starGold">
          {jobStatusLabel(statusForUser)}
        </span>
      </div>
      <p className="mt-3 line-clamp-3 text-sm font-semibold leading-6 text-starMist/70">{detail}</p>
      {jobError ? (
        <p className="mt-3 rounded-xl border border-rose-300/20 bg-rose-500/12 px-3 py-2 text-xs font-bold leading-5 text-rose-100">
          失败原因：{jobError}
        </p>
      ) : null}
      <dl className="mt-4 grid gap-2 text-xs text-starMist/60 md:grid-cols-4">
        <Stat label="任务" value={String(material.jobs.length)} />
        <Stat label="大小" value={formatFileSize(material.file_size)} />
        <Stat label="分类" value={memoryCategorySummary(material)} />
        <Stat label="创建时间" value={formatDate(material.created_at)} />
      </dl>
    </article>
  );
}

function materialStatusForUser(
  material: SourceMaterialRead,
): SourceMaterialRead["parse_status"] {
  if (
    material.parse_status === "failed" &&
    material.jobs.some((job) => isMemoryDocumentProviderDiagnostic(job.error_message))
  ) {
    return "succeeded";
  }
  return material.parse_status;
}

function materialJobError(material: SourceMaterialRead): string | null {
  for (const job of material.jobs) {
    const message = job.error_message?.trim();
    if (!message || isMemoryDocumentProviderDiagnostic(message)) {
      continue;
    }
    return message;
  }
  return null;
}

function isMemoryDocumentProviderDiagnostic(message?: string | null): boolean {
  const normalized = message?.toLowerCase() ?? "";
  if (!normalized.includes("memory document")) {
    return false;
  }
  return (
    normalized.includes("strict json") ||
    normalized.includes("json object") ||
    normalized.includes("structured_memory_document_json")
  );
}

function Stat({ label, value }: { label: string; value: string }) {
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

function renderStructuredMemoryMd(
  memories: MemoryRead[],
  materials: SourceMaterialRead[],
): string | null {
  const activeMemories = memories.filter(
    (memory) => !["rejected", "disabled"].includes(memory.status)
  );
  if (activeMemories.length === 0) {
    return null;
  }

  const sourceLines = materials
    .filter((material) => material.parse_status === "succeeded")
    .map((material) => `- ${material.file_type}: ${materialLabel(material)}`);
  const sections = CATEGORY_VIEW.map((category) => {
    const lines = activeMemories
      .filter((memory) => memory.category === category.key)
      .map(memoryDocumentLine);
    return `## ${category.title}\n${lines.length > 0 ? lines.join("\n") : "- 暂无明确资料"}`;
  });
  const pendingLines = activeMemories
    .filter((memory) => !REVIEW_DONE_STATUSES.includes(memory.status))
    .map(memoryDocumentLine);

  return [
    `## 资料来源\n${sourceLines.length > 0 ? sourceLines.join("\n") : "- 暂无已完成解析资料"}`,
    ...sections,
    `## 待用户确认\n${pendingLines.length > 0 ? pendingLines.join("\n") : "- 暂无待确认记忆"}`
  ].join("\n\n");
}

function memoryDocumentLine(memory: MemoryRead): string {
  const importance = memory.is_important ? "[important] " : "";
  const content = memory.user_correction || memory.content;
  const source = memory.source_location ? `（来源：${memory.source_location}）` : "";
  return `- ${importance}[${memory.status}] ${memory.title}: ${content}${source}`;
}

function materialLabel(material: SourceMaterialRead): string {
  return (
    material.file_name ||
    material.manual_text?.trim().slice(0, 80) ||
    material.user_description ||
    material.id
  );
}

function materialJobIds(materials: SourceMaterialRead[]): string[] {
  return materials.flatMap((material) => material.jobs.map((job) => job.id));
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function memoryCategorySummary(material: SourceMaterialRead): string {
  const categories = new Set<string>();
  for (const job of material.jobs) {
    const output = job.output_json;
    if (!output || Array.isArray(output)) {
      continue;
    }
    const ids = output.memory_card_ids;
    if (Array.isArray(ids) && ids.length > 0) {
      categories.add("解析记忆");
    }
  }
  return categories.size > 0 ? [...categories].join("、") : materialTypeLabel(material.file_type);
}

function formatFileSize(size: number | null): string {
  if (size === null) {
    return "手动记录";
  }
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
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

const inputClass = "star-input text-sm";
const buttonClass = "star-button mt-5 min-w-32 disabled:opacity-60";
