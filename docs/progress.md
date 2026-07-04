# Session Progress Log

## Latest Session Update - 2026-07-04 Frontend Star Interaction Polish

- 确认当前 Next.js 前端没有独立 `.html` 文件；本次用户所指“最新前端代码 html 文件”对应页面入口是 `frontend/app/personas/[id]/chat/page.tsx`，审核跳转入口是 `frontend/app/personas/[id]/memories/page.tsx`。
- 保留记忆审核页“完成审核，点亮星星”后的 `router.push(ROUTES.personaChat(personaId))` 跳转，目标仍为 `/personas/{id}/chat`。
- 微调星空互动页文案与模式：将“文字互动”明确为“文字对话”，将“语音互动”明确为“语音对话”，并把页面说明改为“文字对话 / 视频手势互动 -> 语音对话”的用户流程。
- 视频手势互动模式新增“进入语音对话”按钮，保持当前不新增后端范围，只在前端完成从手势入口切换到语音对话入口。
- 右侧 TA 陪伴区新增 `star-companion-*` 星空人物剪影与轨道光环 CSS，使页面更贴近参考图中的星空人物陪伴主视觉；底部三张卡片继续保留“记忆档案馆”“遗憾对话室”“心愿延续系统”。
- 本次仅修改前端页面与样式、进度文档；后端不作为本次强制跑通项。
- 已通过 `npm.cmd --prefix frontend run test`、`npm.cmd --prefix frontend run lint`、`npm.cmd --prefix frontend run build`。

## Current State

- 项目：可信人格记忆Agent
- 当前阶段：全站温馨沉浸式「记忆空间」前端改造与免注册一键演示入口已接入；Milestone 6 Task 1/2/3/4 后端默认 TTS、语音合成、音色样本、音色克隆兜底、语音消息 ASR 到 TTS、前端录音、声音设置和 mock 语音播放基础闭环已接入；Milestone 7 Task 1/2/3 后端 3D 数字人配置、默认形象、mock 生成、前端 Three.js mock 预览、对话页 3D 数字人展示和播放状态口型联动基础闭环已接入；Milestone 8 后端回忆讲述生成与聊天页星空互动主界面/记忆档案馆入口已接入，Milestone 0 到 Milestone 5 保持可验证
- 当前活跃功能：免注册 `POST /api/auth/demo` 本地演示会话、中文首页和 DemoEntry 演示入口；全站「记忆空间」暖色视觉系统、Pexels 本地素材和共享组件；Milestone 1 人物 CRUD、认证表单接入、人物列表、四步创建人物和人物记忆空间页；Milestone 2 SourceMaterial 资料记录、AI Job、资料上传页和任务状态页；Milestone 3 deterministic mock parsing、ParsedChunk、MemoryCard、记忆审计 API 和记忆审计页；Milestone 4 `PersonaProfile` 聚合/编辑/重生成、可信度重算、上传建议和 profile/trust 页面；Milestone 5 conversation/message/citation/correct-memory API、mock `chat_llm` Provider Gateway、deterministic retrieval 和 `/personas/{id}/chat` 文本对话页；Milestone 6 voice config/default TTS/samples/clone/synthesize/voice-message API、mock `asr`/`tts`/`extract_voice_sample`/`voice_clone` Provider Gateway、voice AI Jobs、`/personas/{id}/voice` 声音设置页、聊天页浏览器录音/已上传音频语音消息和 audio playback；Milestone 7 avatar config/default/generate API、mock `avatar_3d` Provider Gateway、`avatar_3d` AI Job、default/generated/failure fallback AvatarModel、`/personas/{id}/avatar` 3D 形象设置页、共享 Three.js mock 头像/半身预览和聊天页 selected mock 数字人播放状态口型联动；Milestone 8 memory_stories API、`frontend/src/lib/stories.ts` 和聊天页内记忆档案馆故事生成入口
- 当前产品目标：按 PRD 建设可信人格记忆数字人；当前代码覆盖项目初始化、基础连通、账号认证、免注册本地演示、人物创建/记忆空间基础闭环、资料上传/任务队列基础闭环、mock 解析/记忆审计基础闭环、deterministic local 人格档案/可信度基础闭环、deterministic mock 文本对话基础闭环、deterministic mock 默认 TTS/语音合成/音色样本/音色克隆兜底/语音消息/前端录音播放基础闭环、mock 3D 形象配置/生成/前端预览/对话页播放状态口型联动基础闭环，以及基于已审核记忆的 mock 回忆讲述生成入口
- 当前技术栈：Next.js 15、React 19、Three.js、FastAPI、SQLAlchemy、Alembic、PostgreSQL/pgvector、Redis、MinIO、Docker Compose
- 当前统一验证入口：`docs/init.sh`

## Latest Session Update - 2026-07-04 Milestone 8 Task 2 Star Interaction Page

- 保留记忆审计页「完成审核，点亮星星」后的跳转目标为 `/personas/{id}/chat`，并将目标页重排为星空互动主界面。
- `/personas/{id}/chat` 现在包含文字互动、视频手势互动和语音互动三种模式，右侧展示 TA、当前记忆焦点和共同回忆摘要，底部提供「记忆档案馆」「遗憾对话室」「心愿延续系统」三张行动卡。
- 新增 `frontend/src/lib/stories.ts` 和 `API_PATHS.stories`；「记忆档案馆」会调用既有 `POST /api/personas/{id}/stories`，基于已审核记忆生成回忆讲述文本，并在互动页内展示标题、正文、来源摘要和 mock audio 标识。
- 「遗憾对话室」与「心愿延续系统」当前作为对话 prompt 入口，不新增后端范围；视频手势与语音模式保留入口说明，真实手势识别和真实语音质量仍待后续 provider/前端能力补齐。
- 新增 `frontend/tests/stories.test.mjs` 并扩展 routes 测试覆盖 stories API path；当前已通过 `python -m json.tool docs/feature-list.json`、`npm.cmd --prefix frontend run test` 和 `npm.cmd --prefix frontend run lint`；`npm.cmd --prefix frontend run build` 首次 120s 超时，正在用更长超时复跑。

## Previous Session Update - 2026-07-04 Milestone 7 Task 3 Chat Avatar Mouth Linkage

- 抽取共享 `frontend/src/components/AvatarPreview.tsx`，复用 Task 2 的 Three.js mock 头像/半身渲染，避免 `/personas/{id}/avatar` 和 `/personas/{id}/chat` 维护两份场景代码。
- 聊天页加载 `getAvatarConfig(personaId)`；当 selected avatar model 具备 `model_url` 和 `format` 时，在对话侧展示 mock 3D 数字人。
- persona 语音回复的 `<audio>` `onPlay`/`onPause`/`onEnded` 事件更新当前播放消息 ID；只有当前播放中的 persona audio message 会驱动 `mouthActive`，暂停/结束后回到微笑。
- 新增 `shouldShowChatAvatar` 与 `shouldDriveAvatarMouth` helper 测试，覆盖 selected model 显示条件和口型驱动条件。
- 保持范围边界：当前是播放状态驱动的 mock 口型，不加载真实 GLB，不实现真实音频音量包络、viseme、真实 3D provider、影视级拟真或全身动作捕捉。

## Previous Session Update - 2026-07-04 Full-Site Memory Space Frontend

- 将前端产品心智从后台管理切换为温馨沉浸式「记忆空间」：首页、登录/注册、Dashboard、四步创建人物、人物详情、资料上传、任务、记忆审计、人格档案、文本对话、声音设置和形象预览页均已使用暖色生活场景背景、半透明面板、纸质卡片、照片叠层、便签、语音波形和记忆行动卡。
- 新增共享视觉组件与展示常量：`frontend/src/components/MemorySpace.tsx`、`frontend/src/lib/memory-space.ts`、Tailwind 暖色主题和 `prefers-reduced-motion` 降级。
- 使用 Pexels 免费素材并下载到 `frontend/public/memory-space/`：`grandmother-tea.jpg`、`family-album.jpg`、`family-living-room.jpg`、`memory-string-lights.jpg`；来源 URL、用途和 alt 文案记录在 `MEMORY_SPACE_ASSETS`，并由 `frontend/tests/memory-space.test.mjs` 校验。
- 首页首屏保留主入口「立即体验示例」和次入口「登录已有账号」；所有 signed-out 状态保留免注册演示入口。
- 本机重建 Compose 时发现宿主机 `5432` 绑定失败；已将 PostgreSQL 宿主机端口改为 `${POSTGRES_HOST_PORT:-15432}:5432`，容器内服务仍使用 `postgres:5432`，不改变应用数据库连接。
- 保持范围边界：本次不新增后端 API、不改数据库；仍使用 deterministic mock provider，不实现真实 OCR/ASR/LLM、真实音色、真实 3D 数字人或导出。
- 浏览器复验已完成：1280x720 与 390x844 首页均显示中文沉浸式首屏，主/次入口在首屏内，Pexels 本地图片正常加载，无横向溢出或按钮重叠；点击「立即体验示例」无需注册进入「外婆的记忆空间」；文本对话发送「外婆，我今天很想你」返回中文第一人称回复、包含「小铭」并展示「回复依据」。
- 二级页面复验已完成：资料上传、任务、记忆审计、人格档案、声音设置和 3D 形象页均无「工作台」前端文案残留、无横向溢出；3D 形象页 canvas 桌面像素检查 `sampled=6600`、`colorBuckets=50`、`nonblank=True`，移动像素检查 `sampled=6030`、`colorBuckets=38`、`nonblank=True`。
- 最终验证通过：`python -m json.tool docs/feature-list.json`、`python -m pytest backend/tests -q`（116 passed）、`npm.cmd --prefix frontend run test`（44 passed）、`npm.cmd --prefix frontend run lint`、`npm.cmd --prefix frontend run build`、`docker compose config` 和 `& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 均退出码 0。

## Previous Session Update - 2026-07-04 Milestone 7 Task 1 Backend Avatar API

- 新增后端 Avatar API：`GET /api/personas/{id}/avatar`、`POST /api/personas/{id}/avatar/default`、`POST /api/personas/{id}/avatar/generate`。
- 复用既有 `avatar_models` 表，新增 `backend/app/schemas/avatar.py`、`backend/app/services/avatar.py`、`backend/app/api/routes/avatar.py`，并在 `backend/app/main.py` 注册。
- `default` 会创建 selected `default_avatar`，返回 mock GLB、预览图、基础表情、待机/眨眼/微笑/点头动作配置和 `audio_envelope` 口型配置。
- `generate` 只接受当前用户当前人物的 image `SourceMaterial`，创建 `avatar_3d` AI Job，通过 mock `avatar_3d` Provider Gateway 写入 selected `generated_ready` AvatarModel。
- 生成失败会写入 `generation_failed` AvatarModel 和 failed job，并回退 selected `default_avatar`，返回 PRD 原文失败提示。
- 保持范围边界：Task 1 不实现前端 Three.js/GLB 加载、对话页 3D 展示、口型同步可视化、真实 3D provider、全身动作捕捉、影视级拟真、故事/导出；Task 2 已补齐前端 Three.js mock 预览，但仍不做真实 GLB/provider 或对话页联动。

## Previous Session Update - 2026-07-04 Milestone 6 Task 4 Frontend Voice Settings And Playback

- 新增 `/personas/{id}/voice` 声音设置页：展示 voice status、默认 TTS 原文提示、已创建声音记录、音频资料选择、创建音色样本、发起 mock 音色克隆和文本转语音预览播放。
- 人物记忆空间新增「声音设置」入口；`ROUTES.personaVoice`、`API_PATHS.voice` 和 `frontend/src/lib/voice.ts` 统一前端路径与 API helper。
- 文本对话页新增语音消息区：支持浏览器 `MediaRecorder` 录音上传，也支持选择已上传音频资料，调用 `POST /api/conversations/{id}/voice-message`。
- persona 回复存在 `audio_url` 时展示浏览器 `<audio controls>` 播放控件；默认 TTS 仍展示“当前使用系统默认声音，不是 TA 的真实声音...”提示。
- 保持范围边界：当前仍是 deterministic mock ASR/TTS/voice clone，不代表真实音质；本次不实现 3D 口型同步、故事/导出或真实 provider 质量。

## Previous Session Update - 2026-07-04 中文沉浸式前端与免注册演示入口

- 新增 `POST /api/auth/demo`：每次创建本地 `guest_demo` 用户、虚构人物「外婆」、称呼「小铭」、3 条手动资料、confirmed 记忆、人格档案和可信度，并返回 `demo_persona_id`。
- 新增前端 `startDemoSession()` helper 和 `DemoEntry` 组件；首页主按钮「立即体验示例」、登录/注册和 signed-out 状态均可免注册进入外婆记忆空间。
- 将 `layout` 改为 `lang="zh-CN"`，并中文化首页、导航、登录/注册、Dashboard、四步创建人物、人物记忆空间、资料上传、任务、记忆审计、人格档案和文本对话页。
- 人物记忆空间按用户下一步重排为开始对话、上传资料、审核记忆、查看档案；文本对话页中文展示发送、依据和纠正记忆。
- 为本地前端调用后端补充 FastAPI CORS 配置，允许 `FRONTEND_URL` 对应的浏览器来源访问 API，并用后端测试覆盖预检请求。
- 真实浏览器烟测已覆盖首页中文首屏、免注册进入「外婆」记忆空间、文本对话发送「外婆，我今天很想你」并返回中文第一人称回复；桌面和移动视口均确认首屏入口可见且无横向溢出。
- 保持范围边界：当前仍使用 deterministic mock provider；不实现真实 OCR/ASR/LLM、前端语音播放、音色克隆、3D 数字人或导出。

## Previous Session Update - 2026-07-04 Milestone 6 Task 3 Voice Message API

- 按 PRD Milestone 6 继续实现后端语音消息闭环：`POST /api/conversations/{id}/voice-message`。
- 该接口接受当前用户当前 conversation 下的 audio `SourceMaterial`，创建 succeeded `asr_audio` AI Job，通过 mock ASR 得到 transcript，复用现有第一人称文本 chat、记忆检索、引用来源和禁用表达过滤，再调用 TTS 生成 `audio_url`。
- persona message 保存 `audio_url` 和 voice metadata，包括 source material、transcript、ASR job、TTS job 和 voice status。
- voice-message 测试暴露并修复 retrieval 优先级问题：存在 confirmed/corrected 命中时，不再允许 auto_generated 高重叠记忆覆盖事实记忆。
- 保持范围边界：本次不实现前端录音/播放 UI、3D avatar、故事/导出或真实 ASR/TTS/音色质量。

## Previous Session Update - 2026-07-04 Milestone 6 Task 2 Voice Sample And Clone Fallback

- 按 PRD Milestone 6 继续实现后端音色样本和 mock 音色克隆闭环：`POST /api/personas/{id}/voice/samples` 和 `POST /api/personas/{id}/voice/clone`。
- `voice/samples` 只接受当前用户当前人物的 audio `SourceMaterial`，调用 mock `extract_voice_sample`，创建 status=`sample_ready` 的 `VoiceModel` 和 succeeded `extract_voice_sample` AI Job。
- `voice/clone` 调用 mock `voice_clone`，成功时把样本标记为 selected `cloned_ready` 并返回 mock `model_artifact_url`；失败时把样本标记为 `clone_failed`，创建或保留 selected `default_tts` fallback，并返回默认 TTS 提示。
- 保持范围边界：本次不实现 `POST /api/conversations/{id}/voice-message`、前端录音/播放、3D avatar、故事/导出或真实 TTS/音色质量。
- 注意：当前工作区还有未纳入本次 voice 提交的 auth demo 相关修改；完整后端测试 `107 passed` 包含这些未提交测试，voice 提交本身只 staging voice/docs/frontend-copy 相关文件。

## Previous Session Update - 2026-07-04 Milestone 6 Task 1 Backend Default TTS

- 按 PRD Milestone 6 先实现最小可验证后端闭环：`GET /api/personas/{id}/voice`、`POST /api/personas/{id}/voice/default-tts` 和 `POST /api/personas/{id}/voice/synthesize`。
- 新增 `backend/app/schemas/voice.py`、`backend/app/services/voice.py`、`backend/app/api/routes/voice.py` 和 `backend/tests/test_voice.py`，并在 `backend/app/main.py` 注册 voice router。
- `VoiceModel` 复用既有 PRD 表结构；默认 TTS 选择写入 selected `VoiceModel`，status=`default_tts`，provider=`mock_default_tts`。
- mock `tts` Provider Gateway 生成 deterministic `mock://tts/...wav`，语音合成写入 succeeded `synthesize_speech` AI Job，任务列表 API 可查看。
- 默认 TTS 响应返回 PRD 原文提示：`当前使用系统默认声音，不是 TA 的真实声音。上传 TA 的清晰语音后，可以尝试生成模拟音色。`
- 保持范围边界：本次不实现音色样本提取、音色克隆成功/失败兜底、`POST /api/conversations/{id}/voice-message`、前端录音/播放、3D avatar、故事/导出或真实 TTS/音色质量。

## Previous Session Update - 2026-07-04 Local Compose Startup Smoke

- 按本地启动请求运行 `docs/init.sh`，required files、JSON、后端测试、前端 test/lint/build 和 `docker compose config` 均通过。
- 首次执行 `docker compose up --build -d` 时，镜像构建和依赖服务启动成功，但 backend 容器在 Uvicorn 冷启动导入 `app.main` 时因 `app.models.user.uuid_str` 循环导入退出。
- 新增独立 Python 进程导入回归测试，覆盖 `from app.main import app` 的容器冷启动导入路径。
- 最小修复 `backend/app/models/user.py` 的 `uuid_str` 定义顺序，使其他模型在 `Base` 批量注册期间可导入该默认值函数。
- 重新构建并后台启动 Compose 后，frontend、backend、postgres、redis、minio 和四个 mock worker 均已运行；backend 为 healthy。
- HTTP 烟测通过：`http://localhost:3000/` 返回 200，`http://localhost:8000/health` 返回 200 / `{"status":"ok"}`，`http://localhost:9001/` 返回 200。

## Latest Session Update - 2026-07-04 Milestone 5 Task 3 Docs And Harness Sync

- 按 brief 先更新 `docs/prd-checklist.md`，新增 Milestone 5 验收行：conversation list/create、message list/send、mock `chat_llm` Provider Gateway、第一人称与用户称呼、corrected 优先于 confirmed 的 deterministic retrieval、inactive/deleted memory 排除、`message_citations`、`correct-memory` 立即影响后续对话，以及前端 `/personas/{id}/chat` 文本对话、依据和纠错 UI。
- 同步 `docs/README.md`、`docs/feature-list.json`、`docs/progress.md`、`docs/prd-checklist.md`、`docs/平台说明.md`、`docs/init.sh` 和 `frontend/app/page.tsx`，将当前事实更新为 Milestone 5 第一人称文本对话基础闭环已实现。
- 新增 `feat-009` 记录 Milestone 5 已完成范围、依赖和证据。
- 保持范围边界：当前 chat 是 deterministic mock Provider Gateway/local retrieval，不代表真实 LLM 或 embedding retrieval quality；`voice-message`、语音/TTS、音色克隆、3D avatar、故事/导出和完整 Demo flow 仍未实现。
- 本次代码行为来自 commit `88b3194` 和 `01fa440`；docs sync 前 baseline 验证已通过：JSON、后端 96 passed、前端 21 passed、lint、build、Compose config 和 `docs/init.sh`。
- 最终验证已通过：JSON、后端 97 passed、前端 21 passed、lint、build、Compose config、Milestone 5 `docs/init.sh`、`git diff --check` 和 stale-copy 搜索均符合预期；`git diff --check` 只输出 LF-to-CRLF working-copy warnings。

## Previous Session Update - 2026-07-04 Milestone 4 Task 3 Docs And Harness Sync

- 按 brief 先更新 `docs/prd-checklist.md`，新增 Milestone 4 验收行：`PersonaProfile` 从 confirmed/corrected active memories 聚合、维度保留 source memory IDs、profile GET/PATCH/regenerate API 用户隔离、memory audit 后刷新 trust/profile、可信度使用 PRD 可解释权重、前端 `/personas/{id}/profile` 展示并编辑 profile/trust/suggestions，以及 future chat 才读取 `prompt_context.profile_summary`。
- 同步 `docs/README.md`、`docs/feature-list.json`、`docs/progress.md`、`docs/prd-checklist.md`、`docs/平台说明.md`、`docs/init.sh` 和 `frontend/app/page.tsx`，将当前事实更新为 Milestone 4 人格档案与可信度基础闭环已实现。
- 新增 `feat-008` 记录 Milestone 4 已完成范围、依赖和证据。
- 保持范围边界：当前 profile/trust 是 deterministic local 规则，不代表真实 provider profile quality；当时的对话检索、语音/TTS、头像/3D、故事/导出和完整 Demo flow 仍属后续范围。
- 本次不改变后端 API、前端业务逻辑、数据模型或 Compose 拓扑；代码行为来自 commit `6801bab`、`6cc7c21`、`24a889d`、`a184de0` 和 `f43e551`。

## Previous Session Update - 2026-07-04 Milestone 3 Task 4 Docs And Harness Sync

- 按 brief 先更新 `docs/prd-checklist.md`，新增 Milestone 3 验收行：上传/手动资料生成 `ParsedChunk` 与 source-backed `MemoryCard`、OCR/ASR/VLM/video 为 deterministic mock provider 输出、记忆来源字段、用户隔离、确认/编辑/拒绝/禁用/删除、前端筛选与审计动作，以及 chat/trust/profile recalculation 后置。
- 同步 `docs/README.md`、`docs/feature-list.json`、`docs/progress.md`、`docs/prd-checklist.md`、`docs/平台说明.md`、`docs/init.sh` 和 `frontend/app/page.tsx`，将当前事实更新为 Milestone 3 mock 多模态解析与记忆审计基础闭环已实现。
- 新增 `feat-007` 记录 Milestone 3 已完成范围、依赖和证据。
- 保持范围边界：当前材料解析、OCR、ASR、图片理解、视频分析和 memory extraction 只使用 deterministic mock Provider Gateway 输出；真实模型质量、人格档案聚合、可信度重算、对话记忆检索、语音/TTS、头像/3D、故事/导出和完整 Demo flow 仍未实现。
- 本次不改变后端 API、前端业务逻辑、数据模型或 Compose 拓扑；代码行为来自 commit `ed2d6ac`、`5c75991` 和 `92cef29`。

## Previous Session Update - 2026-07-04 Milestone 2 Copy Cleanup

- 修复后续 stale-copy finding：`docs/init.sh` banner/completion 文案已从 Milestone 1 更新为 Milestone 2。
- 修复前端首页文案：当前状态改为账号、人物工作台、资料上传/手动输入和任务状态跟踪已可用；记忆、对话、语音、头像和导出仍标记为 upcoming。
- 修复 `docs/平台说明.md` 页面表格：`/` 入口说明已从 Milestone 0 更新为 Milestone 2 资料工作区入口。
- 本次不改变 API、数据模型、Compose 拓扑或启动命令，仅同步可见文案与 handoff 记录。

## Previous Session Update - 2026-07-04 Milestone 2 Task 3 Docs And Harness Sync

- 按 brief 先更新 `docs/prd-checklist.md`，新增 Milestone 2 验收行：上传/手动资料创建、每资料 AI Job、任务状态可见、重试/取消、用户隔离、前端上传/任务页和本地 storage 兜底。
- 在同步其他 docs 前运行 baseline 验证：JSON、后端测试、前端 test/lint/build、`docker compose config` 和 `docs/init.sh` 均退出码 0。
- 同步 `docs/README.md`、`docs/feature-list.json`、`docs/progress.md`、`docs/prd-checklist.md` 和 `docs/平台说明.md`，将当前事实更新为 Milestone 2 资料上传/任务队列基础闭环已实现。
- 新增 `feat-006` 记录 Milestone 2 已完成范围、依赖和证据。
- 保持范围边界：当前只创建 SourceMaterial、local storage 文件和 queued mock parse jobs；材料解析、OCR、ASR、图片理解、视频分析、记忆抽取/审计、对话、语音/TTS、头像/3D、导出和完整 Demo flow 仍未实现。
- `AGENTS.md` 未修改，因为本任务未改变启动命令、验证命令或 agent 工作流。

## Previous Session Update - 2026-07-04 Task 2 Review Docs Fix

- 修复 Task 2 review docs/handoff finding：文档 truth surface 已同步为当前代码覆盖 Milestone 0 基础工程和 Milestone 1 人物创建/工作台基础闭环。
- 修复后续 minor stale-copy finding：前端首页和 `docs/init.sh` 已从 Milestone 0 文案更新为 Milestone 1 人物工作台状态。
- 新增根目录 `.gitignore`，避免 `.env/`、`node_modules/`、`.next/`、`__pycache__/`、`.superpowers/` 等本地状态污染后续提交。
- 同步 `docs/README.md`、`docs/feature-list.json`、`docs/progress.md`、`docs/prd-checklist.md` 和 `docs/平台说明.md`，将当前事实更新为 Milestone 1 人物创建/工作台基础闭环已实现。
- 记录后端已实现用户隔离的人物 CRUD、四类 MVP 人物类型、预留 `expert_role` 拒绝、`prompt_context` 输出和基础统计。
- 记录前端已实现注册/登录表单接入、JWT 本地保存、Dashboard 人物列表、人物创建表单缺失字段阻止提交，以及人物详情/工作台页。
- 保持范围边界：资料上传、材料解析、记忆抽取/审计、对话、语音/TTS、头像/3D、导出和完整 Demo flow 仍未实现。
- 保留残余风险：Task 2 未运行真实浏览器连接后端的烟测，`docker compose up --build` 服务级烟测未运行，前端依赖树仍有 2 个 moderate severity npm audit findings。

## Previous Session Update - 2026-07-04 Task 3 Review Fix

- 将 `docs/可信人格记忆Agent_mvp_prd.md` 纳入本次提交范围，使 `docs/init.sh` 所需 PRD 文件成为自包含 tracked 文件。
- 新增 `backend/docker-entrypoint.sh`，后端容器启动时先执行 `alembic upgrade head`，再启动 Uvicorn，解决 Compose 注册/登录依赖迁移但未执行迁移的问题。
- 更新 `backend/Dockerfile` 使用后端 entrypoint，并新增 `backend/tests/test_container_runtime.py` 覆盖容器启动迁移脚本和 Docker context 忽略规则。
- 新增 `backend/.dockerignore` 和 `frontend/.dockerignore`，避免本地 `__pycache__`、`.env*`、`node_modules`、`.next`、`next-env.d.ts` 等生成或本地状态进入 Docker build context。
- 清理 `docs/prd-checklist.md` 中与 Milestone 0 已完成状态矛盾的模板行，并同步 `docs/README.md`、`docs/feature-list.json`、`docs/平台说明.md`、`docs/init.sh` 和 `AGENTS.md`。
- 保留 npm audit findings 为非阻塞跟进项，未运行 `npm audit fix --force`。

## Previous Session Update - 2026-07-04

- 先在 `docs/prd-checklist.md` 添加 Milestone 0 验收行并标记 `in-progress`，再开始 Docker 与 harness 修改。
- 新增 `backend/Dockerfile`、`frontend/Dockerfile` 和 `docker-compose.yml`，覆盖 frontend、backend、postgres、redis、minio、worker-text、worker-media、worker-voice、worker-avatar。
- 将 `docs/init.sh` 从 docs-only 自检升级为 Milestone 0 harness：JSON、后端 pytest、前端 test/lint/build、`docker compose config`。
- 生成并纳入 `frontend/package-lock.json`，用于前端依赖可复现安装。
- 同步更新 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md`、`docs/平台说明.md` 和 `AGENTS.md`，移除“技术栈/代码事实待填写”的过期状态。
- 未提交 `.env/runtime.env`、`node_modules`、`.next`、`__pycache__` 或其他本地生成缓存。

## Status

### What's Done

- FastAPI 后端基础、认证 API、模型/迁移和测试由 Task 1 提供。
- 后端人物 CRUD、`prompt_context`、用户隔离、必填字段/枚举校验和 API 测试已接入 Milestone 1。
- Next.js 前端页面骨架、API 路径配置、注册/登录表单接入、人物列表、人物创建表单校验、人物详情/工作台页和前端检查脚本由 Task 2 提供。
- Milestone 2 后端资料和任务 API 已接入：文本/图片/音频/视频上传、手动资料、SourceMaterial、AI Job、资料列表/详情/删除/重新排队、任务列表/详情/重试/取消、用户隔离和本地 storage 兜底。
- Milestone 2 前端上传/任务页已接入：人物详情入口、`/personas/{id}/uploads` 文件/手动资料表单和资料列表、`/personas/{id}/jobs` 任务状态列表与 retry/cancel 操作。
- Milestone 3 后端 mock 解析和记忆 API 已接入：Provider Gateway deterministic `text_parser`/`ocr`/`asr`/`image_understanding`/`video_understanding`/`memory_extraction` 输出、`ParsedChunk`、source-backed `MemoryCard`、记忆列表/创建/详情/编辑/确认/拒绝/禁用/删除和用户隔离。
- Milestone 3 前端记忆审计页已接入：人物详情入口、`/personas/{id}/memories`、状态/分类/置信度筛选、来源展示和 confirm/edit/reject/disable/delete 操作。
- Milestone 4 后端人格档案和可信度 API 已接入：`GET/PATCH /api/personas/{id}/profile`、`POST /api/personas/{id}/profile/regenerate`、`POST /api/personas/{id}/recalculate-trust`、confirmed/corrected active memory 聚合、source memory IDs、manual override preservation、memory audit refresh、PRD weighted deterministic trust score 和 succeeded `update_profile`/`calculate_trust_score` jobs。
- Milestone 4 前端 profile/trust 页已接入：人物详情入口、`/personas/{id}/profile`、trust score/level/components/suggestions、profile dimensions/source memory ids、save/regenerate/recalculate 操作；Milestone 5 文本对话现在读取当前 profile summary。
- Milestone 5 后端文本对话 API 已接入：`GET/POST /api/personas/{id}/conversations`、`GET/POST /api/conversations/{id}/messages`、`GET /api/messages/{id}/citations`、`POST /api/messages/{id}/correct-memory`、mock `chat_llm` Provider Gateway、deterministic retrieval、first-person/nickname response、citation persistence、correct-memory immediate effect 和 user isolation。
- Milestone 5 前端文本对话页已接入：人物详情入口、`/personas/{id}/chat`、conversation 加载/创建、消息流、文本输入、依据展示和记忆纠正操作。
- 免注册本地演示已接入：`POST /api/auth/demo` 创建 `guest_demo` 用户、示例人物「外婆」、3 条手动资料、confirmed 记忆、profile/trust 和 `demo_persona_id`；前端中文首页、登录/注册和 signed-out 状态可通过「无需注册，体验示例」进入人物记忆空间。
- 当前前端主体验已中文化：`lang="zh-CN"`、中文导航、中文首页、四步创建人物、人物记忆空间、资料上传、任务、记忆审计、人格档案和文本对话页。
- Milestone 6 voice 前后端基础闭环已接入：后端 voice config/default TTS/samples/clone/synthesize/voice-message API，前端声音设置页、聊天页录音/已上传音频语音消息和 audio playback。
- Milestone 7 avatar 前端/后端基础闭环已接入：后端 avatar config/default/generate API、mock `avatar_3d` Provider Gateway、avatar_3d AI Job、default/generated/failure fallback AvatarModel，前端 `/personas/{id}/avatar` 3D 形象设置页、共享 Three.js mock 头像/半身预览和聊天页 selected mock 数字人播放状态口型联动。
- Task 3 已接入 Dockerfile、Compose 拓扑、统一 harness 和 Milestone 0 文档说明。
- Task 3 review fix 已补齐 tracked PRD、自启动迁移 entrypoint、Docker context 忽略文件和 PRD checklist 清理。
- Compose 中只包含变量名、空白 provider 配置和开发默认值，不包含真实密钥。

### What's In Progress

- Milestone 8 下一步：回忆讲述与导出/删除关键数据仍待实现；真实 GLB/3D provider 质量不作为当前 mock MVP 阻塞。

### What's Next

1. Milestone 8 后续验收：实现回忆讲述与导出/删除关键数据。
2. 后续接入真实 AI Provider 或 embedding 检索时，先扩展 provider gateway 和 mock/真实 provider 测试，不直接在业务代码中散落模型调用。
3. 跟进当前前端依赖树中的 2 个 moderate severity npm audit findings，避免使用 `npm audit fix --force` 进行破坏性升级。

## Session Impact Checklist

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| 是否改变产品行为 | 是 | 本次会话新增 Milestone 7 对话页 selected mock 3D 数字人展示和语音播放状态口型联动。 |
| 是否改变代码逻辑 | 是 | 抽取共享 `AvatarPreview`，聊天页读取 avatar config 并将 persona audio 播放状态传入口型动画；Compose 拓扑未改。 |
| 是否改变启动命令 | 否 | 本地拓扑仍使用 `docker compose up --build`；统一验证入口仍为 `docs/init.sh`。 |
| 是否更新功能范围账本 | 是 | 新增 `feat-018` 记录 Milestone 7 Task 3 对话页数字人与播放状态口型联动闭环。 |
| 是否更新交接记录 | 是 | 本文件记录 Milestone 7 Task 3 实现、验证证据和残余风险。 |

## Blockers / Risks

- 本次已运行首页、免注册进入外婆记忆空间和文本对话的真实浏览器烟测；Milestone 7 形象设置页与聊天页数字人区域已运行临时 mock API 浏览器烟测和桌面/移动 canvas 区域像素检查；Milestone 2 上传页、任务页、Milestone 3 记忆审计页、Milestone 4 profile/trust 页和 Milestone 6 voice 前端仍主要依赖自动化测试、lint、build、Compose 配置和 harness 证据。
- 2026-07-04 本地已完成一次 `docker compose up --build -d` 服务级烟测；后续如重启服务，仍应确认本机端口 3000、8000、15432（或 `POSTGRES_HOST_PORT` 指定端口）、6379、9000、9001 未被占用。
- 当前前端依赖树存在 2 个 moderate severity npm audit findings；本任务未改依赖版本，未执行破坏性 `npm audit fix --force`。
- 已新增 `.gitignore` 忽略常见本地生成物和 `.env/`；仍需注意不要手动强制 staging 真实密钥或生成目录。
- 当前资料解析、OCR、ASR、图片理解、视频分析、记忆抽取和文本 chat 只使用 deterministic mock Provider Gateway/local retrieval 输出，不代表真实模型质量。
- 当前人格档案聚合和可信度重算只使用 deterministic local 规则，不代表真实 provider profile quality。
- Milestone 6 已接入前端录音、声音设置页和 mock 语音播放；仍未运行真实浏览器连接后端的完整语音端到端 smoke。
- Milestone 7 目前完成后端 avatar API、前端 Three.js mock 头像/半身预览和聊天页播放状态口型联动；真实 GLB 加载、真实音频音量包络/viseme 口型同步和真实 3D provider 质量仍未实现。
- 本地一键演示入口已实现；真实 LLM/embedding 检索质量、真实 TTS/音色质量、故事/导出尚未实现。

## Evidence of Completion

- Milestone 7 Task 3 RED：`npm.cmd --prefix frontend run test -- avatar.test.mjs` 退出码 1，缺少 `shouldDriveAvatarMouth` export，按预期暴露对话页口型 helper 尚未实现。
- Milestone 7 Task 3 focused GREEN：`npm.cmd --prefix frontend run test -- avatar.test.mjs` 退出码 0，44 passed。
- Milestone 7 Task 3 frontend verification：`npm.cmd --prefix frontend run test` 退出码 0，44 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，`/personas/[id]/chat` 构建通过。
- Milestone 7 Task 3 unified harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，Milestone 7 Task 2 banner（随后已更新为 Task 3）、required files、JSON、116 backend tests、44 frontend tests、frontend lint/build、Compose config 均通过。
- Milestone 7 Task 3 browser smoke：临时 mock API + 当前工作树 Next dev server，1280x720 聊天页截图可见对话侧 Three.js mock 数字人和 audio 回复；截图 avatar 区域像素统计 `sampledPixels=9483`、`nonWhiteSamples=9483`、`colorBuckets=82`、`skinToneSamples=5861`、`darkSamples=176`。
- Milestone 7 Task 3 browser smoke：390x844 移动视口滚动到聊天页 canvas，截图可见 mock 数字人；截图 avatar 区域像素统计 `sampledPixels=9492`、`nonWhiteSamples=9492`、`colorBuckets=132`、`skinToneSamples=4774`、`darkSamples=139`。

- 中文体验 CORS focused RED：`python -m pytest backend/tests/test_health.py -q` 退出码 1，`OPTIONS /api/auth/demo` 从 `http://localhost:3000` 来源返回 405。
- 中文体验 CORS focused GREEN：`python -m pytest backend/tests/test_health.py -q` 退出码 0，2 passed。
- 中文体验 backend full：`python -m pytest backend/tests -q` 退出码 0，110 passed。
- 中文体验 JSON 校验：`python -m json.tool docs/feature-list.json` 退出码 0。
- 中文体验 frontend tests：`npm.cmd --prefix frontend run test` 退出码 0，32 passed。
- 中文体验 frontend lint：`npm.cmd --prefix frontend run lint` 退出码 0。
- 中文体验 frontend build：`npm.cmd --prefix frontend run build` 退出码 0，Next.js build succeeded。
- 中文体验 Compose config：`docker compose config` 退出码 0。
- 中文体验服务启动：`docker compose up --build -d` 退出码 0，backend healthy，frontend started；Compose 报告既有 orphan containers warning，未阻塞服务启动。
- 中文体验真实浏览器烟测：首页中文首屏展示「立即体验示例」和「登录已有账号」；点击主入口无需注册进入「外婆」人物记忆空间；进入文本对话发送「外婆，我今天很想你」后返回中文第一人称回复、包含「小铭」并展示回复依据。
- 中文体验响应式检查：in-app browser 以 1280x720 和 390x844 视口检查首页，主/次入口均在首屏内，未发现横向溢出或按钮重叠。
- 中文体验统一 harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，required files、JSON、110 backend tests、32 frontend tests、frontend lint/build、Compose config 均通过。
- Pre-change baseline `python -m json.tool docs/feature-list.json`：退出码 0。
- Pre-change baseline `& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh`：退出码 0，旧 docs-only harness 通过。
- `python -m json.tool docs/feature-list.json`：退出码 0。
- `python -m pytest backend/tests -q`：退出码 0，63 passed。
- `npm.cmd --prefix frontend run test`：退出码 0，5 passed。
- `npm.cmd --prefix frontend run lint`：退出码 0。
- `npm.cmd --prefix frontend run build`：退出码 0，Next.js build succeeded。
- `docker compose config`：退出码 0。
- `& "C:\Program Files\Git\bin\bash.exe" -lc "cd '/c/Users/Admin/Desktop/coding/可信人格记忆Agent' && sh -n backend/docker-entrypoint.sh"`：退出码 0。
- MinIO image check：`minio/minio:RELEASE.2026-06-13T11-33-47Z` 不存在，已改为 Docker Hub 返回且 manifest 可解析的 `minio/minio:RELEASE.2025-09-07T16-13-09Z`。
- `& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh`：退出码 0，required harness files、JSON、63 backend tests、5 frontend tests、frontend lint/build、Compose config 均通过。
- Task 2 frontend RED：`npm.cmd --prefix frontend run test` 退出码 1，新增 Milestone 1 routes/persona helper 测试按预期失败。
- Task 2 frontend GREEN：`npm.cmd --prefix frontend run test` 退出码 0，5 tests passed。
- Task 2 final frontend verification：`npm.cmd --prefix frontend run test`、`npm.cmd --prefix frontend run lint`、`npm.cmd --prefix frontend run build` 均退出码 0。
- Task 2 docs review fix verification：`python -m json.tool docs/feature-list.json` 退出码 0；`python -m pytest backend/tests -q` 退出码 0，63 passed；`npm.cmd --prefix frontend run test` 退出码 0，5 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`docker compose config` 退出码 0；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0。
- Milestone 2 Task 3 pre-doc verification after checklist update：`python -m json.tool docs/feature-list.json` 退出码 0。
- Milestone 2 Task 3 pre-doc verification after checklist update：`python -m pytest backend/tests -q` 退出码 0，74 passed。
- Milestone 2 Task 3 pre-doc verification after checklist update：`npm.cmd --prefix frontend run test` 退出码 0，8 passed。
- Milestone 2 Task 3 pre-doc verification after checklist update：`npm.cmd --prefix frontend run lint` 退出码 0。
- Milestone 2 Task 3 pre-doc verification after checklist update：`npm.cmd --prefix frontend run build` 退出码 0，Next.js build succeeded with `/personas/[id]/uploads` and `/personas/[id]/jobs` routes.
- Milestone 2 Task 3 pre-doc verification after checklist update：`docker compose config` 退出码 0。
- Milestone 2 Task 3 pre-doc verification after checklist update：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，required files、JSON、74 backend tests、8 frontend tests、frontend lint/build、Compose config 均通过。
- Milestone 2 Task 3 post-doc verification：`python -m json.tool docs/feature-list.json` 退出码 0。
- Milestone 2 Task 3 post-doc verification：`python -m pytest backend/tests -q` 退出码 0，74 passed。
- Milestone 2 Task 3 post-doc verification：`npm.cmd --prefix frontend run test` 退出码 0，8 passed。
- Milestone 2 Task 3 post-doc verification：`npm.cmd --prefix frontend run lint` 退出码 0。
- Milestone 2 Task 3 post-doc verification：`npm.cmd --prefix frontend run build` 退出码 0，Next.js build succeeded with `/personas/[id]/uploads` and `/personas/[id]/jobs` routes.
- Milestone 2 Task 3 post-doc verification：`docker compose config` 退出码 0。
- Milestone 2 Task 3 post-doc verification：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，required files、JSON、74 backend tests、8 frontend tests、frontend lint/build、Compose config 均通过。
- Milestone 2 copy cleanup verification：`python -m json.tool docs/feature-list.json` 退出码 0。
- Milestone 2 copy cleanup verification：`python -m pytest backend/tests -q` 退出码 0，74 passed。
- Milestone 2 copy cleanup verification：`npm.cmd --prefix frontend run test` 退出码 0，8 passed。
- Milestone 2 copy cleanup verification：`npm.cmd --prefix frontend run lint` 退出码 0。
- Milestone 2 copy cleanup verification：`npm.cmd --prefix frontend run build` 退出码 0，Next.js build succeeded with `/personas/[id]/uploads` and `/personas/[id]/jobs` routes.
- Milestone 2 copy cleanup verification：`docker compose config` 退出码 0。
- Milestone 2 copy cleanup verification：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，Milestone 2 banner、required files、JSON、74 backend tests、8 frontend tests、frontend lint/build、Compose config 均通过。
- Milestone 6 Task 4 RED：`npm.cmd --prefix frontend run test -- voice.test.mjs` 退出码 1，按预期暴露 `frontend/src/lib/voice.js`/`voice.ts` 尚不存在。
- Milestone 6 Task 4 frontend verification：`npm.cmd --prefix frontend run test` 退出码 0，32 tests passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，Next.js build includes `/personas/[id]/voice` route。
- Milestone 6 Task 4 unified harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，required files、JSON、110 backend tests、32 frontend tests、frontend lint/build、Compose config 均通过。
- Milestone 7 Task 1 RED：`python -m pytest backend/tests/test_avatar.py -q` 退出码 1，5 failed / 1 passed，按预期暴露 avatar routes 尚不存在。
- Milestone 7 Task 1 backend verification：`python -m pytest backend/tests/test_avatar.py -q` 退出码 0，6 passed；`python -m pytest backend/tests -q` 退出码 0，116 passed。
- Milestone 7 Task 1 unified harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，required files、JSON、116 backend tests、32 frontend tests、frontend lint/build、Compose config 均通过。
- Milestone 3 Task 4 pre-doc baseline：`python -m json.tool docs/feature-list.json` 退出码 0。
- Milestone 3 Task 4 pre-doc baseline：`python -m pytest backend/tests -q` 退出码 0，80 passed。
- Milestone 3 Task 4 pre-doc baseline：`npm.cmd --prefix frontend run test` 退出码 0，12 passed。
- Milestone 3 Task 4 pre-doc baseline：`npm.cmd --prefix frontend run lint` 退出码 0。
- Milestone 3 Task 4 pre-doc baseline：`npm.cmd --prefix frontend run build` 退出码 0，Next.js build succeeded with `/personas/[id]/memories` route.
- Milestone 3 Task 4 pre-doc baseline：`docker compose config` 退出码 0。
- Milestone 3 Task 4 pre-doc baseline：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，80 backend tests、12 frontend tests、frontend build includes memory route；banner 仍为 Milestone 2，已在本次同步中更新。
- Milestone 3 Task 4 post-doc verification：`python -m json.tool docs/feature-list.json` 退出码 0。
- Milestone 3 Task 4 post-doc verification：`python -m pytest backend/tests -q` 退出码 0，80 passed。
- Milestone 3 Task 4 post-doc verification：`npm.cmd --prefix frontend run test` 退出码 0，12 passed。
- Milestone 3 Task 4 post-doc verification：`npm.cmd --prefix frontend run lint` 退出码 0。
- Milestone 3 Task 4 post-doc verification：`npm.cmd --prefix frontend run build` 退出码 0，Next.js build succeeded with `/personas/[id]/memories` route.
- Milestone 3 Task 4 post-doc verification：`docker compose config` 退出码 0。
- Milestone 3 Task 4 post-doc verification：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，Milestone 3 banner、required files、JSON、80 backend tests、12 frontend tests、frontend lint/build、Compose config 均通过。
- Milestone 3 Task 4 post-doc verification：`git diff --check` 退出码 0，仅输出既有 LF-to-CRLF working-copy warnings。
- Milestone 4 Task 3 pre-doc baseline：`python -m json.tool docs/feature-list.json` 退出码 0。
- Milestone 4 Task 3 pre-doc baseline：`python -m pytest backend/tests -q` 退出码 0，89 passed。
- Milestone 4 Task 3 pre-doc baseline：`npm.cmd --prefix frontend run test` 退出码 0，16 passed。
- Milestone 4 Task 3 pre-doc baseline：`npm.cmd --prefix frontend run lint` 退出码 0。
- Milestone 4 Task 3 pre-doc baseline：`npm.cmd --prefix frontend run build` 退出码 0，Next.js build succeeded with `/personas/[id]/profile` route.
- Milestone 4 Task 3 pre-doc baseline：`docker compose config` 退出码 0。
- Milestone 4 Task 3 pre-doc baseline：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，89 backend tests、16 frontend tests、frontend build includes profile route；banner 仍为 Milestone 3，已在本次同步中更新。
- Milestone 4 Task 3 post-doc verification：`python -m json.tool docs/feature-list.json` 退出码 0。
- Milestone 4 Task 3 post-doc verification：`python -m pytest backend/tests -q` 退出码 0，89 passed。
- Milestone 4 Task 3 post-doc verification：`npm.cmd --prefix frontend run test` 退出码 0，16 passed。
- Milestone 4 Task 3 post-doc verification：`npm.cmd --prefix frontend run lint` 退出码 0。
- Milestone 4 Task 3 post-doc verification：`npm.cmd --prefix frontend run build` 退出码 0，Next.js build succeeded with `/personas/[id]/profile` route.
- Milestone 4 Task 3 post-doc verification：`docker compose config` 退出码 0。
- Milestone 4 Task 3 post-doc verification：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，Milestone 4 banner、required files、JSON、89 backend tests、16 frontend tests、frontend lint/build、Compose config 均通过。
- Milestone 4 Task 3 post-doc verification：`git diff --check` 退出码 0，仅输出既有 LF-to-CRLF working-copy warnings。
- Milestone 5 Task 1 focused RED：`python -m pytest backend/tests/test_chat.py -q` 退出码 1，chat routes missing，7 failed。
- Milestone 5 Task 1 focused GREEN：`python -m pytest backend/tests/test_provider_gateway.py backend/tests/test_chat.py -q` 退出码 0，8 passed。
- Milestone 5 Task 1 backend full：`python -m pytest backend/tests -q` 退出码 0，96 passed。
- Milestone 5 Task 2 frontend RED：`npm.cmd --prefix frontend run test` 退出码 1，missing `frontend/src/lib/chat.js`、`ROUTES.personaChat` 和 `API_PATHS.chat`。
- Milestone 5 Task 2 frontend GREEN：`npm.cmd --prefix frontend run test` 退出码 0，21 passed。
- Milestone 5 Task 2 frontend lint：`npm.cmd --prefix frontend run lint` 退出码 0。
- Milestone 5 Task 2 frontend build：`npm.cmd --prefix frontend run build` 退出码 0，Next.js build succeeded with `/personas/[id]/chat` route.
- Milestone 5 Task 3 pre-doc baseline after checklist update：`python -m json.tool docs/feature-list.json` 退出码 0。
- Milestone 5 Task 3 pre-doc baseline after checklist update：`python -m pytest backend/tests -q` 退出码 0，96 passed。
- Milestone 5 Task 3 pre-doc baseline after checklist update：`npm.cmd --prefix frontend run test` 退出码 0，21 passed。
- Milestone 5 Task 3 pre-doc baseline after checklist update：`npm.cmd --prefix frontend run lint` 退出码 0。
- Milestone 5 Task 3 pre-doc baseline after checklist update：`npm.cmd --prefix frontend run build` 退出码 0，Next.js build succeeded with `/personas/[id]/chat` route.
- Milestone 5 Task 3 pre-doc baseline after checklist update：`docker compose config` 退出码 0。
- Milestone 5 Task 3 pre-doc baseline after checklist update：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，96 backend tests、21 frontend tests、frontend build includes chat route；banner 仍为 Milestone 4，已在本次同步中更新。
- Local Compose startup RED：`python -m pytest backend/tests/test_container_runtime.py -q` 退出码 1，新增 `test_backend_app_imports_from_clean_process` 复现 `ImportError: cannot import name 'uuid_str' from partially initialized module 'app.models.user'`。
- Local Compose startup GREEN：`python -m pytest backend/tests/test_container_runtime.py -q` 退出码 0，3 passed。
- Local Compose startup backend verification：`python -m pytest backend/tests -q` 退出码 0，97 passed。
- Local Compose startup service verification：`docker compose up --build -d` 退出码 0，backend healthy，frontend started。
- Local Compose startup HTTP smoke：`curl.exe` 检查 `http://localhost:3000/`、`http://localhost:8000/health`、`http://localhost:9001/` 均返回 HTTP 200。
- Milestone 5 Task 3 post-doc verification：`python -m json.tool docs/feature-list.json` 退出码 0。
- Milestone 5 Task 3 post-doc verification：`python -m pytest backend/tests -q` 退出码 0，97 passed。
- Milestone 5 Task 3 post-doc verification：`npm.cmd --prefix frontend run test` 退出码 0，21 passed。
- Milestone 5 Task 3 post-doc verification：`npm.cmd --prefix frontend run lint` 退出码 0。
- Milestone 5 Task 3 post-doc verification：`npm.cmd --prefix frontend run build` 退出码 0，Next.js build succeeded with `/personas/[id]/chat` route.
- Milestone 5 Task 3 post-doc verification：`docker compose config` 退出码 0。
- Milestone 5 Task 3 post-doc verification：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，Milestone 5 banner、required files、JSON、97 backend tests、21 frontend tests、frontend lint/build、Compose config 均通过。
- Milestone 5 Task 3 post-doc verification：`git diff --check` 退出码 0，仅输出 LF-to-CRLF working-copy warnings。
- Milestone 5 Task 3 post-doc verification：stale-copy `rg` 无命中；`rg` 退出码 1 按“未找到过期声明”处理为预期结果。
- Milestone 6 Task 1 focused RED：`python -m pytest backend/tests/test_voice.py -q` 退出码 1，voice routes missing，3 failed / 1 passed。
- Milestone 6 Task 1 focused GREEN：`python -m pytest backend/tests/test_voice.py -q` 退出码 0，4 passed。
- Milestone 6 Task 1 backend full：`python -m pytest backend/tests -q` 退出码 0，101 passed。
- Milestone 6 Task 1 post-doc verification：`python -m json.tool docs/feature-list.json` 退出码 0。
- Milestone 6 Task 1 post-doc verification：`python -m pytest backend/tests/test_voice.py -q` 退出码 0，4 passed。
- Milestone 6 Task 1 post-doc verification：`docker compose config` 退出码 0。
- Milestone 6 Task 1 post-doc verification：`git diff --check` 退出码 0，仅输出 LF-to-CRLF working-copy warnings。
- Milestone 6 Task 1 post-doc verification：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，Milestone 6 Task 1 banner、required files、JSON、101 backend tests、21 frontend tests、frontend lint/build、Compose config 均通过。
- Milestone 6 Task 2 focused RED：`python -m pytest backend/tests/test_voice.py -q` 退出码 1，voice_models field and samples/clone routes missing，5 failed / 3 passed。
- Milestone 6 Task 2 focused GREEN：`python -m pytest backend/tests/test_voice.py -q` 退出码 0，8 passed。
- Milestone 6 Task 2 backend full current worktree：`python -m pytest backend/tests -q` 退出码 0，107 passed；该数量包含当前未纳入本次提交的 auth demo 测试。
- Milestone 6 Task 2 post-doc verification current worktree：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，Milestone 6 Task 2 banner、required files、JSON、107 backend tests、23 frontend tests、frontend lint/build、Compose config 均通过；backend/frontend 测试数量包含当前未纳入本次提交的 demo/auth 前端与后端测试。
- Milestone 6 Task 3 focused RED：`python -m pytest backend/tests/test_chat.py -q` 退出码 1，voice-message route missing，2 failed / 7 passed。
- Milestone 6 Task 3 fix loop：`python -m pytest backend/tests/test_chat.py -q` 退出码 1，auto_generated audio memory outranked confirmed memory；已修复 retrieval fact-priority。
- Milestone 6 Task 3 focused GREEN：`python -m pytest backend/tests/test_chat.py backend/tests/test_voice.py -q` 退出码 0，17 passed。
- Milestone 6 Task 3 backend full current worktree：`python -m pytest backend/tests -q` 退出码 0，109 passed；该数量包含当前未纳入本次提交的 auth demo 测试。
- Milestone 6 Task 3 post-doc verification current worktree：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，Milestone 6 Task 3 banner、required files、JSON、109 backend tests、23 frontend tests、frontend lint/build、Compose config 均通过；backend/frontend 测试数量包含当前未纳入本次提交的 demo/auth 前端与后端测试。

## Files Modified This Session

- `backend/app/main.py`
- `backend/app/api/routes/auth.py`
- `backend/app/schemas/auth.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_health.py`
- `frontend/src/components/DemoEntry.tsx`
- `frontend/src/lib/auth.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/persona.ts`
- `frontend/src/lib/materials.ts`
- `frontend/src/lib/jobs.ts`
- `frontend/src/lib/memories.ts`
- `frontend/src/lib/profile.ts`
- `frontend/src/lib/chat.ts`
- `frontend/app/layout.tsx`
- `frontend/app/globals.css`
- `frontend/app/page.tsx`
- `frontend/app/login/page.tsx`
- `frontend/app/register/page.tsx`
- `frontend/app/dashboard/page.tsx`
- `frontend/app/personas/new/page.tsx`
- `frontend/app/personas/[id]/page.tsx`
- `frontend/app/personas/[id]/uploads/page.tsx`
- `frontend/app/personas/[id]/jobs/page.tsx`
- `frontend/app/personas/[id]/memories/page.tsx`
- `frontend/app/personas/[id]/profile/page.tsx`
- `frontend/app/personas/[id]/chat/page.tsx`
- `frontend/tests/auth.test.mjs`
- `frontend/tests/routes.test.mjs`

## Milestone 7 Task 2 Update - 2026-07-04

### 本次完成内容

- 完成前端 `/personas/{id}/avatar` 3D 形象设置页：读取人物、avatar config 和图片资料；支持选择默认纪念形象、从图片资料发起 mock 3D 生成、展示 PRD 失败提示、状态、模型记录和 model_url。
- 接入 Three.js 头像/半身 mock 预览：包含待机、眨眼、微笑、点头和简化口型测试，保持 MVP 范围为头像/半身和 mock 预览。
- 人物记忆空间与对话页新增「3D 形象」入口，并清理旧的“3D 展示尚未实现”前端文案。
- 新增 `frontend/src/lib/avatar.ts` 与 `frontend/tests/avatar.test.mjs`，补齐 routes/API 路径测试；为当前前端 lint 覆盖到的 `MemorySpace` 图片组件切换到 `next/image`，避免 `<img>` 警告阻断 `--max-warnings=0`。
- 同步 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md`、`docs/平台说明.md`、`docs/init.sh` 和 SDD 账本。

### 修改文件

- `frontend/src/lib/avatar.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/routes.ts`
- `frontend/src/lib/memory-space.ts`
- `frontend/src/components/MemorySpace.tsx`
- `frontend/app/page.tsx`
- `frontend/app/personas/[id]/avatar/page.tsx`
- `frontend/app/personas/[id]/page.tsx`
- `frontend/app/personas/[id]/chat/page.tsx`
- `frontend/tests/avatar.test.mjs`
- `frontend/tests/routes.test.mjs`
- `frontend/public/memory-space/grandmother-tea.jpg`
- `frontend/public/memory-space/family-album.jpg`
- `frontend/public/memory-space/family-living-room.jpg`
- `frontend/public/memory-space/memory-string-lights.jpg`
- `frontend/package.json`
- `frontend/package-lock.json`
- `docs/README.md`
- `docs/feature-list.json`
- `docs/prd-checklist.md`
- `docs/progress.md`
- `docs/平台说明.md`
- `docs/init.sh`

### 验证记录

- Milestone 7 Task 2 RED：`npm.cmd --prefix frontend run test` 退出码 1，缺少 `frontend/src/lib/avatar.ts`；同时当前测试通配符覆盖到既有未跟踪 `frontend/tests/memory-space.test.mjs`，提示缺少 `frontend/src/lib/memory-space.ts`。
- Milestone 7 Task 2 helper GREEN：`npm.cmd --prefix frontend run test` 退出码 0，40 passed。
- Milestone 7 Task 2 frontend verification：`npm.cmd --prefix frontend run test` 退出码 0，42 passed。
- Milestone 7 Task 2 frontend lint：`npm.cmd --prefix frontend run lint` 退出码 0。
- Milestone 7 Task 2 frontend build：`npm.cmd --prefix frontend run build` 退出码 0，Next.js build succeeded with `/personas/[id]/avatar` route。
- Milestone 7 Task 2 browser smoke：临时 mock API + 当前工作树 Next dev server，1280x720 截图可见 Three.js 头像；canvas 区域截图像素统计 `sampledPixels=6624`、`colorBuckets=57`、`darkSamples=11`、`skinToneSamples=345`。
- Milestone 7 Task 2 browser smoke：390x844 移动视口滚动到 canvas，截图可见头像/半身；canvas 区域截图像素统计 `sampledPixels=5655`、`colorBuckets=113`、`darkSamples=27`、`skinToneSamples=1069`。
- Milestone 7 Task 2 unified harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，Milestone 7 Task 2 banner、required files、JSON、116 backend tests、42 frontend tests、frontend lint/build、Compose config 均通过。
- Milestone 7 Task 2 diff check：`git diff --check` 退出码 0，仅输出 LF-to-CRLF working-copy warnings。
- Milestone 7 Task 2 review fix：复审发现沉浸式人物记忆空间未暴露 `/personas/{id}/avatar` 入口，且范围提示仍写“3D 数字人尚未实现”；已在 `MemoryActionCard` 网格新增「设置 3D 形象」入口，补充 `MEMORY_SPACE_ACTIONS.avatar`，并把范围提示改为 mock 3D 已接入、真实 provider/对话页联动/导出未实现。
- Milestone 7 Task 2 review fix verification：`npm.cmd --prefix frontend run test` 退出码 0，42 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，`/personas/[id]` 和 `/personas/[id]/avatar` 构建通过。
- Milestone 7 Task 2 final unified harness after review fix：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，116 backend tests、42 frontend tests、frontend lint/build、Compose config 均通过。
- Milestone 7 Task 2 final diff check after review fix：`git diff --check` 退出码 0，仅输出 LF-to-CRLF working-copy warnings。

### 当前残余风险

- `/personas/{id}/avatar` 当前渲染的是 Three.js mock 头像/半身，不加载真实 GLB，不代表真实 3D provider 质量。
- Task 2 收尾时对话页仅提供 3D 形象入口；Task 3 已补齐 selected mock 数字人展示和语音播放状态口型联动。
- 浏览器烟测使用临时 mock API 绕开本地 3101 与 Docker 后端 CORS 端口差异；后续如需完整服务级浏览器验收，应重建 Docker 前端镜像或更新本地 CORS/端口配置后再测。
- `frontend/public/memory-space/*.jpg` 是为当前未跟踪 memory-space 测试提供的占位本地文件，只用于文件存在性测试，不代表最终视觉素材质量。
- 前端依赖树仍有 2 个 moderate severity npm audit findings，未在本任务处理。

### 下一步

- Milestone 7 对话页 mock 数字人展示和播放状态口型联动已由 Task 3 补齐；当前下一步转入 Milestone 8 回忆讲述与导出/删除关键数据。
- `frontend/tests/persona.test.mjs`
- `frontend/tests/materials.test.mjs`
- `frontend/tests/memories.test.mjs`
- `frontend/tests/profile.test.mjs`
- `frontend/tests/chat.test.mjs`
- `backend/app/models/user.py`
- `backend/tests/test_container_runtime.py`
- `backend/app/api/routes/voice.py`
- `backend/app/schemas/voice.py`
- `backend/app/services/voice.py`
- `backend/tests/test_voice.py`
- `docs/superpowers/plans/2026-07-04-milestone-6-voice-tts.md`
- `docs/progress.md`
- `docs/README.md`
- `docs/feature-list.json`
- `docs/prd-checklist.md`
- `docs/progress.md`
- `docs/平台说明.md`
- `docs/superpowers/plans/2026-07-04-milestone-5-chat-agent.md`
- `docs/init.sh`
- `frontend/app/page.tsx`
- `backend/app/api/routes/chat.py`
- `backend/app/schemas/chat.py`
- `backend/app/services/chat.py`
- `backend/app/providers/gateway.py`
- `backend/app/main.py`
- `backend/tests/test_chat.py`
- `backend/tests/test_provider_gateway.py`
- `frontend/app/personas/[id]/chat/page.tsx`
- `frontend/app/personas/[id]/memories/page.tsx`
- `frontend/app/personas/[id]/page.tsx`
- `frontend/app/personas/[id]/profile/page.tsx`
- `frontend/src/lib/chat.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/routes.ts`
- `frontend/tests/chat.test.mjs`
- `frontend/tests/routes.test.mjs`
