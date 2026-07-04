# Memory Audit（记忆审计）— 完整机制设计

## 概述

Memory Audit 是"亲友纪念数字人"的可信基石。它确保数字人说的每一句话都可以追溯到原始聊天记录，每一次修改都有日志可查，每一次人格变化都有版本可回溯。

**核心问题**：当用户与"数字外婆"对话时，如何确保：
- 她说的话有据可查？
- 记忆被修改时不被篡改？
- 人格不会因为新增资料而悄悄"漂移"？
- 所有操作都有完整的审计链？

**答案**：三层审计 + 事件溯源 + 快照版本管理。

---

## 一、设计原则

### 1. 全事件溯源（Event Sourcing）
不是只存当前状态，而是记录每一次变更事件。任何时刻的"记忆全景"都可以通过重放事件日志重建。

### 2. 不可篡改
审计日志一旦写入，不提供修改或删除 API。只能追加，不能覆盖。

### 3. 可追溯、可回滚
每条回复 → 引用记忆卡片 → 引用源材料 → 引用原始文件。任一层级出问题都可以定位溯源。支持回滚到任意历史快照。

### 4. 主动告警
系统自动检测记忆冲突和人格漂移，主动提醒用户审查，而不是等出问题再排查。

### 5. 用户可修正
用户是最终仲裁者。系统提供修正入口，但修正本身也被审计记录。

---

## 二、三层审计架构

对应展览路演材料中的三层设计：

```
第一层：回复级追溯
┌─────────────────────────────────────────┐
│ 用户: "你以前喜欢做什么给我吃？"        │
│ ─────────────────────────────────────── │
│ 外婆: "小铭，我记得，外婆喜欢包馄饨给   │
│       你吃。"                           │
│                                         │
│ ▸ 依据记忆卡片 #M042 [置信度 90%]       │
│   └ 来源: 微信聊天记录 2024.03.15       │
│      "小铭，外婆今天包了你最爱吃的馄饨" │
└─────────────────────────────────────────┘

第二层：记忆管理面板
┌─────────────────────────────────────────┐
│ 记忆列表 │ 搜索 ▢ │ 筛选 [状态 ▼]      │
│ ─────────────────────────────────────── │
│ ☑ 外婆喜欢包馄饨     confirmed  90%    │
│ ☐ 外婆喜欢买花       pending   60%     │
│ ✎ 外婆常说"慢慢来"   corrected 85%    │
│ ✕ 外婆喜欢重庆火锅   rejected  30%     │
│                                         │
│ 操作: [批量确认] [批量导出] [新建快照]  │
└─────────────────────────────────────────┘

第三层：审计日志
┌─────────────────────────────────────────┐
│ 时间          │ 操作        │ 详情      │
│ ─────────────────────────────────────── │
│ 07-04 14:32  │ memory.confirmed │ M042  │
│ 07-04 10:15  │ memory.corrected │ M038  │
│ 07-03 18:00  │ snapshot.created │ V4     │
│ 07-03 09:45  │ conflict.detected│ #C012  │
│                                         │
│ 操作: [查看详情] [回滚到此快照]          │
└─────────────────────────────────────────┘
```

---

## 三、审计事件分类体系

### 3.1 事件类型定义（18 种）

#### 记忆类事件

| event_type | 触发时机 | 严重度 | 说明 |
|------------|---------|--------|------|
| `memory.created` | 记忆卡片创建（系统提取或用户手动） | info | 记录创建来源 |
| `memory.confirmed` | 用户确认记忆 | info | pending → confirmed |
| `memory.corrected` | 用户编辑记忆内容或标题 | warning | 自动设置 status=corrected |
| `memory.corrected_in_chat` | 用户在对话侧边栏纠正引用记忆 | warning | 与 memory.corrected 区分入口 |
| `memory.rejected` | 用户驳回记忆 | warning | 记忆被标记为不可用 |
| `memory.disabled` | 用户禁用记忆 | info | 暂不使用但不删除 |
| `memory.deleted` | 软删除记忆 | critical | 不可逆操作，记录完整快照 |
| `memory.retrieved` | 记忆在对话中被检索并引用 | debug | 追踪"哪条记忆被用了" |
| `memory.cited_in_story` | 记忆作为故事生成的来源 | info | 追踪记忆 → 故事链路 |

#### 人物类事件

| event_type | 触发时机 | 严重度 | 说明 |
|------------|---------|--------|------|
| `persona.updated` | 人物字段变更（说话风格等） | info | 记录变更字段 |
| `persona.trust_changed` | trust_score 变化 ≥10 分 | warning | 显著信任变化需关注 |

#### 画像类事件

| event_type | 触发时机 | 严重度 | 说明 |
|------------|---------|--------|------|
| `profile.regenerated` | 画像从记忆完全重建 | info | 自动或手动触发 |
| `profile.field_edited` | 用户手动覆盖画像维度 | warning | 手动编辑优先于自动生成 |

#### 审计类事件

| event_type | 触发时机 | 严重度 | 说明 |
|------------|---------|--------|------|
| `snapshot.created` | 创建状态快照 | info | 定期/手动/回滚前 |
| `rollback.executed` | 用户回滚到历史快照 | critical | 不可逆操作，先自动创建安全快照 |
| `conflict.detected` | 系统检测到记忆矛盾 | warning | 自动触发，通知用户审查 |
| `drift.detected` | 画像维度变化超过阈值 | warning | 自动触发，通知用户关注 |

### 3.2 严重度定义

| 严重度 | 含义 | UI 表现 |
|--------|------|---------|
| `debug` | 技术追踪用，默认不展示 | 仅在详细审计视图可见 |
| `info` | 正常操作记录 | 时间线展示，无告警 |
| `warning` | 需要用户关注 | 黄色徽章 + 审查建议 |
| `critical` | 不可逆或破坏性操作 | 红色强调 + 操作前必须二次确认 |

---

## 四、数据模型

### 4.1 AuditLog（审计日志 — 扩展现有模型）

```
audit_logs 表
┌──────────────────────┬─────────────┬──────────────────────────────┐
│ 字段                 │ 类型        │ 说明                         │
├──────────────────────┼─────────────┼──────────────────────────────┤
│ id                   │ UUID PK     │                              │
│ user_id              │ FK users    │ 操作者                       │
│ persona_id           │ FK personas │ 所属人物（可空）             │
│ target_type          │ String(50)  │ 目标类型: memory_card,       │
│                      │             │   persona, persona_profile,  │
│                      │             │   audit_snapshot,            │
│                      │             │   memory_conflict,           │
│                      │             │   persona_drift              │
│ target_id            │ String(36)  │ 目标 ID（可空）             │
│ event_type           │ String(50)  │ 事件类型（见 3.1 节）       │
│ severity             │ String(20)  │ debug/info/warning/critical  │
│ action               │ Text        │ 人类可读的操作摘要            │
│ changed_fields       │ JSON        │ 变更的字段名列表              │
│ before_snapshot      │ JSON        │ 变更前完整状态（序列化 dict） │
│ after_snapshot       │ JSON        │ 变更后完整状态（序列化 dict） │
│ correlation_id       │ String(36)  │ 跨表操作的关联 ID            │
│ parent_event_id      │ FK self     │ 链接因果事件（如 drift 链接  │
│                      │             │   到触发它的 memory 变更）    │
│ metadata_json        │ JSON        │ request_id, ip, user_agent   │
│ created_at           │ DateTime    │ 事件时间戳（不可修改）        │
└──────────────────────┴─────────────┴──────────────────────────────┘

索引:
  (persona_id, event_type, created_at DESC)  -- 按人物查询事件
  (correlation_id)                            -- 关联事件查找
  (target_type, target_id)                    -- 按目标查询历史
```

### 4.2 AuditSnapshot（状态快照 — 新建）

```
audit_snapshots 表
┌──────────────────────┬─────────────┬──────────────────────────────┐
│ 字段                 │ 类型        │ 说明                         │
├──────────────────────┼─────────────┼──────────────────────────────┤
│ id                   │ UUID PK     │                              │
│ persona_id           │ FK personas │                              │
│ snapshot_type        │ String(20)  │ auto_periodic / manual /     │
│                      │             │   pre_rollback               │
│ label                │ Text        │ 用户标签，如"Q2审查前"       │
│ persona_snapshot     │ JSON        │ Persona 全部字段序列化       │
│ profile_snapshot     │ JSON        │ PersonaProfile 全部字段      │
│ memory_snapshots     │ JSON        │ 全部活跃 MemoryCard 列表     │
│ trust_report         │ JSON        │ TrustReport 序列化           │
│ memory_count         │ Integer     │ 去范式化：记忆总数           │
│ trust_score          │ Integer     │ 去范式化：信任分数           │
│ created_at           │ DateTime    │ 快照时间戳                   │
└──────────────────────┴─────────────┴──────────────────────────────┘

快照策略:
  - manual: 用户手动创建，永久保留
  - pre_rollback: 回滚前自动创建的安全快照，永久保留
  - auto_periodic: 定期自动快照
    保留: 30 天内全部保留，30-90 天每周 1 份，>90 天每月 1 份
```

### 4.3 MemoryConflict（记忆冲突 — 新建）

```
memory_conflicts 表
┌──────────────────────┬─────────────┬──────────────────────────────┐
│ 字段                 │ 类型        │ 说明                         │
├──────────────────────┼─────────────┼──────────────────────────────┤
│ id                   │ UUID PK     │                              │
│ persona_id           │ FK personas │                              │
│ memory_id_a          │ FK memories │ 冲突方 A                     │
│ memory_id_b          │ FK memories │ 冲突方 B                     │
│ conflict_type        │ String(30)  │ factual_contradiction /      │
│                      │             │   correction_vs_confirmed /  │
│                      │             │   temporal_inconsistency /   │
│                      │             │   category_overlap           │
│ conflict_description │ Text        │ 人类可读描述                 │
│ resolution_status    │ String(20)  │ open / acknowledged /        │
│                      │             │   resolved_by_user /         │
│                      │             │   resolved_by_correction /   │
│                      │             │   dismissed                  │
│ resolved_by          │ FK users    │ 解决者（可空）              │
│ resolved_at          │ DateTime    │ 解决时间（可空）            │
│ severity             │ String(20)  │ high / medium / low          │
│ created_at           │ DateTime    │                              │
│ updated_at           │ DateTime    │                              │
└──────────────────────┴─────────────┴──────────────────────────────┘
```

### 4.4 PersonaDrift（人格漂移 — 新建）

```
persona_drifts 表
┌──────────────────────┬─────────────┬──────────────────────────────┐
│ 字段                 │ 类型        │ 说明                         │
├──────────────────────┼─────────────┼──────────────────────────────┤
│ id                   │ UUID PK     │                              │
│ persona_id           │ FK personas │                              │
│ snapshot_id_before   │ FK snapshots│ 漂移前快照                   │
│ snapshot_id_after    │ FK snapshots│ 漂移后快照                   │
│ dimension            │ String(50)  │ 变化的维度名或 "trust_score" │
│                      │             │   或 "memory_count"          │
│ drift_score          │ Float       │ 变化幅度 (0.0-1.0)          │
│ before_summary       │ Text        │ 变化前摘要                   │
│ after_summary        │ Text        │ 变化后摘要                   │
│ triggered_alert      │ Boolean     │ 是否触发告警                 │
│ acknowledged_at      │ DateTime    │ 用户确认时间（可空）        │
│ created_at           │ DateTime    │                              │
└──────────────────────┴─────────────┴──────────────────────────────┘

漂移阈值:
  trust_score:     绝对变化 ≥15 分 → 告警
  memory_count:    相对变化 ≥30%  → 告警
  profile_dimension: Jaccard 距离 ≥0.40 → 告警（某维度条目集合变化超过 40%）
```

---

## 五、服务层

### 5.1 app/services/audit.py — 核心审计服务

```
write_audit_event(db, *, user_id, persona_id, target_type, target_id,
    event_type, severity, action, before_snapshot=None, after_snapshot=None,
    changed_fields=None, correlation_id=None, parent_event_id=None,
    metadata_json=None, commit=True) → AuditLog
  # 写入一条审计事件。commit=False 时只 flush，用于批量操作。

snapshot_entity(model_instance) → dict
  # 将任意 SQLAlchemy 模型实例序列化为 JSON 安全的 dict。
  # 反射 Column 属性，递归处理日期/枚举。

diff_before_after(before: dict, after: dict) → list[str]
  # 比较两个 dict，返回变更的字段名列表。

# --- 查询 ---

query_audit_logs(db, *, persona_id, event_type=None, severity=None,
    target_type=None, target_id=None, user_id=None, date_from=None,
    date_to=None, correlation_id=None, limit=50, offset=0)
    → (list[AuditLog], total_count)
  # 多条件筛选审计日志。返回分页结果 + 总数。

get_memory_change_history(db, memory_id, limit=100) → list[AuditLog]
  # 单条记忆的完整变更历史。

get_audit_summary(db, persona_id) → dict
  # 聚合统计：总事件数、按严重度分布、按类型分布、
  # 未解决冲突数、未确认漂移数、最近快照信息。

# --- 报告 ---

generate_audit_report(db, persona_id) → dict
  # 生成完整审计报告结构（供前端渲染 Markdown/PDF）。
  # 包含：元数据、事件时间线(最近200条)、冲突列表、
  # 漂移列表、信任分数趋势(最近10个快照)、来源覆盖图。

# --- 快照 ---

create_snapshot(db, *, persona_id, snapshot_type="manual",
    label=None, commit=True) → AuditSnapshot
  # 冻结当前 persona + profile + 全部活跃 memory 的完整状态。

compare_snapshots(db, snapshot_id_a, snapshot_id_b) → dict
  # 两个快照的结构化差异：
  # trust_score_delta, memory_count_delta,
  # persona_changes (字段名列表), profile_changes (维度名列表)

get_snapshots(db, persona_id, limit=20) → list[AuditSnapshot]

# --- 回滚 ---

rollback_to_snapshot(db, user_id, snapshot_id, confirmed=False) → AuditLog
  # 1. 自动创建 pre_rollback 安全快照
  # 2. 恢复 Persona 字段
  # 3. 恢复 PersonaProfile 字段
  # 4. 软删除当前全部记忆，从快照重新插入
  # 5. 写入 rollback.executed 审计事件
  # confirmed 必须为 True 才执行。
```

### 5.2 app/services/conflict_detector.py — 冲突检测

**检测算法**：基于否定词模式匹配 + 同主题不同值检测。

```
核心否定词模式:
  (喜欢, 不喜欢, 讨厌)
  (会, 不会, 从不)
  (是, 不是, 并非)
  (能, 不能, 无法)
  (爱, 不爱, 恨)
  (经常, 从不, 偶尔)
  (擅长, 不擅长, 不会)

同主题检测:
  两条记忆提取 ≥3 个相同的 2-gram 中文词组 → 同主题
  同主题 + 不同来源状态 → 潜在不一致

冲突分类:
  - factual_contradiction: 同类别同主题，内容矛盾
  - correction_vs_confirmed: 一条 confirmed vs 一条 pending/auto_generated
  - category_overlap: 不同类别但涉及相同实体
  - temporal_inconsistency: 时间线矛盾（未来实现）

冲突严重度:
  - high: 两条都是 confirmed 状态
  - medium: 一条 confirmed 一条其他
  - low: 两条都不是 confirmed

detect_conflicts_for_memory(db, memory, commit=True) → list[MemoryConflict]
  # 对一条记忆检查与同人物下所有其他活跃记忆的冲突。
  # 在 create_memory 和 update_memory 后调用。
  # 去重: 如果相同 (A,B) 组合已有 open 冲突，不再创建。

resolve_conflict(db, conflict_id, user_id, resolution) → MemoryConflict
  # resolution: "resolved_by_user" | "resolved_by_correction" | "dismissed"
```

### 5.3 app/services/drift_detector.py — 漂移检测

**检测算法**：比较两个快照，当任意维度变化超过阈值时生成告警。

```
DRIFT_THRESHOLDS = {
    "trust_score": 15,          # 绝对分数变化
    "memory_count": 0.30,       # 30% 相对变化
    "profile_dimension": 0.40,  # Jaccard 距离 (基于 memory_id 集合)
}

detect_drift_between_snapshots(db, snapshot_before, snapshot_after,
    commit=True) → list[PersonaDrift]
  # 比较两个快照的全部维度，超标则生成 drift 记录 + audit event。

check_drift_after_profile_change(db, persona_id, commit=True) → list[PersonaDrift]
  # 在记忆变更/画像更新后调用。
  # 自动创建新快照 → 与最近快照比较 → 检测漂移。
```

---

## 六、API 端点

全部挂载在 `app/api/routes/audit.py`，标签 `["audit"]`。

### 6.1 审计日志

```
GET /api/personas/{persona_id}/audit/logs
  参数: event_type, severity, target_type, target_id, user_id,
        date_from, date_to, correlation_id, limit(50), offset(0)
  返回: { items: AuditLogRead[], total, limit, offset }
  说明: 多条件筛选审计日志，按时间倒序。

GET /api/personas/{persona_id}/audit/summary
  返回: { total_events, by_severity, by_event_type,
          open_conflicts, unacknowledged_drifts,
          last_snapshot_at, last_snapshot_id }
  说明: 某个人物的审计聚合统计。

GET /api/personas/{persona_id}/audit/report
  返回: { report_generated_at, persona_name, summary, timeline,
          conflicts, drifts, trust_trend, current_trust, source_coverage }
  说明: 完整审计报告结构，供前端渲染 Markdown/PDF。

GET /api/memories/{memory_id}/history
  参数: limit(100)
  返回: { items: AuditLogRead[] }
  说明: 单条记忆的完整变更历史。
```

### 6.2 快照管理

```
POST /api/personas/{persona_id}/audit/snapshots
  Body: { snapshot_type: "manual"|"auto_periodic", label: string|null }
  返回: SnapshotRead
  说明: 创建手动快照。

GET /api/personas/{persona_id}/audit/snapshots
  参数: limit(20)
  返回: { items: SnapshotRead[] }
  说明: 快照列表，最新在前。

GET /api/personas/{persona_id}/audit/snapshots/compare
  参数: snapshot_id_a, snapshot_id_b
  返回: { snapshot_a, snapshot_b, trust_score_delta,
          memory_count_delta, persona_changes, profile_changes }
  说明: 两个快照的结构化差异。
```

### 6.3 回滚

```
POST /api/personas/{persona_id}/audit/rollback
  Body: { snapshot_id, confirmed: bool }
  返回: { success, safety_snapshot_id, rollback_event }
  说明: confirmed 必须为 true。自动创建安全快照后恢复状态。
        该操作本身被完整审计记录。
```

### 6.4 冲突管理

```
GET /api/personas/{persona_id}/audit/conflicts
  参数: resolution_status (默认 "open")
  返回: { items: ConflictRead[] }
  说明: 列出冲突，默认只看未解决的。

POST /api/personas/{persona_id}/audit/conflicts/{conflict_id}/resolve
  Body: { resolution: "resolved_by_user"|"dismissed" }
  返回: ConflictRead
  说明: 解决或忽略一个冲突。记录操作者和时间。
```

### 6.5 漂移管理

```
GET /api/personas/{persona_id}/audit/drifts
  参数: unacknowledged_only (默认 false)
  返回: { items: DriftRead[] }
  说明: 列出漂移记录。

POST /api/personas/{persona_id}/audit/drifts/{drift_id}/acknowledge
  返回: DriftRead
  说明: 确认漂移告警（不回退，仅消除告警状态）。
```

### 6.6 仪表盘

```
GET /api/personas/{persona_id}/audit/dashboard
  返回: {
    memory_health_score,      # 0-100，记忆健康度综合评分
    review_queue_size,         # 待审核记忆数量
    open_conflict_count,       # 未解决冲突数
    unacknowledged_drift_count,# 未确认漂移数
    recent_events,             # 最近 10 条审计事件（不含 debug）
    trust_score_trend,         # 最近 10 个快照的信任分数序列
    source_coverage            # 来源覆盖: 总数/类型/类别/状态/置信度分布
  }
```

---

## 七、集成钩子

在现有代码中嵌入审计事件写入，遵循"不改变原有逻辑，只追加审计"原则。

### 7.1 memories.py 集成

```
create_memory():
  原有逻辑 → db.refresh(memory)
  + write_audit_event(memory.created)
  + detect_conflicts_for_memory(memory)
  + check_drift_after_profile_change(persona_id)

update_memory():
  + before = snapshot_entity(memory)
  原有逻辑 → db.refresh(memory)
  + after = snapshot_entity(memory)
  + write_audit_event(memory.corrected, before, after)
  + detect_conflicts_for_memory(memory)

_set_memory_status() (confirm/reject/disable):
  + before = snapshot_entity(memory)
  原有逻辑
  + write_audit_event(memory.{confirmed|rejected|disabled}, before, after)

delete_memory():
  + before = snapshot_entity(memory)
  原有软删除逻辑
  + write_audit_event(memory.deleted, before)
  + check_drift_after_profile_change(persona_id)
```

### 7.2 chat.py 集成

```
send_text_message():
  原有逻辑
  + for each retrieved memory that was cited:
      write_audit_event(memory.retrieved, severity=debug,
        metadata={message_id, conversation_id, retrieval_score})

correct_cited_memory():
  + before = snapshot_entity(memory)
  原有纠正逻辑
  + after = snapshot_entity(memory)
  + write_audit_event(memory.corrected_in_chat, before, after)
  + detect_conflicts_for_memory(memory)
  + check_drift_after_profile_change(persona_id)
```

### 7.3 profile.py 集成

```
refresh_profile_and_trust():
  + before_trust = persona.trust_score
  原有逻辑
  + after_trust = persona.trust_score
  + if |after - before| >= 10:
      write_audit_event(persona.trust_changed)
  + write_audit_event(profile.regenerated)

update_profile() (路由层):
  + before = snapshot_entity(profile)
  原有逻辑
  + after = snapshot_entity(profile)
  + write_audit_event(profile.field_edited, diff_before_after(before, after))
```

### 7.4 stories.py 集成

```
generate_story():
  原有逻辑 → db.refresh(story)
  + for each source_memory_id:
      write_audit_event(memory.cited_in_story, metadata={story_id})
```

---

## 八、仪表盘数据模型

### 8.1 记忆健康度评分（Memory Health Score）

```
health_score = 以下三项加权:

  A. 审核完成度 (40%):
     confirmed 或 corrected 记忆数 / 活跃记忆总数 × 100

  B. 置信度平均分 (30%):
     avg(confidence_score) of all active memories / 100 × 100

  C. 来源可追溯率 (30%):
     同时有 source_quote 和 source_location 的记忆数 / 活跃总数 × 100

分数范围: 0-100
  0-30:   危险 — 大量未审核记忆，来源不清
  31-60:  需改进 — 建议批量审核
  61-80:  良好 — 大部分记忆可靠
  81-100: 优秀 — 记忆库健康
```

### 8.2 来源覆盖图（Source Coverage Map）

```json
{
  "total_memories": 42,
  "unique_sources_used": 8,
  "memories_by_source_type": {
    "text": 20, "image": 10, "audio": 8, "video": 4, "manual": 0
  },
  "memories_by_category": {
    "basic_fact": 10, "preference": 8, "shared_event": 12,
    "habit": 5, "expression_style": 7
  },
  "memories_by_status": {
    "confirmed": 20, "corrected": 8, "pending_review": 10, "rejected": 4
  },
  "memories_by_confidence": {
    "high": 25, "medium": 12, "low": 5
  }
}
```

### 8.3 信任分数趋势

```json
{
  "trust_score_trend": [
    {"at": "2026-06-01T00:00:00", "score": 45},
    {"at": "2026-06-15T00:00:00", "score": 52},
    {"at": "2026-07-01T00:00:00", "score": 68},
    {"at": "2026-07-04T14:00:00", "score": 72}
  ]
}
```
取最近 10 个快照的 trust_score + 当前实时值，按时间正序。

---

## 九、置信度阈值与措辞规则

与展览 HTML 中描述一致，在检索和回复生成中应用：

| 置信度区间 | 使用策略 | 回复措辞 |
|-----------|---------|---------|
| ≥ 0.85 (绿色) | 正常使用，措辞确定 | "我记得，外婆喜欢包馄饨给你吃。" |
| 0.70–0.84 (黄色) | 谨慎使用，措辞软化 | "我好像记得，外婆可能喜欢..." |
| 0.50–0.69 (橙色) | 加"可能/好像"前缀 | "我记不太清，不过好像..." |
| < 0.50 (红色) | 排除，不进入可用记忆池 | "这件事我记不太清..." |

此规则在 `app/services/chat.py` 的 `_used_memories()` 和 `generate_persona_reply()` 中落地。

---

## 十、用户修正流程

```
用户发现回复有误
      │
      ▼
点击回复旁的记忆卡片
      │
      ▼
查看原始来源（聊天记录片段）
      │
      ▼
点击"修正" → 输入正确内容
      │
      ▼
┌─────────────────────────────┐
│ 系统自动执行:               │
│ 1. 更新 memory.content      │
│ 2. 设置 status = corrected  │
│ 3. 写审计日志 (before/after)│
│ 4. 触发冲突检测             │
│ 5. 触发漂移检测             │
│ 6. 刷新 Persona Profile     │
│ 7. 重算 Trust Score         │
└─────────────────────────────┘
      │
      ▼
下次对话立即生效
```

---

## 十一、与现有系统的关系

```
已有系统                          新增审计层
──────────                      ──────────
MemoryCard CRUD          ──→    审计事件记录
Status 流转              ──→    每次状态变更 = 一条 event
Trust Score              ──→    trust_changed 事件 + 趋势追踪
PersonaProfile           ──→    profile.regenerated / field_edited 事件
Chat 检索                ──→    memory.retrieved 追踪（debug 级）
Chat 纠正                ──→    memory.corrected_in_chat 事件
Story 生成               ──→    memory.cited_in_story 事件
                         ──→    AuditSnapshot 定期冻结
                         ──→    MemoryConflict 自动检测
                         ──→    PersonaDrift 自动检测
                         ──→    Rollback 回滚能力
```

---

## 十二、文件规划

```
新增文件:
  app/models/audit_snapshot.py      — AuditSnapshot 模型
  app/models/memory_conflict.py     — MemoryConflict 模型
  app/models/persona_drift.py       — PersonaDrift 模型
  app/services/audit.py             — 审计核心服务
  app/services/conflict_detector.py  — 冲突检测服务
  app/services/drift_detector.py    — 漂移检测服务
  app/schemas/audit.py              — 审计 Pydantic schemas
  app/api/routes/audit.py           — 审计 API 路由 (12 端点)

修改文件:
  app/models/audit_log.py           — 新增字段
  app/db/base.py                    — 导入新模型
  app/main.py                       — 注册 audit router
  app/api/routes/memories.py        — 嵌入审计钩子
  app/api/routes/profile.py         — 嵌入审计钩子
  app/api/routes/chat.py            — 嵌入审计钩子
  app/services/chat.py              — 嵌入检索追踪 + 纠正审计
  app/services/profile.py           — 嵌入 trust_changed 检测
  app/services/stories.py           — 嵌入 story 引用审计

新增测试:
  tests/test_audit.py               — 审计服务测试
  tests/test_conflict_detector.py   — 冲突检测测试
  tests/test_drift_detector.py      — 漂移检测测试
  tests/test_audit_api.py           — 审计 API 测试

数据库:
  alembic/versions/0003_audit_enhancements.py  — Migration
```
