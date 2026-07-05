# 可信人格记忆Agent Docs Harness

本目录提供项目的 docs-driven harness。它用于把目标、范围、实现事实、验证入口和 agent 交接规则放在同一套文档约束中，避免后续开发在没有上下文的情况下扩大范围或重复判断。

当前仓库已完成 Milestone 0 基础工程、Milestone 1 人物创建/记忆空间基础闭环、Milestone 2 资料上传/任务队列基础闭环、Milestone 3 mock 多模态解析/记忆审计基础闭环、Milestone 4 人格档案/可信度基础闭环、Milestone 5 第一人称文本对话基础闭环，Milestone 6 Task 1/2/3/4 后端默认 TTS、语音合成、音色样本、音色克隆兜底、语音消息 ASR 到 TTS、前端录音、声音设置和 mock 语音播放基础闭环，Milestone 7 Task 1/2/3 后端 3D 数字人配置、默认形象、mock 生成、前端 Three.js mock 预览、对话页 3D 数字人展示和播放状态口型联动基础闭环，并已接入 Milestone 8 后端回忆讲述、来源追溯、故事导出、mock WAV 音频文件导出、档案/记忆/对话 JSON 导出、人物删除级联软删除、单条对话软删除、清空当前账号数据和模型设置后端运行配置 API。当前前端以 `origin/yawen` 的星空交互为准，并已把 `/personas/{id}/memories` 升级为星空主题“记忆档案馆”：顶部导航固定为“首页 / 产品介绍 / 创建档案 / 我的星空”，人物详情页保留下方资料、记忆和互动功能卡片作为人物内功能入口；各人物内功能页不再展示“人物工作台”导航块、分组按钮或返回人物工作台按钮。当前保留人物列表、星空创建页、人物详情、资料解析与审核、任务、记忆档案馆、自动档案摘要展示、文本/手势/语音对话、遗憾对话室、心愿延续引导、声音和 3D 页面交互；声音页默认 TTS 支持从 MiniMax 中文普通话真人相关 system voices 静态列表选择具体 `voice_id`，选项名称使用中文，音色样本可通过本页上传或浏览器录制纯净无噪声的 TA 人声音频创建，浏览器录音停止后会先转为 WAV 再作为提交样本，前端会按 MiniMax 克隆要求拦截少于 10 秒的样本，并保留“创建音色样本”和“生成模拟音色”两个独立步骤。独立 `/personas/{id}/profile` 人格档案页面 UI 不再保留，深链访问会重定向到 uploads。对话页收口为三模式对话和共享 `AvatarStage` 数字人舞台，形象页上传 GLB 后可替换星空占位；记忆档案馆只承接回忆讲述和语义搜索，进入页面会通过后端 seed 接口幂等补足最多三段锚定真实已审核记忆的默认故事，用户点击“让TA讲一段回忆”会按关键词追加新故事；story/search 都会读取长期/短期记忆 Markdown 辅助主题检索，story 输出会在入库、列表、导出和 TTS 前清洗模型思考块，语义搜索仍只返回可追溯 MemoryCard；遗憾对话室和心愿延续引导分别为独立前端页。不再展示登录/注册、登录态差异、数据设置页、模型设置页或独立 `/personas/{id}/stories` 页面。前端无 token 时通过现有 `POST /api/auth/demo` 自动获得 demo token，已有 token 会静默复用；后端注册/登录、profile、导出/删除、provider settings 和 stories API 均保留不变。创建星星页继续提交后端必需的 `age`、`language=zh-CN`、默认说话风格、情绪边界和禁用表达，并在创建成功后用现有资料上传 API 上传已选文件；创建页内部展示“资料卡片 -> 上传回忆 -> 保存并进入审核”流程步骤。视频手势互动已接入浏览器本地摄像头识别和 GLB 动作反馈：摄像头画面只在前端本地用于识别停留、挥手、张开手掌和握拳，不上传后端或持久化；遗憾对话室继续作为 guided chat 轻量引导，心愿延续引导使用 `context_kind=wishes` 专用 conversation 和心愿 system prompt，不读取普通聊天、遗憾对话等其他对话短期上下文，但仍不声明独立后端心愿数据模型、提醒策略或长期 P1 心愿系统。本文只描述当前已存在的代码事实和验证入口；真实解析质量依赖本地 `DASHSCOPE_API_KEY` 和已开通模型，真实 Chat/Story LLM、Persona Engine 显式画像分析、TTS/音色调用依赖本地 MiniMax/OpenAI-compatible 配置、模型权限、账号实名/企业认证和样本质量；真实 3D provider、真实 MinIO/S3 对象删除和生产级 secret manager 仍未实现。

补充：2026-07-05 星空前端 UX 打磨后，旧的大块人物工作台导航和后续紧凑人物工具栏均不再展示；人物详情页下方功能卡片作为资料、记忆和互动入口，人物子页仅保留单一“返回人物总览”入口，不提供子页快速切换栏。`StarNav` 支持当前路由高亮和移动端单行菜单；`/personas/{id}/stories` 作为兼容深链重定向到 `/personas/{id}/memories`，不恢复独立 stories 产品入口。主对话、遗憾和心愿页面共用内部滚动的对话工作区，输入栏保持在面板底部，避免发送后页面自动滚走；数字人舞台始终可见，窄屏按“上方对话框、下方数字人”堆叠，`xl` 宽屏按左右双栏等高展示。

补充：embedding 运行入口已停用并移除；历史数据库 embedding 列和 Alembic `0004` 保留以兼容旧库。当前普通对话上下文链路为“LLM/规则抽取结构化记忆 -> 已确认/已修正记忆生成长期 Markdown -> kind 维度短期对话 Markdown -> Chat 直接读取 Markdown”。`Conversation.kind` 支持 `chat`、`regrets` 和 `wishes`；普通聊天写入 `short_term_memory.md`，遗憾对话室写入 `short_term_memory_regrets.md` 并保留长期已确认记忆，心愿延续引导使用独立 `wishes` conversation/context。Markdown 过长时通过 `memory_context_compression` 压缩，失败时用确定性截断兜底，不阻断聊天。`kind=regrets` 的遗憾对话室使用“有没有什么以前没说的话，今天想慢慢告诉我？”专用 system prompt，只读取同类 regrets 短期上下文，不读取普通聊天短期消息；`context_kind=wishes` 的心愿延续对话只使用当前心愿 conversation 历史、人物基础信息和专用 system prompt，不读取人物维度短期 Markdown 或默认记忆召回；该 prompt 围绕“你现在有什么想完成的心愿，或者想替我继续做的一件事吗？”引导用户聚焦心愿、替 TA 继续做的一件事和下一步行动。

当前 GLB 形象流程补充：`/personas/{id}/avatar` 已从默认形象、图片生成和口型测试收口为单一 GLB 上传流程。后端提供 `POST /api/personas/{id}/avatar/upload` 保存自包含 `.glb` 为当前 selected `AvatarModel`，状态为 `uploaded_ready`；`GET /api/avatar-models/{id}/file` 按 JWT 用户隔离返回 `model/gltf-binary` 文件；Compose 后端把 `/app/storage/avatar_models` 挂到 `avatar-model-storage`，避免开发容器重建后丢失已上传 GLB 文件。前端 `AvatarPreview`/`AvatarStage` 使用 GLTFLoader + MeshoptDecoder 加载同一模型文件，并通过 Three.js `AnimationMixer` 优先播放模型自带动作 clip；缺少匹配 clip 时使用整体转身、点头、轻摆、靠近等基础动作 fallback。形象页、对话页、遗憾对话室和心愿延续页共享 GLB 展示；对话页视频手势模式可用浏览器本地摄像头识别触发动作反馈。旧 default/generate API 仅保留兼容；当前仍不处理真实 audio envelope 或 viseme 口型同步，也不声明真实 3D 生成 provider 质量。

当前职责边界补充：资料解析结果审查已从 `/personas/{id}/memories` 迁到 `/personas/{id}/uploads`。创建星星成功后进入 uploads；uploads 同页承接资料上传、由当前 active `MemoryCard` 渲染的结构化记忆 Markdown、分类记忆卡片确认/编辑/删除/星标、可选自定义维度、唯一“记忆可信度”和“完成审核，点亮星星”，不再提供手动档案摘要编辑；上传文件或手动资料提交后立即创建 `SourceMaterial + AIJob(pending)` 并返回，后台解析完成前页面轮询 materials/memories/profile 展示进度，已有资料卡片只展示真正资料解析 failed job 错误，不展示结构化文档 provider 技术诊断。四类资料的识别结果先统一写入 `ParsedChunk.content`，再进入严格六模块 JSON `memory_extraction`；后端校验 `structured_memory_json` 后先派生待审核记忆卡片，再从当前 active MemoryCard 确定性生成全人物 `structured_memory_document_json` 和 `structured_memory_md`。`memory_document_generation` 只负责基于当前资料、解析块和记忆卡片输出 `profile_summary`、trust、rationale 和 suggestions，不再补造结构化文档条目。上传区不再暴露资料级备注或重要程度，重要性由用户在真实 `MemoryCard` 上点星标持久化，并进入结构化记忆文档、长期 Markdown、story 和 chat 上下文。`/personas/{id}/memories` 只保留回忆讲述和语义搜索，不再展示审核卡片、可信度、健康分、待审核、开放冲突、冲突中心或最近事件/历史。回忆讲述进入页面时先由 `POST /api/personas/{id}/stories/seed` 幂等补足最多三段默认故事，每段锚定一条 confirmed/corrected 且未删除的真实 MemoryCard；用户输入主题后仍以该主题作为检索关键词读取长期/短期记忆 Markdown 追加新故事，只允许 confirmed/corrected 且未删除的 MemoryCard 成为故事来源，并在写入故事、列表返回、导出文本和 TTS 输入前统一清洗模型 `<think>` 或思考文本；语义搜索读取长期/短期记忆辅助排序，但结果仍只展示可追溯 MemoryCard、来源摘录和来源位置，不把短期对话片段作为独立结果。`/personas/{id}/profile` 不再渲染独立人格档案 UI，深链访问重定向到 uploads；后端 profile API 和前端 profile helper 仍保留供人物详情、chat 和兼容调用使用。人物详情页顶部简介读取最近一次上传解析链路自动生成的 `profile.profile_summary`，没有摘要时显示中性空态，不再展示创建人物时填写的 `short_bio`。`persona.trust_score` 只由资料解析后的 `memory_document_generation` 后端链路或兼容的 `POST /recalculate-trust` 更新；profile GET、记忆确认/编辑/删除和 profile 重生成只刷新档案维度/长期 Markdown，不覆盖 trust 或自动摘要。Dashboard、人物详情、profile 和 memories 页面不展示 trust 数字或可信度组成。

## 文档地图

| 文档 | 主要用途 | 维护要求 |
| --- | --- | --- |
| [可信人格记忆Agent_mvp_prd.md](可信人格记忆Agent_mvp_prd.md) | 定义 MVP 范围、用户角色、核心流程、对象字段和验收标准。 | 产品范围变化时同步更新。 |
| [feature-list.json](feature-list.json) | 记录功能范围账本、状态、依赖和证据。 | 每次完成或启动功能切片时同步维护。 |
| [progress.md](progress.md) | 记录当前会话状态、活跃风险、验证证据和交接信息。 | 每次任务收尾前更新。 |
| [prd-checklist.md](prd-checklist.md) | 对齐 PRD 要求与代码事实，暴露差距和优先级。 | 行为或范围变化后同步核对。 |
| [平台说明.md](平台说明.md) | 面向首次用户说明准备、启动、操作流程和常见结果。 | 只写用户可执行步骤，不写未实现能力。 |
| [Persona_Engine_System_Prompt.md](Persona_Engine_System_Prompt.md) | 归档 Persona Engine 人格分析器 system prompt。 | 只用于结构化人格画像分析，不作为聊天 prompt。 |
| [展览路演材料.html](展览路演材料.html) | 中文路演演示 HTML 静态资料。 | 作为 docs 静态源材料；`/product-intro` 使用精选摘编，不直接嵌入原始 HTML。 |
| [init.sh](init.sh) | 提供完整启动与验证入口。 | 运行 JSON、后端、前端和 Compose 配置检查；依赖未安装时按项跳过并提示；仅在用户明确要求时运行。 |
| [../AGENTS.md](../AGENTS.md) | 约束 agent 的阅读顺序、编辑边界和验证要求。 | agent 工作规则变化时同步维护。 |

## Harness 分工

PRD 定义目标与边界；`feature-list.json` 和 `progress.md` 锁定当前范围、活跃风险和交接状态；`AGENTS.md` 约束 agent 怎么读、怎么改、怎么验证；`init.sh` 与本 README 验证命令提供完整启动和验收入口；`prd-checklist.md` 负责把产品要求与代码事实对齐；`平台说明.md` 把技术和产品约束翻译成首次用户可执行的操作说明。

## 当前状态

- 项目名称：可信人格记忆Agent
- 产品目标：按 PRD 聚焦可信人格记忆数字人；当前后端能力保持 Milestone 0-8、provider settings、长期/短期记忆 Markdown、age 必填和真实 provider adapter 的既有范围；当前前端已迁移为 yawen 星空视觉和交互，不再展示登录/注册、登录态差异、数据设置页、模型设置页或独立 `/personas/{id}/stories` 页面。
- 当前代码范围：FastAPI 后端基础、允许本地前端来源访问 API 的 CORS 配置、注册/登录接口、`POST /api/auth/demo` 本地演示会话接口、用户隔离的人物 CRUD、创建人物 age 必填、语言固定中文和默认风格边界基础闭环、删除人物时级联软删除 PRD 关联记录、单条对话软删除、清空当前账号数据、`GET/PUT /api/settings/providers` 模型运行配置 API、人物 `prompt_context` 输出、SourceMaterial 资料上传/手动创建/列表/详情/删除接口、AI Job 列表/详情/重试/取消接口、deterministic mock parsing、DashScope 真实解析 adapter、MiniMax 真实 TTS/音色克隆/默认 TTS system `voice_id` 选择/文本 Chat/Story/记忆上下文压缩/Persona Engine 显式画像分析 adapter、`ParsedChunk` 与 source-backed `MemoryCard` 生成、Memory Audit v2 审计日志/冲突/语义搜索/历史 API、长期/短期记忆 Markdown、profile/trust、conversation `kind/context_kind`、chat/voice/avatar/stories/export API、SQLAlchemy/Alembic 模型和迁移；Next.js 前端提供星空首页、无登录态差异的 Dashboard、Dashboard 星星卡确认删除入口、创建星星页、人物总览页下方功能卡片、资料解析与审核、任务、记忆档案馆、uploads 内自动档案摘要来源/可信度/记忆星标审核、文本/手势/语音对话、遗憾对话室、心愿延续引导、声音设置、3D 形象设置和共享 `AvatarStage` 数字人舞台，创建页透明调用 demo session 并在创建后上传已选资料；`/personas/{id}/profile` 仅保留为重定向到 uploads 的兼容深链。
- 当前前端 UX 补充：顶部星空导航支持当前路由高亮和移动端紧凑菜单；人物总览和人物子页不再展示统一人物工具栏，人物详情页下方功能卡片作为内部入口，人物子页保留单一返回人物总览入口；创建页移动端保存区固定在底部；对话类页面使用内部消息滚动和固定输入栏，数字人舞台不再折叠，窄屏上下堆叠、`xl` 宽屏左右等高展示；记忆档案馆故事卡片支持收藏和来源折叠；旧 `/personas/{id}/stories` 深链重定向到 memories。
- 当前产品介绍入口：顶部导航 `产品介绍` 指向独立 `/product-intro` 星空路演摘编页；首页仍保留简版 `#product-intro` 三卡概览，用于还原星空首页原有布局。
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
- PostgreSQL 宿主机端口：127.0.0.1:15432（容器内仍为 `postgres:5432`；可用 `POSTGRES_HOST_PORT` 覆盖）
- Redis 宿主机端口：127.0.0.1:6379
- MinIO API：http://127.0.0.1:9000
- MinIO Console：http://127.0.0.1:9001

Compose 文件不包含真实密钥。真实密钥只应放在本地未提交环境中。

### ECS 直连端口部署

当前云服务器方案不引入 Nginx、域名或 HTTPS，直接使用 Compose 暴露前端 `3000` 和后端 `8000`。部署时把 `<ECS公网IP>` 替换为阿里云 ECS 实际公网 IPv4，不要保留尖括号。

在 ECS 仓库根目录创建未提交的 `.env/runtime.env`：

```env
FRONTEND_URL=http://<ECS公网IP>:3000
BACKEND_URL=http://<ECS公网IP>:8000
NEXT_PUBLIC_API_BASE_URL=http://<ECS公网IP>:8000
JWT_SECRET=<生成强随机字符串>
```

`NEXT_PUBLIC_API_BASE_URL` 会在 Docker build 期写入 Next.js 客户端包；如果修改公网 IP 或后端端口，必须重新执行带 `--build` 的 Compose 命令。

阿里云 ECS 安全组只需要放行入站 TCP `3000` 和 `8000`。不要对公网放行 `15432`、`6379`、`9000` 或 `9001`；当前 Compose 默认把 PostgreSQL、Redis 和 MinIO 的宿主端口绑定到 `127.0.0.1`。

```bash
docker compose --env-file .env/runtime.env up --build -d
```

远程访问地址：

- 网页：`http://<ECS公网IP>:3000`
- 后端健康检查：`http://<ECS公网IP>:8000/health`

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
DASHSCOPE_REQUEST_TIMEOUT_SECONDS=180
TRIPO_API_KEY=
TRIPO_BASE_URL=https://api.tripo3d.ai
MINIMAX_API_KEY=
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
MINIMAX_TTS_MODEL=speech-2.8-hd
MINIMAX_CLONE_MODEL=speech-2.8-hd
MINIMAX_DEFAULT_VOICE_ID=male-qn-qingse
OPENAI_NEXT_API_KEY=
OPENAI_NEXT_BASE_URL=https://api.openai-next.com/v1
OPENAI_NEXT_MODEL=gpt-5
OPENAI_NEXT_REQUEST_TIMEOUT_SECONDS=60
```

当前真实/本地 provider 接入覆盖四类链路：材料解析链路的 `text_parser`、`ocr`、`image_understanding`、`asr`、`video_understanding` 和严格六模块 JSON `memory_extraction` 可走 DashScope；DashScope 请求默认超时为 180 秒，可用 `DASHSCOPE_REQUEST_TIMEOUT_SECONDS` 覆盖。文本生成链路的 `chat_llm`、`story_generation`、`memory_context_compression`、`persona_profile_analysis` 和 `memory_document_generation` 可走 MiniMax OpenAI-compatible `/chat/completions`；当 MiniMax 文本生成失败且 `OPENAI_NEXT_API_KEY`、`OPENAI_NEXT_BASE_URL` 与 `OPENAI_NEXT_MODEL` 配置齐全时，Provider Gateway 会仅对这些文本 capability 追加一次 OpenAI-Next `/chat/completions` 兜底，并在 metadata 记录 `provider_name=openai_next`、`fallback_from_provider=minimax` 和脱敏失败原因。OpenAI-Next 不用于 TTS、音色克隆、ASR、OCR、图片/视频理解或记忆抽取。`memory_document_generation` 使用 JSON object 响应约束，但模型只输出 `profile_summary`、trust、rationale 和 suggestions；`structured_memory_document_json` 与 `structured_memory_md` 由后端 service 层从当前 active `MemoryCard` 确定性渲染，避免文档和审核卡片出现第二套事实源。语音链路的 `tts` 与 `voice_clone` 可走 MiniMax。声音页默认 TTS 先使用内置 MiniMax 中文普通话真人相关 system voices 静态列表，选择后把 `voice_id` 保存到当前人物的 `VoiceModel.model_artifact_url`，后续语音合成优先使用该 `voice_id`；`MINIMAX_DEFAULT_VOICE_ID` 仍作为没有 selected voice model 时的 provider fallback。音色克隆样本遵守 MiniMax 至少 10 秒要求：前端创建样本前检查音频时长，后端 clone 前会对可读 WAV 做短音频预检，失败时写入 `voice_preflight` failed job 并回退默认 TTS。本轮不接入动态 `POST /v1/get_voice`。未配置对应 API Key 或模型名时自动回到 mock/确定性路径；已配置后第三方请求失败会把对应 job 标记为 `failed` 并记录错误；如果资料已生成 `ParsedChunk` 与 `MemoryCard`，即使 MiniMax/OpenAI-Next 摘要/可信度输出不可用，后端也会保留记忆卡片和确定性结构化文档，并把 provider 诊断仅保存在 job metadata，不在 uploads 资料卡片展示。记忆上下文压缩失败则回退确定性截断，不阻断聊天；Persona Engine 解析失败时 profile regenerate 回退 deterministic profile 并在 job 中记录 fallback。`extract_voice_sample` 和 3D 生成仍沿用现有 mock/本地逻辑。

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

- 当前 yawen 星空前端已通过前端 test/lint/build 做基础回归；浏览器 smoke 已覆盖对话页三模式、侧边数字人、移除故事面板和三功能卡片、记忆档案馆回忆讲述区与语义搜索区、遗憾对话室和心愿延续引导页，以及桌面和移动无横向溢出。独立 `/settings/data`、`/settings/providers` 和 `/personas/{id}/stories` 页面已不再作为当前前端入口；对应后端 API 保留。
- 既有服务级烟测已运行 `docker compose up --build -d` 并确认 backend healthy、frontend started；后续本地重启服务时仍需确认本机端口 3000、8000 未被占用。PostgreSQL、Redis 和 MinIO 宿主端口默认仅绑定到 `127.0.0.1`，ECS 对外只放行 3000/8000。
- 当前前端依赖树存在 2 个 moderate severity npm audit findings，尚未通过依赖升级处理。
- 全站温馨沉浸式前端使用下载到 `frontend/public/memory-space/` 的 Pexels 免费素材：elderly thoughtful Asian woman with tea、old pictures on photo album、family in living room、old pictures hung on string light；素材来源 URL 记录在 `frontend/src/lib/memory-space.ts` 并由 `frontend/tests/memory-space.test.mjs` 覆盖。
- 当前材料解析、OCR、ASR、图片理解、视频分析和严格六模块记忆抽取已可在配置 `DASHSCOPE_API_KEY` 后走 DashScope；公网样本烟测脚本已接入并在 2026-07-04 复跑通过，文本、图片、音频、视频、PDF、DOCX 和 DOC 均经真实上传 API 生成 DashScope third_party parse job、ParsedChunk 和 source-backed MemoryCard，结果记录在 `.smoke/real-multimodal/results/20260704-170719.json`。文本 chat、story generation、memory context compression、Persona Engine profile analysis、TTS 和音色克隆已可在配置 MiniMax key/base URL 与 `OPENAI_MODEL` 后走 MiniMax；默认 TTS 可选择 MiniMax 中文普通话 system voice 并在预览区展示模型和 `voice_id`，声音页样本可通过上传或浏览器录制 TA 的纯净人声音频创建，录音提交前会转为 MiniMax 克隆支持的 WAV，但不动态拉取完整 system voice catalog；默认未配置时仍使用 deterministic mock Provider Gateway 或 local fallback。文本 Chat/Story 已完成真实 MiniMax 调用烟测，Persona Engine 仅在显式 profile regenerate 时调用，长期人格质量和更大样本评测仍待后续验收；音色样本提取和 3D 生成仍为 mock/本地规则；当前自动记忆审核刷新 profile 和长期 Markdown，不触发真实 LLM 成本且不覆盖上传解析链路生成的唯一 trust；对象存储桶初始化、生产密钥管理和真实 3D provider 仍待后续任务确认，MiniMax 音色克隆质量还取决于账号实名/企业认证和样本音频质量。
- Milestone 7 已保留后端 avatar config/default/generate/mock fallback 兼容 API，并完成 GLB 上传/文件读取 API、前端 GLB 数字人展示、共享 `AvatarStage`、视频手势本地识别和 GLB 动作反馈；Milestone 8 后端故事、导出、删除和清空账号数据 API 保留；当前前端把回忆讲述放入记忆档案馆，并提供独立遗憾对话室和心愿延续引导页；两者通过 conversation kind/context_kind 使用专用 conversation、专门 prompt 和上下文隔离，但不声明独立后端遗憾记录模型、心愿数据模型、提醒策略或长期 P1 心愿系统能力。复杂手语、全身动作捕捉、多人识别、手势触发模型回复、真实音频音量包络/viseme 口型同步、真实 3D provider 质量、真实 MinIO/S3 对象删除、生产级 secret manager 和真实 LLM 长期质量仍待验收或后续实现。
- P1 创建人物资料卡片 `age` 必填已完成基础闭环；根据当前用户指令，自定义人格档案维度、AI 主动关怀、心愿延续系统及其他 P1/P2 功能点暂缓开发，已完成功能点保留。
