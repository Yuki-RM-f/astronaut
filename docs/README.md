# 可信人格记忆Agent Docs Harness

本目录提供项目的 docs-driven harness。它用于把目标、范围、实现事实、验证入口和 agent 交接规则放在同一套文档约束中，避免后续开发在没有上下文的情况下扩大范围或重复判断。

当前仓库已完成 Milestone 0 基础工程、Milestone 1 人物创建/记忆空间基础闭环、Milestone 2 资料上传/任务队列基础闭环、Milestone 3 mock 多模态解析/记忆审计基础闭环、Milestone 4 人格档案/可信度基础闭环、Milestone 5 第一人称文本对话基础闭环，Milestone 6 Task 1/2/3/4 后端默认 TTS、语音合成、音色样本、音色克隆兜底、语音消息 ASR 到 TTS、前端录音、声音设置和 mock 语音播放基础闭环，并已接入 Milestone 7 Task 1/2/3 后端 3D 数字人配置、默认形象、mock 生成、前端 Three.js mock 预览、对话页 3D 数字人展示和播放状态口型联动基础闭环，以及全站温馨沉浸式「记忆空间」前端与免注册一键演示入口：后端为 FastAPI，前端为 Next.js，基础依赖包含 PostgreSQL、Redis、MinIO 和 mock worker 进程；后端已提供用户隔离的人物 CRUD、`prompt_context` 输出、SourceMaterial 资料记录、AI Job 状态接口、本地 storage 兜底、deterministic mock Provider Gateway 解析、`ParsedChunk`/source-backed `MemoryCard` 生成、记忆审计 API、profile GET/PATCH/regenerate API、recalculate-trust API、conversation/message/citation/correct-memory/voice-message API、`POST /api/auth/demo` 本地演示会话 API、mock `chat_llm` Provider Gateway、voice config/default TTS/samples/clone/synthesize API、avatar config/default/generate API，以及 mock `tts`/`extract_voice_sample`/`voice_clone`/`avatar_3d` Provider Gateway；前端已接入中文首页、免注册演示入口、注册/登录表单、人物列表、四步创建人物、人物记忆空间页、资料上传页、任务状态页、记忆审计页、人格档案/可信度页、文本对话页（含 selected mock 3D 数字人与播放状态口型联动）、声音设置页、3D 形象设置页和本地 Pexels 视觉素材。本文只描述当前已存在的代码事实和验证入口；真实 OCR/ASR/VLM/模型质量、真实 LLM/embedding 检索质量、真实 GLB/3D provider 质量、故事/导出仍未实现。

## 文档地图

| 文档 | 主要用途 | 维护要求 |
| --- | --- | --- |
| [可信人格记忆Agent_mvp_prd.md](可信人格记忆Agent_mvp_prd.md) | 定义 MVP 范围、用户角色、核心流程、对象字段和验收标准。 | 产品范围变化时同步更新。 |
| [feature-list.json](feature-list.json) | 记录功能范围账本、状态、依赖和证据。 | 每次完成或启动功能切片时同步维护。 |
| [progress.md](progress.md) | 记录当前会话状态、活跃风险、验证证据和交接信息。 | 每次任务收尾前更新。 |
| [prd-checklist.md](prd-checklist.md) | 对齐 PRD 要求与代码事实，暴露差距和优先级。 | 行为或范围变化后同步核对。 |
| [平台说明.md](平台说明.md) | 面向首次用户说明准备、启动、操作流程和常见结果。 | 只写用户可执行步骤，不写未实现能力。 |
| [init.sh](init.sh) | 提供统一启动与验证入口。 | 运行 JSON、后端、前端和 Compose 配置检查；依赖未安装时按项跳过并提示。 |
| [../AGENTS.md](../AGENTS.md) | 约束 agent 的阅读顺序、编辑边界和验证要求。 | agent 工作规则变化时同步维护。 |

## Harness 分工

PRD 定义目标与边界；`feature-list.json` 和 `progress.md` 锁定当前范围、活跃风险和交接状态；`AGENTS.md` 约束 agent 怎么读、怎么改、怎么验证；`init.sh` 与本 README 验证命令提供统一启动和验收入口；`prd-checklist.md` 负责把产品要求与代码事实对齐；`平台说明.md` 把技术和产品约束翻译成首次用户可执行的操作说明。

## 当前状态

- 项目名称：可信人格记忆Agent
- 产品目标：按 PRD 聚焦可信人格记忆数字人；当前代码覆盖 Milestone 0 基础工程、Milestone 1 人物创建/记忆空间基础闭环、Milestone 2 资料上传/任务队列基础闭环、Milestone 3 mock 多模态解析/记忆审计基础闭环、Milestone 4 人格档案/可信度基础闭环、Milestone 5 第一人称文本对话基础闭环、Milestone 6 Task 1/2/3/4 后端默认 TTS、语音合成、音色样本、音色克隆兜底、语音消息 ASR 到 TTS、前端录音、声音设置和 mock 语音播放基础闭环、Milestone 7 Task 1/2/3 后端 3D 数字人配置/默认形象/mock 生成、前端 Three.js mock 预览和对话页播放状态口型联动基础闭环，以及全站温馨沉浸式「记忆空间」前端与免注册一键演示入口。
- 当前代码范围：FastAPI 后端基础、允许本地前端来源访问 API 的 CORS 配置、注册/登录接口、`POST /api/auth/demo` 本地演示会话接口、用户隔离的人物 CRUD、人物 `prompt_context` 输出、SourceMaterial 资料上传/手动创建/列表/详情/删除接口、AI Job 列表/详情/重试/取消接口、deterministic mock parsing、`ParsedChunk` 与 source-backed `MemoryCard` 生成、记忆列表/创建/详情/编辑/确认/拒绝/禁用/删除接口、`PersonaProfile` 聚合/读取/编辑/重生成接口、可信度重算接口、显式 `update_profile` 与 `calculate_trust_score` succeeded AI jobs、conversation/message/citation/correct-memory API、voice API、avatar config/default/generate API、mock `chat_llm` Provider Gateway、deterministic local retrieval、资料本地 storage 兜底、SQLAlchemy/Alembic 初始模型，后端容器启动前自动执行 Alembic 迁移，Next.js 前端中文首页、免注册演示入口、注册/登录表单、Dashboard 人物列表、四步创建人物、人物记忆空间页、资料上传页、任务状态页、记忆审计页、人格档案/可信度页、文本对话页、声音设置页、3D 形象设置页、Three.js mock 头像/半身预览、聊天页 selected mock 3D 数字人与播放状态口型联动、本地 Pexels 视觉素材和 `lucide-react` 图标，Docker Compose 开发拓扑和 mock worker 进程。
- 技术栈：Next.js 15、React 19、FastAPI、SQLAlchemy、Alembic、PostgreSQL/pgvector、Redis、MinIO、Docker Compose。
- 运行入口：`docker compose up --build` 可用于本地开发拓扑；`docs/init.sh` 是统一验证入口。
- 验收命令：见下方“启动与验证”。

## 启动与验证

### 依赖安装

后端测试依赖来自 `backend/requirements.txt`。当前 harness 不自动创建虚拟环境；请在本机 Python 环境中安装后再运行后端测试。

```powershell
python -m pip install -r backend/requirements.txt
```

前端依赖安装请在 PowerShell 使用：

```powershell
npm.cmd --prefix frontend install
```

### 单项验证

在仓库根目录运行：

```powershell
python -m json.tool docs/feature-list.json
python -m pytest backend/tests -q
npm.cmd --prefix frontend run test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
docker compose config
```

### 统一 harness

Windows Git Bash 入口：

```powershell
& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh
```

如果当前终端已经有可用 Bash，也可以运行：

```bash
bash ./docs/init.sh
```

`docs/init.sh` 执行以下检查：

- 确认必需 harness 文件存在。
- 校验 `docs/feature-list.json` 是合法 JSON。
- 如果后端 Python 依赖已安装，运行 `python -m pytest backend/tests -q`。
- 如果前端 `node_modules` 已安装，运行前端 `test`、`lint` 和 `build`。
- 如果 Docker Compose 可用，运行 `docker compose config`。

### 本地服务启动

```powershell
docker compose up --build
```

后端容器通过 `backend/docker-entrypoint.sh` 在启动 Uvicorn 前执行 `alembic upgrade head`，确保注册/登录 API 和人物 API 使用的表结构已应用到 Compose PostgreSQL。

默认开发地址：

- 前端：http://localhost:3000
- 后端健康检查：http://localhost:8000/health
- PostgreSQL 宿主机端口：localhost:15432（容器内仍为 `postgres:5432`；可用 `POSTGRES_HOST_PORT` 覆盖）
- MinIO API：http://localhost:9000
- MinIO Console：http://localhost:9001

Compose 文件只使用开发默认值和空白 provider 变量名，不包含真实密钥。真实密钥只应放在本地未提交环境中。

## 维护流程

1. 先读 `docs/README.md`、PRD、`feature-list.json`、`progress.md` 和根目录 `AGENTS.md`。
2. 明确本次任务对应的功能切片和验收标准。
3. 只修改与任务直接相关的文件。
4. 如果范围、验证命令、风险或交接状态变化，同步更新 `feature-list.json`、`progress.md`、`prd-checklist.md` 和必要的说明文档。
5. 收尾前运行 `docs/init.sh`，并记录额外验证证据。

## 残余风险与待补齐

- Task 2 原始页面未运行真实浏览器连接后端的烟测；本次中文体验已运行浏览器演示烟测，Milestone 7 头像设置页和聊天页数字人区域均已运行 1280x720 与 390x844 临时 mock API 浏览器烟测和 canvas 区域像素检查；其他 Milestone 2 上传/任务页、Milestone 3 记忆审计页、Milestone 4 人格档案/可信度页和 Milestone 6 voice 前端仍主要依赖自动化测试、前端 test/lint/build、Compose 配置校验和统一 harness。
- 本次已运行 `docker compose up --build -d` 服务级烟测并确认 backend healthy、frontend started；后续重启服务时仍需确认本机端口 3000、8000、15432（或 `POSTGRES_HOST_PORT` 指定端口）、6379、9000、9001 未被占用。
- 当前前端依赖树存在 2 个 moderate severity npm audit findings，尚未通过依赖升级处理。
- 全站温馨沉浸式前端使用下载到 `frontend/public/memory-space/` 的 Pexels 免费素材：elderly thoughtful Asian woman with tea、old pictures on photo album、family in living room、old pictures hung on string light；素材来源 URL 记录在 `frontend/src/lib/memory-space.ts` 并由 `frontend/tests/memory-space.test.mjs` 覆盖。
- 当前材料解析、OCR、ASR、图片理解、视频分析、记忆抽取和文本 chat 只使用 deterministic mock Provider Gateway/local retrieval 输出，不代表真实模型质量；当前人格档案聚合和可信度计算为 deterministic local 规则，不代表真实 LLM profile quality；真实 AI Provider、对象存储桶初始化和生产密钥管理仍待后续任务确认。
- Milestone 7 目前完成后端 avatar config/default/generate/mock fallback API、前端 Three.js mock 头像/半身预览和聊天页 selected mock 数字人播放状态口型联动；真实 GLB 加载、真实音频音量包络/viseme 口型同步、真实 3D provider 质量、故事/导出和真实 LLM/embedding 检索质量仍未实现。
