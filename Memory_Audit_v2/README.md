# Memory Audit v2 — 记忆档案馆 (Memory Archive)

## v2 vs v1 变化

v1 是完整审计基础设施，v2 聚焦「记忆档案馆」体验。

| 组件 | v1 | v2 |
|------|----|----|
| 审计日志 (AuditLog) | 保留 | 保留 |
| 冲突检测 (ConflictDetector) | 保留 | 保留（精简否定词匹配） |
| 漂移检测 (PersonaDrift) | 有 | **移除** |
| 快照 (AuditSnapshot) | 有 | **移除** |
| 回滚 (Rollback) | 有 | **移除** |
| 仪表盘 (Dashboard) | 有 | 保留 |
| 语义检索 (Semantic Search) | 无 | **新增** |

## 文件夹结构

```
Memory_Audit_v2/
├── README.md
├── Memory_Audit_v2_Demo.html          ← 记忆档案馆前端（梦幻治愈风）
│
└── backend/
    ├── models/
    │   ├── audit_log.py               ← 审计日志模型
    │   └── memory_conflict.py         ← 记忆冲突模型
    │
    ├── services/
    │   ├── audit.py                   ← 审计核心（写、查、报告、仪表盘）
    │   ├── conflict_detector.py       ← 冲突检测（否定词模式匹配）
    │   └── semantic_search.py         ← 语义向量检索（TF-IDF + Cosine）
    │
    ├── schemas/
    │   └── audit.py                   ← Pydantic schemas（含 Search）
    │
    ├── api/
    │   └── audit.py                   ← API 路由（10 endpoints）
    │
    ├── tests/
    │   └── test_audit.py              ← 测试（15 tests）
    │
    └── modified/                      ← 集成钩子
        ├── main.py, base.py
        ├── memories.py, chat.py
        ├── profile.py, profile_routes.py
        └── stories.py
```

## API 端点

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/personas/{id}/audit/logs` | 审计日志（多条件筛选） |
| GET | `/personas/{id}/audit/summary` | 审计聚合统计 |
| GET | `/personas/{id}/audit/report` | 完整审计报告 |
| GET | `/memories/{id}/history` | 单条记忆变更历史 |
| GET | `/personas/{id}/audit/conflicts` | 冲突列表 |
| POST | `/personas/{id}/audit/conflicts/{id}/resolve` | 解决冲突 |
| GET | `/personas/{id}/audit/dashboard` | 仪表盘 |
| **POST** | `/personas/{id}/audit/search` | **语义检索（新增）** |

## 语义检索

POST `/personas/{id}/audit/search`
```json
{ "query": "馄饨", "top_k": 5 }
```
返回按相关度排序的记忆卡片，含 `relevance_score`。检索操作被审计记录（`memory.searched` 事件）。
