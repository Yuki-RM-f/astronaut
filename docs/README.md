# 可信人格记忆Agent Docs Harness

本目录提供项目的 docs-driven harness。它用于把目标、范围、实现事实、验证入口和 agent 交接规则放在同一套文档约束中，避免后续开发在没有上下文的情况下扩大范围或重复判断。

当前仓库已完成 Milestone 0 基础工程、Milestone 1 人物创建/记忆空间基础闭环、Milestone 2 资料上传/任务队列基础闭环、Milestone 3 mock 多模态解析/记忆审计基础闭环、Milestone 4 人格档案/可信度基础闭环、Milestone 5 第一人称文本对话基础闭环，Milestone 6 Task 1/2/3/4 后端默认 TTS、语音合成、音色样本、音色克隆兜底、语音消息 ASR 到 TTS、前端录音、声音设置和 mock 语音播放基础闭环，Milestone 7 Task 1/2/3 后端 3D 数字人配置、默认形象、mock 生成、前端 Three.js mock 预览、对话页 3D 数字人展示和播放状态口型联动基础闭环，并已接入 Milestone 8 后端回忆讲述、来源追溯、故事导出、mock WAV 音频文件导出、档案/记忆/对话 JSON 导出、人物删除级联软删除、单条对话软删除、清空当前账号数据和模型设置后端运行配置 API。当前前端以 `origin/yawen` 的星空交互为准，并已把 `/personas/{id}/memories` 升级为星空主题“记忆解析与审核”：保留人物列表、星空创建页、人物详情、资料上传、任务、分类记忆审核、审计仪表盘、语义搜索、冲突中心、记忆历史、人格档案、对话、声音和 3D 页面交互；对话页按参考图形成左侧三模式对话、右侧 `AvatarStage` 数字人舞台，形象页生成或选择 avatar 后可替换右侧占位；审核页按参考图形成可信度横幅、6 个维度卡片和底部完成审核 CTA。不再展示登录/注册、登录态差异、数据设置页、模型设置页或独立回忆讲述页。前端无 token 时通过现有 `POST /api/auth/demo` 自动获得 demo token，已有 token 会静默复用；后端注册/登录、导出/删除、provider settings 和 stories API 均保留不变。创建星星页继续提交后端必需的 `age`、`language=zh-CN`、默认说话风格、情绪边界和禁用表达，并在创建成功后用现有资料上传 API 上传已选文件。yawen 未闭环的视频手势互动、遗憾对话室和心愿延续只作为前端模式或 prompt 入口，不声明真实后端能力。本文只描述当前已存在的代码事实和验证入口；真实解析质量依赖本地 `DASHSCOPE_API_KEY` 和已开通模型，真实 Chat/Story LLM、Persona Engine 显式画像分析、TTS/音色调用依赖本地 MiniMax/OpenAI-compatible 配置、模型权限、账号实名/企业认证和样本质量；真实 GLB/3D provider、真实 MinIO/S3 对象删除和生产级 secret manager 仍未实现。

补充：embedding 运行入口已停用并移除；历史数据库 embedding 列和 Alembic `0004` 保留以兼容旧库。当前对话上下文链路为“LLM/规则抽取结构化记忆 -> 已确认/已修正记忆生成长期 Markdown -> 人物维度短期对话 Markdown -> Chat 直接读取 Markdown”。Markdown 过长时通过 `memory_context_compression` 压缩，失败时用确定性截断兜底，不阻断聊天。

## 文档地图

| 文档 | 主要用途 | 维护要求 |
| --- | --- | --- |
| [可信人格记忆Agent_mvp_prd.md](可信人格记忆Agent_mvp_prd.md) | 定义 MVP 范围、用户角色、核心流程、对象字段和验收标准。 | 产品范围变化时同步更新。 |
| [feature-list.json](feature-list.json) | 记录功能范围账本、状态、依赖和证据。 | 每次完成或启动功能切片时同步维护。 |
| [progress.md](progress.md) | 记录当前会话状态、活跃风险、验证证据和交接信息。 | 每次任务收尾前更新。 |
| [prd-checklist.md](prd-checklist.md) | 对齐 PRD 要求与代码事实，暴露差距和优先级。 | 行为或范围变化后同步核对。 |
| [平台说明.md](平台说明.md) | 面向首次用户说明准备、启动、操作流程和常见结果。 | 只写用户可执行步骤，不写未实现能力。 |
| [Persona_Engine_System_Prompt.md](Persona_Engine_System_Prompt.md) | 归档 Persona Engine 人格分析器 system prompt。 | 只用于结构化人格画像分析，不作为聊天 prompt。 |
| [展览路演材料.html](展览路演材料.html) | 中文路演演示 HTML 静态资料。 | 作为 docs 可查看材料，不作为产品路由。 |
| [init.sh](init.sh) | 提供完整启动与验证入口。 | 运行 JSON、后端、前端和 Compose 配置检查；依赖未安装时按项跳过并提示；仅在用户明确要求时运行。 |
| [../AGENTS.md](../AGENTS.md) | 约束 agent 的阅读顺序、编辑边界和验证要求。 | agent 工作规则变化时同步维护。 |

## Harness 分工

PRD 定义目标与边界；`feature-list.json` 和 `progress.md` 锁定当前范围、活跃风险和交接状态；`AGENTS.md` 约束 agent 怎么读、怎么改、怎么验证；`init.sh` 与本 README 验证命令提供完整启动和验收入口；`prd-checklist.md` 负责把产品要求与代码事实对齐；`平台说明.md` 把技术和产品约束翻译成首次用户可执行的操作说明。

## 当前状态

- 项目名称：可信人格记忆Agent
- 产品目标：按 PRD 聚焦可信人格记忆数字人；当前后端能力保持 Milestone 0-8、provider settings、长期/短期记忆 Markdown、age 必填和真实 provider adapter 的既有范围；当前前端已迁移为 yawen 星空视觉和交互，不再展示登录/注册、登录态差异、数据设置页、模型设置页或独立回忆讲述页。
- 当前代码范围：FastAPI 后端基础、允许本地前端来源访问 API 的 CORS 配置、注册/登录接口、`POST /api/auth/demo` 本地演示会话接口、用户隔离的人物 CRUD、创建人物 age 必填、语言固定中文和默认风格边界基础闭环、删除人物时级联软删除 PRD 关联记录、单条对话软删除、清空当前账号数据、`GET/PUT /api/settings/providers` 模型运行配置 API、人物 `prompt_context` 输出、SourceMaterial 资料上传/手动创建/列表/详情/删除接口、AI Job 列表/详情/重试/取消接口、deterministic mock parsing、DashScope 真实解析 adapter、MiniMax 真实 TTS/音色克隆/文本 Chat/Story/记忆上下文压缩/Persona Engine 显式画像分析 adapter、`ParsedChunk` 与 source-backed `MemoryCard` 生成、Memory Audit v2 审计日志/冲突/语义搜索/历史 API、长期/短期记忆 Markdown、profile/trust、conversation/chat/voice/avatar/stories/export API、SQLAlchemy/Alembic 模型和迁移；Next.js 前端提供星空首页、无登录态差异的 Dashboard、创建星星页、人物详情、资料上传、任务、记忆解析与审核页、人格档案、文本/模式对话、声音设置、3D 形象设置和共享 `AvatarStage` 数字人舞台，创建页透明调用 demo session 并在创建后上传已选资料。
- 技术栈：Next.js 15、React 19、FastAPI、SQLAlchemy、Alembic、PostgreSQL、Redis、MinIO、Docker Compose。
- 运行入口：`docker compose up --build` 可用于本地开发拓扑；`docs/init.sh` 是仅在用户明确要求时运行的完整基线验证入口，agent 不主动运行。
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

`docs/init.sh` 只在用户明确要求完整基线验证时运行。agent 不要因为收尾、发布/合并前、变更启动/验证链路、改动较大或需要完整基线证据而主动运行它；其他场景优先运行与改动直接相关的单项验证并记录证据。

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

Compose 文件不包含真实密钥。真实密钥只应放在本地未提交环境中。

### 真实 Provider 配置

默认 `DEFAULT_LLM_PROVIDER=mock`，不会调用第三方 API。需要真实解析时，将本地未提交的 `.env/runtime.env` 或系统环境变量设置为：

Docker Compose 的 backend 和 worker 服务会在本地存在 `.env/runtime.env` 时自动加载该文件；该文件已被 `.gitignore` 排除，不要提交真实密钥。

```env
DEFAULT_LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=
DASHSCOPE_REGION=cn-beijing
DASHSCOPE_WORKSPACE_ID=
DASHSCOPE_BASE_URL=https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1
DASHSCOPE_COMPAT_BASE_URL=https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
QWEN_TEXT_MODEL=qwen-plus
QWEN_VISION_MODEL=qwen3.7-plus
QWEN_OCR_MODEL=qwen-vl-ocr-latest
QWEN_ASR_MODEL=qwen3-asr-flash
TRIPO_API_KEY=
TRIPO_BASE_URL=https://api.tripo3d.ai
MINIMAX_API_KEY=
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
MINIMAX_TTS_MODEL=speech-2.8-hd
MINIMAX_CLONE_MODEL=speech-2.8-hd
MINIMAX_DEFAULT_VOICE_ID=male-qn-qingse
```

当前真实/本地 provider 接入覆盖四类链路：材料解析链路的 `text_parser`、`ocr`、`image_understanding`、`asr`、`video_understanding` 和 `memory_extraction` 可走 DashScope；文本生成链路的 `chat_llm`、`story_generation`、`memory_context_compression` 和 `persona_profile_analysis` 可走 MiniMax OpenAI-compatible `/chat/completions`；语音链路的 `tts` 与 `voice_clone` 可走 MiniMax。未配置对应 API Key 或模型名时自动回到 mock/确定性路径；已配置后第三方请求失败会把对应 job 标记为 `failed` 并记录错误，记忆上下文压缩失败则回退确定性截断，不阻断聊天；Persona Engine 解析失败时 profile regenerate 回退 deterministic profile 并在 job 中记录 fallback。`extract_voice_sample` 和 3D 生成仍沿用现有 mock/本地逻辑。

### 真实多模态公网样本烟测

真实 DashScope 解析烟测不属于 `docs/init.sh` 完整基线验证，因为它会下载公网样本并调用付费第三方模型。确认后端已通过 `docker compose up --build -d backend` 启动，且 `.env/runtime.env` 或系统环境变量已配置 `DEFAULT_LLM_PROVIDER=dashscope` 和有效 DashScope key 后，可手动运行：

```powershell
python backend/scripts/real_multimodal_smoke.py --sample-mode public --backend-url http://localhost:8000
```

脚本会下载 Project Gutenberg 文本、Wikimedia Commons 图片、LibriVox/Internet Archive 公版音频和 Wikimedia/USGS 视频到 `.smoke/real-multimodal/`，从公版文本派生 PDF/DOCX/DOC，使用 ffmpeg 或本地 backend Docker 镜像裁剪视频，并通过真实上传 API 验证 DashScope provider、parse job、ParsedChunk id 和 source-backed MemoryCard。结果写入 `.smoke/real-multimodal/results/*.json`，不写入或输出原始密钥。

## 维护流程

1. 先读 `docs/README.md`、PRD、`feature-list.json`、`progress.md` 和根目录 `AGENTS.md`。
2. 明确本次任务对应的功能切片和验收标准。
3. 只修改与任务直接相关的文件。
4. 如果范围、验证命令、风险或交接状态变化，同步更新 `feature-list.json`、`progress.md`、`prd-checklist.md` 和必要的说明文档。
5. 收尾前按改动范围运行最小必要验证并记录证据；不要主动运行 `docs/init.sh`，除非用户明确要求完整基线验证。

## 残余风险与待补齐

- 当前 yawen 星空前端已通过前端 test/lint/build 做基础回归；浏览器 smoke 已覆盖对话页三模式、默认星空占位、形象页选择默认形象后对话页数字人 canvas 非空、记忆解析与审核页可信度横幅/6 维卡片/底部 CTA，以及桌面和移动无横向溢出。独立 `/settings/data`、`/settings/providers` 和 `/personas/{id}/stories` 页面已不再作为当前前端入口；对应后端 API 保留。
- 本次已运行 `docker compose up --build -d` 服务级烟测并确认 backend healthy、frontend started；后续重启服务时仍需确认本机端口 3000、8000、15432（或 `POSTGRES_HOST_PORT` 指定端口）、6379、9000、9001 未被占用。
- 当前前端依赖树存在 2 个 moderate severity npm audit findings，尚未通过依赖升级处理。
- 全站温馨沉浸式前端使用下载到 `frontend/public/memory-space/` 的 Pexels 免费素材：elderly thoughtful Asian woman with tea、old pictures on photo album、family in living room、old pictures hung on string light；素材来源 URL 记录在 `frontend/src/lib/memory-space.ts` 并由 `frontend/tests/memory-space.test.mjs` 覆盖。
- 当前材料解析、OCR、ASR、图片理解、视频分析和记忆抽取已可在配置 `DASHSCOPE_API_KEY` 后走 DashScope；公网样本烟测脚本已接入并在 2026-07-04 复跑通过，文本、图片、音频、视频、PDF、DOCX 和 DOC 均经真实上传 API 生成 DashScope third_party parse job、ParsedChunk 和 source-backed MemoryCard，结果记录在 `.smoke/real-multimodal/results/20260704-170719.json`。文本 chat、story generation、memory context compression、Persona Engine profile analysis、TTS 和音色克隆已可在配置 MiniMax key/base URL 与 `OPENAI_MODEL` 后走 MiniMax；默认未配置时仍使用 deterministic mock Provider Gateway 或 local fallback。文本 Chat/Story 已完成真实 MiniMax 调用烟测，Persona Engine 仅在显式 profile regenerate 时调用，长期人格质量和更大样本评测仍待后续验收；音色样本提取和 3D 生成仍为 mock/本地规则；当前自动记忆审核刷新仍使用 deterministic local profile/trust，不触发真实 LLM 成本；对象存储桶初始化、生产密钥管理和真实 3D provider 仍待后续任务确认，MiniMax 音色克隆质量还取决于账号实名/企业认证和样本音频质量。
- Milestone 7 已完成后端 avatar config/default/generate/mock fallback API、前端 Three.js mock 头像/半身预览和聊天页 selected mock 数字人播放状态口型联动；Milestone 8 后端故事、导出、删除和清空账号数据 API 保留；当前前端把回忆讲述、遗憾对话室和心愿延续整合为对话页模式/入口，不声明独立后端能力。真实 GLB 加载、真实音频音量包络/viseme 口型同步、真实 3D provider 质量、真实 MinIO/S3 对象删除、生产级 secret manager 和真实 LLM 长期质量仍待验收或后续实现。
- P1 创建人物资料卡片 `age` 必填已完成基础闭环；根据当前用户指令，自定义人格档案维度、AI 主动关怀、心愿延续系统及其他 P1/P2 功能点暂缓开发，已完成功能点保留。
