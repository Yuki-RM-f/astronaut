import assert from "node:assert/strict";
import test from "node:test";
import {
  auditEventLabel,
  auditSeverityLabel,
  buildAuditSearchPayload,
  buildResolveConflictPayload,
  conflictStatusLabel,
  formatRelevanceScore
} from "../src/lib/audit.js";

test("audit search payload trims query and clamps result count", () => {
  assert.deepEqual(buildAuditSearchPayload("  馄饨  "), {
    query: "馄饨",
    top_k: 5
  });
  assert.deepEqual(buildAuditSearchPayload("外婆", 24), {
    query: "外婆",
    top_k: 10
  });
  assert.deepEqual(buildAuditSearchPayload("外婆", 0), {
    query: "外婆",
    top_k: 1
  });
  assert.throws(() => buildAuditSearchPayload("   "), /query/);
});

test("resolve conflict payload only allows user-facing resolution states", () => {
  assert.deepEqual(buildResolveConflictPayload("resolved_by_user"), {
    resolution_status: "resolved_by_user"
  });
  assert.deepEqual(buildResolveConflictPayload("dismissed"), {
    resolution_status: "dismissed"
  });
  assert.throws(() => buildResolveConflictPayload("open"), /resolution/);
});

test("audit labels are stable for v2 timeline and conflict center", () => {
  assert.equal(auditEventLabel("memory.retrieved"), "记忆被对话引用");
  assert.equal(auditEventLabel("profile.regenerated"), "画像已重生成");
  assert.equal(auditSeverityLabel("warning"), "警告");
  assert.equal(conflictStatusLabel("resolved_by_user"), "已按用户处理");
  assert.equal(formatRelevanceScore(0.873), "87%");
});
