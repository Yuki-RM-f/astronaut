import { API_PATHS, buildApiUrl, readApiJson } from "./api";
import { authHeaders } from "./auth";
import type { MemoryRead } from "./memories";

export type AuditSeverity = "debug" | "info" | "warning" | "error";
export type ConflictResolutionStatus = "open" | "resolved_by_user" | "dismissed";
export type ResolveConflictStatus = Exclude<ConflictResolutionStatus, "open">;

export type AuditLogRead = {
  id: string;
  user_id: string;
  persona_id: string | null;
  target_type: string | null;
  target_id: string | null;
  action: string | null;
  event_type: string;
  severity: AuditSeverity | string;
  changed_fields: string[] | null;
  before_json: Record<string, unknown> | unknown[] | null;
  after_json: Record<string, unknown> | unknown[] | null;
  correlation_id: string | null;
  parent_event_id: string | null;
  metadata_json: Record<string, unknown> | unknown[] | null;
  created_at: string;
};

export type AuditLogListResponse = {
  items: AuditLogRead[];
  total: number;
  limit: number;
  offset: number;
};

export type AuditSummaryResponse = {
  persona_id: string;
  total_events: number;
  by_event_type: Record<string, number>;
  by_severity: Record<string, number>;
  recent_events: AuditLogRead[];
  open_conflicts: number;
  health_score: number;
};

export type AuditDashboardResponse = {
  persona_id: string;
  health_score: number;
  pending_review_count: number;
  open_conflict_count: number;
  source_coverage: Record<string, number>;
  recent_events: AuditLogRead[];
};

export type MemoryConflictRead = {
  id: string;
  persona_id: string;
  memory_id_a: string;
  memory_id_b: string;
  memory_title_a: string | null;
  memory_title_b: string | null;
  conflict_type: string;
  conflict_description: string;
  resolution_status: ConflictResolutionStatus | string;
  resolved_by: string | null;
  resolved_at: string | null;
  severity: AuditSeverity | string;
  created_at: string;
  updated_at: string;
};

export type MemoryConflictListResponse = {
  items: MemoryConflictRead[];
  total: number;
};

export type AuditReportResponse = {
  persona_id: string;
  generated_at: string;
  summary: AuditSummaryResponse;
  events_by_day: Record<string, number>;
  conflicts: MemoryConflictRead[];
  recommendations: string[];
};

export type SearchResultItem = {
  memory: MemoryRead;
  relevance_score: number;
  matched_terms: string[];
  source_excerpt: string | null;
};

export type SearchResponse = {
  query: string;
  items: SearchResultItem[];
  total: number;
};

export type MemoryHistoryResponse = {
  memory_id: string;
  events: AuditLogRead[];
  conflicts: MemoryConflictRead[];
};

export type AuditSearchPayload = {
  query: string;
  top_k: number;
};

export type ResolveConflictPayload = {
  resolution_status: ResolveConflictStatus;
};

export function buildAuditSearchPayload(query: string, topK = 5): AuditSearchPayload {
  const trimmed = query.trim();
  if (!trimmed) {
    throw new Error("query cannot be blank");
  }
  const requestedTopK = Number.isFinite(topK) ? Math.trunc(topK) : 5;
  return {
    query: trimmed,
    top_k: Math.max(1, Math.min(10, requestedTopK))
  };
}

export function buildResolveConflictPayload(
  resolutionStatus: string
): ResolveConflictPayload {
  if (resolutionStatus !== "resolved_by_user" && resolutionStatus !== "dismissed") {
    throw new Error("resolution status is not allowed");
  }
  return { resolution_status: resolutionStatus };
}

export function auditEventLabel(eventType: string): string {
  return (
    {
      "memory.created": "记忆已创建",
      "memory.updated": "记忆已更新",
      "memory.confirmed": "记忆已确认",
      "memory.rejected": "记忆已拒绝",
      "memory.disabled": "记忆已停用",
      "memory.deleted": "记忆已删除",
      "memory.retrieved": "记忆被对话引用",
      "memory.corrected_in_chat": "对话中纠正记忆",
      "memory.cited_in_story": "故事引用记忆",
      "memory.searched": "执行语义搜索",
      "memory.conflict_detected": "发现记忆冲突",
      "memory.conflict_resolved": "记忆冲突已处理",
      "profile.field_edited": "画像字段已编辑",
      "profile.regenerated": "画像已重生成",
      "trust.changed": "可信度已变化"
    }[eventType] ?? eventType
  );
}

export function auditSeverityLabel(severity: string): string {
  return (
    {
      debug: "调试",
      info: "信息",
      warning: "警告",
      error: "错误"
    }[severity] ?? severity
  );
}

export function conflictStatusLabel(status: string): string {
  return (
    {
      open: "待处理",
      resolved_by_user: "已按用户处理",
      dismissed: "已忽略"
    }[status] ?? status
  );
}

export function formatRelevanceScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export async function listAuditLogs(
  personaId: string,
  params: Record<string, string | number | undefined> = {}
): Promise<AuditLogListResponse> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  }
  const path = API_PATHS.audit.logs(personaId);
  const url = query.size > 0 ? `${path}?${query.toString()}` : path;
  const response = await fetch(buildApiUrl(url), { headers: authHeaders() });
  return readApiJson<AuditLogListResponse>(response, "无法加载审计日志。");
}

export async function getAuditSummary(personaId: string): Promise<AuditSummaryResponse> {
  const response = await fetch(buildApiUrl(API_PATHS.audit.summary(personaId)), {
    headers: authHeaders()
  });
  return readApiJson<AuditSummaryResponse>(response, "无法加载审计摘要。");
}

export async function getAuditDashboard(
  personaId: string
): Promise<AuditDashboardResponse> {
  const response = await fetch(buildApiUrl(API_PATHS.audit.dashboard(personaId)), {
    headers: authHeaders()
  });
  return readApiJson<AuditDashboardResponse>(response, "无法加载审计仪表盘。");
}

export async function getAuditReport(personaId: string): Promise<AuditReportResponse> {
  const response = await fetch(buildApiUrl(API_PATHS.audit.report(personaId)), {
    headers: authHeaders()
  });
  return readApiJson<AuditReportResponse>(response, "无法加载审计报告。");
}

export async function listConflicts(
  personaId: string
): Promise<MemoryConflictListResponse> {
  const response = await fetch(buildApiUrl(API_PATHS.audit.conflicts(personaId)), {
    headers: authHeaders()
  });
  return readApiJson<MemoryConflictListResponse>(response, "无法加载冲突中心。");
}

export async function resolveConflict(
  personaId: string,
  conflictId: string,
  resolutionStatus: ResolveConflictStatus
): Promise<MemoryConflictRead> {
  const response = await fetch(
    buildApiUrl(API_PATHS.audit.resolveConflict(personaId, conflictId)),
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders()
      },
      body: JSON.stringify(buildResolveConflictPayload(resolutionStatus))
    }
  );
  return readApiJson<MemoryConflictRead>(response, "无法处理记忆冲突。");
}

export async function searchAuditMemories(
  personaId: string,
  query: string,
  topK = 5
): Promise<SearchResponse> {
  const response = await fetch(buildApiUrl(API_PATHS.audit.search(personaId)), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify(buildAuditSearchPayload(query, topK))
  });
  return readApiJson<SearchResponse>(response, "无法完成语义搜索。");
}

export async function getMemoryHistory(memoryId: string): Promise<MemoryHistoryResponse> {
  const response = await fetch(buildApiUrl(API_PATHS.audit.history(memoryId)), {
    headers: authHeaders()
  });
  return readApiJson<MemoryHistoryResponse>(response, "无法加载记忆历史。");
}
