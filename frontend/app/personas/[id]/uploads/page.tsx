"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { DemoEntry } from "@/src/components/DemoEntry";
import {
  GlassPanel,
  MemoryContainer,
  MemoryShell,
  MemoryTitle,
  StepRibbon
} from "@/src/components/MemorySpace";
import { getAuthToken } from "@/src/lib/auth";
import { jobStatusLabel } from "@/src/lib/jobs";
import {
  createManualMaterial,
  listMaterials,
  MATERIAL_IMPORTANCE_OPTIONS,
  materialImportanceLabel,
  materialTypeLabel,
  MaterialImportance,
  SourceMaterialRead,
  uploadMaterials
} from "@/src/lib/materials";
import { ROUTES } from "@/src/lib/routes";

type PageState = "checking" | "signedOut" | "loading" | "ready" | "error";

const ACCEPTED_UPLOAD_TYPES = [
  ".txt",
  ".md",
  ".pdf",
  ".doc",
  ".docx",
  "text/plain",
  "image/*",
  "audio/*",
  "video/*"
].join(",");

export default function PersonaUploadsPage() {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<PageState>("checking");
  const [materials, setMaterials] = useState<SourceMaterialRead[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [fileDescription, setFileDescription] = useState("");
  const [fileImportance, setFileImportance] = useState<MaterialImportance>("normal");
  const [manualText, setManualText] = useState("");
  const [manualDescription, setManualDescription] = useState("");
  const [manualImportance, setManualImportance] = useState<MaterialImportance>("important");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fileInputKey, setFileInputKey] = useState(0);

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

    listMaterials(personaId)
      .then((items) => {
        if (!isCurrent) {
          return;
        }
        setMaterials(items);
        setState("ready");
      })
      .catch((caught) => {
        if (!isCurrent) {
          return;
        }
        setError(caught instanceof Error ? caught.message : "无法加载资料。");
        setState("error");
      });

    return () => {
      isCurrent = false;
    };
  }, [personaId]);

  async function refreshMaterials() {
    if (!personaId) {
      return;
    }
    setMaterials(await listMaterials(personaId));
  }

  function updateSelectedFiles(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFiles(event.target.files ? Array.from(event.target.files) : []);
  }

  async function handleFileUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);

    if (!personaId || selectedFiles.length === 0) {
      setError("请至少选择一个文本、图片、音频或视频文件。");
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await uploadMaterials(personaId, {
        files: selectedFiles,
        importance: fileImportance,
        user_description: fileDescription
      });
      await refreshMaterials();
      setSelectedFiles([]);
      setFileDescription("");
      setFileImportance("normal");
      setFileInputKey((current) => current + 1);
      setNotice(`已加入 ${created.length} 条资料，并创建 mock 解析任务。`);
    } catch (caught) {
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
    try {
      await createManualMaterial(personaId, {
        manual_text: manualText,
        importance: manualImportance,
        user_description: manualDescription
      });
      await refreshMaterials();
      setManualText("");
      setManualDescription("");
      setManualImportance("important");
      setNotice("已创建手动资料，并进入 mock 解析链路。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法创建手动资料。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <MemoryShell background="familyAlbum">
      <MemoryContainer>
      <div className="flex flex-wrap items-center gap-3 text-sm font-semibold text-memoryAccent">
        <Link href={personaId ? ROUTES.personaDetail(personaId) : ROUTES.dashboard}>
          返回记忆空间
        </Link>
        {personaId ? <Link href={ROUTES.personaJobs(personaId)}>查看任务</Link> : null}
      </div>

      <div className="mt-6 grid gap-5">
        <MemoryTitle
          title="补充可追溯资料"
          subtitle="上传文件或手动记录故事、习惯和称呼。资料会进入本地 mock 解析链路，供后续记忆确认使用。"
        />
        <StepRibbon activeIndex={1} />
      </div>

      {state === "signedOut" ? <SignedOutState /> : null}
      {state === "loading" || state === "checking" ? <Notice text="正在加载资料..." /> : null}
      {state === "error" ? <Notice text={error ?? "无法加载资料。"} /> : null}

      {state === "ready" ? (
        <div className="mt-8 grid gap-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <form
              className="memory-glass rounded-[2rem] border border-white/70 p-5 shadow-memory"
              onSubmit={handleFileUpload}
            >
              <h2 className="font-serif text-2xl font-semibold text-memoryText">文件资料</h2>
              <p className="mt-2 text-sm leading-7 text-memoryText/70">
                可以先放入照片、录音、视频或文字文件。系统会保存资料记录，并创建本地 mock 解析任务。
              </p>
              <label className="mt-5 grid gap-2 text-sm font-semibold text-memoryText">
                选择文件
                <input
                  key={fileInputKey}
                  type="file"
                  multiple
                  accept={ACCEPTED_UPLOAD_TYPES}
                  onChange={updateSelectedFiles}
                  className={inputClass}
                />
              </label>
              {selectedFiles.length > 0 ? (
                <ul className="mt-3 grid gap-1 text-sm text-memoryText/70">
                  {selectedFiles.map((file) => (
                    <li key={`${file.name}-${file.size}`}>{file.name}</li>
                  ))}
                </ul>
              ) : null}
              <MetadataFields
                description={fileDescription}
                importance={fileImportance}
                onDescriptionChange={setFileDescription}
                onImportanceChange={setFileImportance}
              />
              <button type="submit" disabled={isSubmitting} className={buttonClass}>
                {isSubmitting ? "正在加入..." : "加入资料"}
              </button>
            </form>

            <form
              className="memory-glass rounded-[2rem] border border-white/70 p-5 shadow-memory"
              onSubmit={handleManualCreate}
            >
              <h2 className="font-serif text-2xl font-semibold text-memoryText">手动资料</h2>
              <p className="mt-2 text-sm leading-7 text-memoryText/70">
                直接写下一段记忆、口头禅、共同经历或背景说明。演示数据也使用这个入口生成。
              </p>
              <label className="mt-5 grid gap-2 text-sm font-semibold text-memoryText">
                资料内容
                <textarea
                  value={manualText}
                  onChange={(event) => setManualText(event.target.value)}
                  className={`${inputClass} min-h-40 resize-y`}
                  placeholder="外婆喜欢给小铭包馄饨，也常说饭要趁热慢慢吃。"
                />
              </label>
              <MetadataFields
                description={manualDescription}
                importance={manualImportance}
                onDescriptionChange={setManualDescription}
                onImportanceChange={setManualImportance}
              />
              <button type="submit" disabled={isSubmitting} className={buttonClass}>
                {isSubmitting ? "正在创建..." : "保存手动资料"}
              </button>
            </form>
          </div>

          {error ? <Alert tone="error" text={error} /> : null}
          {notice ? <Alert tone="success" text={notice} /> : null}

          <GlassPanel>
            <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="font-serif text-2xl font-semibold text-memoryText">已有资料</h2>
                <p className="mt-2 text-sm leading-7 text-memoryText/70">
                  资料状态来自当前解析任务，后续审核记忆会从这些资料中生成。
                </p>
              </div>
              <span className="text-sm font-semibold text-memoryText/60">
                {materials.length} 条
              </span>
            </div>
            {materials.length === 0 ? (
              <p className="mt-6 rounded-2xl bg-memoryPaper/75 p-4 text-sm text-memoryText/70">
                还没有资料。先上传文件或写一段手动资料。
              </p>
            ) : (
              <div className="mt-6 grid gap-3">
                {materials.map((material) => (
                  <MaterialCard key={material.id} material={material} />
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
        资料属于具体人物。可以免注册体验外婆示例，或登录已有账号。
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

function MetadataFields({
  description,
  importance,
  onDescriptionChange,
  onImportanceChange
}: {
  description: string;
  importance: MaterialImportance;
  onDescriptionChange: (value: string) => void;
  onImportanceChange: (value: MaterialImportance) => void;
}) {
  return (
    <div className="mt-4 grid gap-4">
      <label className="grid gap-2 text-sm font-semibold text-memoryText">
        备注
        <input
          value={description}
          onChange={(event) => onDescriptionChange(event.target.value)}
          className={inputClass}
          placeholder="这条资料为什么重要，或它记录了什么。"
        />
      </label>
      <label className="grid gap-2 text-sm font-semibold text-memoryText">
        重要程度
        <select
          value={importance}
          onChange={(event) => onImportanceChange(event.target.value as MaterialImportance)}
          className={inputClass}
        >
          {MATERIAL_IMPORTANCE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

function MaterialCard({ material }: { material: SourceMaterialRead }) {
  const title = material.file_name || "手动资料";
  const detail = material.manual_text || material.user_description || "暂无说明。";

  return (
    <article className="rounded-2xl border border-memoryLine/55 bg-memoryPaper/70 p-4 shadow-soft">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-semibold text-memoryText">{title}</p>
          <p className="mt-1 text-xs font-semibold tracking-[0.08em] text-memoryAccent">
            {materialTypeLabel(material.file_type)} · {materialImportanceLabel(material.importance)}
          </p>
        </div>
        <span className="rounded-full bg-white/80 px-3 py-1 text-xs font-semibold text-memoryAccent">
          {jobStatusLabel(material.parse_status)}
        </span>
      </div>
      <p className="mt-3 line-clamp-3 text-sm leading-6 text-memoryText/70">{detail}</p>
      <dl className="mt-4 grid gap-2 text-xs text-memoryText/60 md:grid-cols-3">
        <Stat label="任务" value={String(material.jobs.length)} />
        <Stat label="大小" value={formatFileSize(material.file_size)} />
        <Stat label="创建时间" value={formatDate(material.created_at)} />
      </dl>
    </article>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-medium">{label}</dt>
      <dd className="mt-1 text-memoryText">{value}</dd>
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

const inputClass =
  "rounded-2xl border border-memoryLine/80 bg-white/74 px-4 py-3 text-sm text-memoryText outline-none transition focus:border-memoryAccent focus:ring-4 focus:ring-memoryAccent/20";

const buttonClass =
  "memory-button mt-5 rounded-2xl bg-memoryAccent px-5 py-3 text-sm font-semibold text-white shadow-warm transition hover:bg-memoryAccentDark focus:outline-none focus:ring-4 focus:ring-memoryAccent/25 disabled:cursor-not-allowed disabled:bg-memoryText/30";
