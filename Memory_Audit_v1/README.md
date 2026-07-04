# Memory Audit（记忆审计）完整资料

## 文件夹结构

```
Memory_Audit/
├── README.md                        ← 本文件
├── Memory_Audit_Design.md           ← 完整机制设计文档（12 节）
├── Memory_Audit_Demo.html           ← 路演 Demo（用户视角，浏览器打开）
│
└── backend/
    ├── models/                      ← 4 张数据表模型
    │   ├── audit_log.py             #   审计日志表（扩展）
    │   ├── audit_snapshot.py        #   版本快照表
    │   ├── memory_conflict.py       #   冲突记录表
    │   └── persona_drift.py         #   漂移检测表
    │
    ├── services/                    ← 3 个核心服务
    │   ├── audit.py                 #   审计写入、快照、回滚、报告、仪表盘（~450 行）
    │   ├── conflict_detector.py     #   冲突检测引擎（否定词模式匹配）
    │   └── drift_detector.py        #   漂移检测引擎（Jaccard 距离）
    │
    ├── schemas/                     ← Pydantic 响应模型
    │   └── audit.py                 #   15 个 Schema
    │
    ├── api/                         ← FastAPI 路由
    │   └── audit.py                 #   12 个 API 端点
    │
    ├── tests/                       ← 测试
    │   └── test_audit.py            #   19 个测试用例
    │
    └── modified/                    ← 被修改的现有文件（审计钩子集成）
        ├── main.py                  #   注册 audit_router
        ├── base.py                  #   导入新模型
        ├── memories.py              #   记忆 CRUD 处插入审计钩子
        ├── chat.py                  #   对话引用 + 侧边栏修正写审计事件
        ├── profile.py               #   画像刷新写 trust_changed 事件
        ├── profile_routes.py        #   手动编辑画像字段写 field_edited 事件
        └── stories.py               #   故事生成写 cited_in_story 事件
```

## 设计文档 + 路演 Demo

| 文件 | 用途 |
|------|------|
| `Memory_Audit_Design.md` | 完整机制设计 — 事件体系、数据模型、服务 API、集成策略 |
| `Memory_Audit_Demo.html` | 交互式演示页面 — 记忆审查台、冲突中心、版本管理、追溯查询 |

- **测试 1 个文件**：test_audit.py（19 个测试全部通过）
