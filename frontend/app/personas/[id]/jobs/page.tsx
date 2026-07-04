"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
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
  AIJobRead,
  canCancelJob,
  canRetryJob,
  cancelJob,
  jobStatusLabel,
  listJobs,
  retryJob
} from "@/src/lib/jobs";
import { ROUTES } from "@/src/lib/routes";

type PageState = "checking" | "signedOut" | "loading" | "ready" | "error";

export default function PersonaJobsPage() {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<PageState>("checking");
  const [jobs, setJobs] = useState<AIJobRead[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyJobId, setBusyJobId] = useState<string | null>(null);

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

    listJobs(personaId)
      .then((items) => {
        if (!isCurrent) {
          return;
        }
        setJobs(items);
        setState("ready");
      })
      .catch((caught) => {
        if (!isCurrent) {
          return;
        }
        setError(caught instanceof Error ? caught.message : "无法加载任务。");
        setState("error");
      });

    return () => {
      isCurrent = false;
    };
  }, [personaId]);

  async function refreshJobs() {
    if (!personaId) {
      return;
    }
    setJobs(await listJobs(personaId));
  }

  async function handleRetry(job: AIJobRead) {
    setError(null);
    setNotice(null);
    setBusyJobId(job.id);
    try {
      const updated = await retryJob(job.id);
      await refreshJobs();
      setNotice(`${jobTypeLabel(updated.job_type)} 已重新排队。`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法重试任务。");
    } finally {
      setBusyJobId(null);
    }
  }

  async function handleCancel(job: AIJobRead) {
    setError(null);
    setNotice(null);
    setBusyJobId(job.id);
    try {
      const updated = await cancelJob(job.id);
      await refreshJobs();
      setNotice(`${jobTypeLabel(updated.job_type)} 已取消。`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法取消任务。");
    } finally {
      setBusyJobId(null);
    }
  }

  return (
    <MemoryShell background="familyAlbum">
      <MemoryContainer>
      <div className="flex flex-wrap items-center gap-3 text-sm font-semibold text-memoryAccent">
        <Link href={personaId ? ROUTES.personaDetail(personaId) : ROUTES.dashboard}>
          返回记忆空间
        </Link>
        {personaId ? <Link href={ROUTES.personaUploads(personaId)}>上传资料</Link> : null}
      </div>

      <div className="mt-6 grid gap-5">
        <MemoryTitle
          title="资料整理进度"
          subtitle="这里展示资料进入 mock 解析链路后的状态。真实模型解析、语音和数字人能力仍不在当前范围内。"
        />
        <StepRibbon activeIndex={1} />
      </div>

      {state === "signedOut" ? <SignedOutState /> : null}
      {state === "loading" || state === "checking" ? <Notice text="正在加载任务..." /> : null}
      {state === "error" ? <Notice text={error ?? "无法加载任务。"} /> : null}

      {state === "ready" ? (
        <div className="mt-8 grid gap-6">
          {error ? <Alert tone="error" text={error} /> : null}
          {notice ? <Alert tone="success" text={notice} /> : null}

          <GlassPanel>
            <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="font-serif text-2xl font-semibold text-memoryText">任务状态</h2>
                <p className="mt-2 text-sm leading-7 text-memoryText/70">
                  可以重试或取消未完成的任务，状态会回写到后端任务记录。
                </p>
              </div>
              <span className="text-sm font-semibold text-memoryText/60">
                {jobs.length} 个任务
              </span>
            </div>
            {jobs.length === 0 ? (
              <p className="mt-6 rounded-2xl bg-memoryPaper/75 p-4 text-sm text-memoryText/70">
                还没有任务。上传文件或创建手动资料后会出现解析任务。
              </p>
            ) : (
              <div className="mt-6 grid gap-3">
                {jobs.map((job) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    busy={busyJobId === job.id}
                    onRetry={handleRetry}
                    onCancel={handleCancel}
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
        可以免注册体验外婆示例，或登录已有账号查看私有任务。
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

function JobCard({
  job,
  busy,
  onRetry,
  onCancel
}: {
  job: AIJobRead;
  busy: boolean;
  onRetry: (job: AIJobRead) => void;
  onCancel: (job: AIJobRead) => void;
}) {
  return (
    <article className="rounded-2xl border border-memoryLine/55 bg-memoryPaper/70 p-4 shadow-soft">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-memoryText">{jobTypeLabel(job.job_type)}</p>
          <p className="mt-1 text-xs font-semibold tracking-[0.08em] text-memoryAccent">
            {providerLabel(job.provider_type)}
            {job.provider_name ? ` · ${job.provider_name}` : ""}
          </p>
          <dl className="mt-4 grid gap-2 text-xs text-memoryText/60 md:grid-cols-3">
            <Stat label="状态" value={jobStatusLabel(job.status)} />
            <Stat label="重试次数" value={String(job.retry_count)} />
            <Stat label="创建时间" value={formatDate(job.created_at)} />
          </dl>
          {job.error_message ? (
            <p className="mt-3 text-sm leading-6 text-red-700">{job.error_message}</p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy || !canRetryJob(job.status)}
            onClick={() => onRetry(job)}
            className={secondaryButtonClass}
          >
            重试
          </button>
          <button
            type="button"
            disabled={busy || !canCancelJob(job.status)}
            onClick={() => onCancel(job)}
            className={secondaryButtonClass}
          >
            取消
          </button>
        </div>
      </div>
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

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function jobTypeLabel(value: string): string {
  const labels: Record<string, string> = {
    parse_material: "资料解析",
    extract_memory: "记忆抽取",
    update_profile: "更新人格档案",
    calculate_trust_score: "计算可信度",
    synthesize_speech: "语音合成"
  };

  return labels[value] ?? value;
}

function providerLabel(value: string): string {
  const labels: Record<string, string> = {
    text_parser: "文本解析",
    ocr: "图片文字识别",
    asr: "音频转写",
    image_understanding: "图片理解",
    video_understanding: "视频理解",
    memory_extraction: "记忆抽取",
    chat_llm: "文本对话",
    tts: "语音合成"
  };

  return labels[value] ?? value;
}

const secondaryButtonClass =
  "rounded-2xl border border-memoryLine/80 bg-white/72 px-4 py-2.5 text-sm font-semibold text-memoryText shadow-soft transition hover:border-memoryAccent hover:text-memoryAccent disabled:cursor-not-allowed disabled:border-memoryLine/40 disabled:text-memoryText/35";
