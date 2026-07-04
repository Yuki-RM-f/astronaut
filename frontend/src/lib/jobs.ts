import { API_PATHS, buildApiUrl, readApiJson } from "./api";
import { authHeaders } from "./auth";

export const JOB_STATUSES = [
  "pending",
  "running",
  "succeeded",
  "failed",
  "retrying",
  "canceled"
] as const;

export type AIJobStatus = (typeof JOB_STATUSES)[number];

export type AIJobRead = {
  id: string;
  persona_id: string | null;
  source_material_id: string | null;
  job_type: string;
  provider_type: string;
  provider_name: string | null;
  status: AIJobStatus;
  input_json: Record<string, unknown> | unknown[] | null;
  output_json: Record<string, unknown> | unknown[] | null;
  error_message: string | null;
  retry_count: number;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

type AIJobListResponse = {
  items: AIJobRead[];
};

export function jobStatusLabel(status: AIJobStatus): string {
  const labels: Record<AIJobStatus, string> = {
    pending: "等待中",
    running: "处理中",
    succeeded: "已完成",
    failed: "失败",
    retrying: "重试中",
    canceled: "已取消"
  };

  return labels[status];
}

export function canCancelJob(status: AIJobStatus): boolean {
  return status === "pending" || status === "running" || status === "retrying";
}

export function canRetryJob(status: AIJobStatus): boolean {
  return status !== "running";
}

export async function listJobs(personaId: string): Promise<AIJobRead[]> {
  const response = await fetch(buildApiUrl(API_PATHS.jobs.list(personaId)), {
    headers: authHeaders()
  });
  const data = await readApiJson<AIJobListResponse>(response, "无法加载任务。");
  return data.items;
}

export async function retryJob(id: string): Promise<AIJobRead> {
  const response = await fetch(buildApiUrl(API_PATHS.jobs.retry(id)), {
    method: "POST",
    headers: authHeaders()
  });
  return readApiJson<AIJobRead>(response, "无法重试任务。");
}

export async function cancelJob(id: string): Promise<AIJobRead> {
  const response = await fetch(buildApiUrl(API_PATHS.jobs.cancel(id)), {
    method: "POST",
    headers: authHeaders()
  });
  return readApiJson<AIJobRead>(response, "无法取消任务。");
}
