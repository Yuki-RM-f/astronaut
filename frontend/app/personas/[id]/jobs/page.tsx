"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  PageTitle,
  StarNav,
  StarPanel,
  StarShell
} from "@/src/components/StarSite";
import { PersonaBackLink } from "@/src/components/PersonaBackLink";
import { ensureDemoSession } from "@/src/lib/auth";
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

type PageState = "loading" | "ready" | "error";

export default function PersonaJobsPage() {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<PageState>("loading");
  const [jobs, setJobs] = useState<AIJobRead[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyJobId, setBusyJobId] = useState<string | null>(null);

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
      .then(() => listJobs(personaId))
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
          title="资料整理进度"
          subtitle="这里展示资料进入当前后端解析链路后的状态。"
        />

        {state === "loading" ? <Notice text="正在加载任务..." /> : null}
        {state === "error" ? <Notice text={error ?? "无法加载任务。"} /> : null}

        {state === "ready" ? (
          <div className="mt-8 grid gap-6">
            {error ? <Alert tone="error" text={error} /> : null}
            {notice ? <Alert tone="success" text={notice} /> : null}

            <div className="grid gap-3 md:grid-cols-4">
              <StatusSummary label="全部任务" value={jobs.length} />
              <StatusSummary
                label="进行中"
                value={jobs.filter((job) => ["pending", "running"].includes(job.status)).length}
              />
              <StatusSummary
                label="已完成"
                value={jobs.filter((job) => job.status === "succeeded").length}
              />
              <StatusSummary
                label="需处理"
                value={jobs.filter((job) => ["failed", "canceled"].includes(job.status)).length}
              />
            </div>

            <StarPanel className="p-5">
              <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
                <div>
                  <h2 className="font-serif text-2xl font-bold text-starGold">任务状态</h2>
                  <p className="mt-2 text-sm font-semibold leading-7 text-starMist/70">
                    可以重试或取消未完成的任务，状态会回写到后端任务记录。
                  </p>
                </div>
                <span className="text-sm font-bold text-starMist/60">{jobs.length} 个任务</span>
              </div>
              {jobs.length === 0 ? (
                <p className="mt-6 rounded-2xl border border-white/8 bg-white/6 p-4 text-sm font-semibold text-starMist/70">
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
            </StarPanel>
          </div>
        ) : null}
      </main>
    </StarShell>
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
    <article className="rounded-2xl border border-white/8 bg-white/6 p-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-bold text-starCream">{jobTypeLabel(job.job_type)}</p>
          <p className="mt-1 text-xs font-bold tracking-[0.08em] text-starGold">
            {providerLabel(job.provider_type)}
            {job.provider_name ? ` · ${job.provider_name}` : ""}
          </p>
          <dl className="mt-4 grid gap-2 text-xs text-starMist/60 md:grid-cols-3">
            <Stat label="状态" value={jobStatusLabel(job.status)} />
            <Stat label="重试次数" value={String(job.retry_count)} />
            <Stat label="创建时间" value={formatDate(job.created_at)} />
          </dl>
          {job.error_message ? (
            <p className="mt-3 text-sm font-semibold leading-6 text-rose-100">{job.error_message}</p>
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

function StatusSummary({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/6 p-4">
      <dt className="text-xs font-bold text-starMist/52">{label}</dt>
      <dd className="mt-1 text-2xl font-bold text-starCream">{value}</dd>
    </div>
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
  "rounded-full border border-starGold/22 bg-starGold/10 px-4 py-2.5 text-sm font-bold text-starCream transition hover:bg-starGold/16 disabled:cursor-not-allowed disabled:opacity-35";
