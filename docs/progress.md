# Session Progress Log

## Current State

- 项目：可信人格记忆Agent
- 当前阶段：以当前工作区为基础完成 yawen 星空前端交互迁移、长期/短期记忆 Markdown 上下文、Memory Audit v2 星空集成和页面路径与入口重编排。当前前端不展示登录/注册、登录态差异、数据设置页、模型设置页或独立 `/personas/{id}/stories` 页面；无 token 时透明调用现有 `POST /api/auth/demo` 获取 demo token。
- 当前活跃功能：星空首页、Dashboard、创建星星页、人物详情、资料解析与审核、任务、记忆档案馆、对话、遗憾对话室、心愿延续引导、声音（含可选 MiniMax 中文默认 TTS）和 3D 形象页面；顶部导航固定为产品级入口 `首页 / 产品介绍 / 创建档案 / 我的星空`，人物详情页下方资料、记忆和互动功能卡片作为人物内功能入口，各人物内功能页不再展示人物工作台块。`/personas/{id}/uploads` 承接资料上传、结构化记忆 Markdown、分类记忆卡片审核/星标、唯一“记忆可信度”和“完成审核，点亮星星”，不再提供档案摘要手动保存或重生成；`profile.profile_summary` 由上传解析后的 `memory_document_generation` 自动生成并在人物详情页展示；`/personas/{id}/memories` 只承接回忆讲述和语义搜索，进入页面会幂等补足最多三段锚定真实已审核记忆的默认回忆，用户点击“让TA讲一段回忆”会按关键词追加新故事；`/personas/{id}/profile` 仅作为兼容深链重定向到 uploads。对话页收口为三模式对话和共享 `AvatarStage` 数字人舞台，视频手势模式已接入浏览器本地摄像头识别和 GLB 动作反馈；形象页上传 GLB 模型后可替换星空空态，chat/regrets/wishes 共享同一 GLB 展示；创建星星页保留后端必需 `age` 字段，提交 `language=zh-CN`、默认说话风格、情绪边界和禁用表达，创建成功后通过现有资料上传 API 上传已选文件并进入 uploads。后端注册/登录、profile API、Memory Audit v2 审计 API、Persona Engine 显式画像分析、导出/删除、provider settings、stories API 和长期/短期记忆 Markdown 上下文仍保留；遗憾对话室和心愿延续引导复用现有 messages endpoint，但通过 conversation kind/context_kind 隔离普通聊天、遗憾对话和心愿引导上下文，不新增独立遗憾记录模型、心愿数据模型、提醒策略或长期 P1 心愿系统。
- 当前 UX 打磨补充：旧大块人物工作台导航仍不恢复；人物总览和人物子页不再展示统一人物工具栏，“当前星星”和子页快速切换栏已移除，人物子页保留单一“返回人物总览”入口，人物详情页下方功能卡片作为内部入口。`StarNav` 支持当前路由高亮和移动端紧凑菜单；创建页移动端保存操作固定在底部；uploads 已有资料超过 2 条时默认折叠为 2 条并提供展开/收起；主对话、遗憾和心愿页面使用共享对话工作区，消息只在内部滚动，输入栏保持可操作；数字人舞台始终可见，窄屏上下堆叠、`xl` 宽屏左右等高展示；旧 `/personas/{id}/stories` 深链重定向到 `/personas/{id}/memories`。
- 当前默认人物补充：`GET /api/personas` 会为当前用户幂等补齐私有 active「外婆」和「郑木生」，demo 用户、注册用户和既有用户都适用；软删除默认人物后再次进入 Dashboard 会重建新的 active 副本。该 seed 直接写入 succeeded 资料、ParsedChunk、confirmed MemoryCard、PersonaProfile 和 trust，不在 Dashboard 请求中调用真实 LLM/provider。

## Latest Session Update - 2026-07-05 Dashboard 默认双人物种子

- 根据用户计划，本次为 `/dashboard` 和 `GET /api/personas` 增加每用户私有默认人物 seed：默认 active「外婆」（关系外婆）和「郑木生」（关系爷爷）都由后端确定性写入，覆盖 demo 用户、正式注册用户和既有用户。
- 后端新增 `backend/app/services/default_personas.py`，定义 grandmother 与 zheng_musheng 两个 seed，直接创建 `Persona`、`SourceMaterial(parse_status=succeeded)`、`ParsedChunk`、`MemoryCard(status=confirmed)`、`PersonaProfile` 和 trust；记忆卡片保留 `source_material_id`、`parsed_chunk_id`、`source_quote` 和 `source_location`，保证 uploads/memories/chat 仍可追溯。
- `GET /api/personas` 在查询前调用 `ensure_default_personas_for_user()` 并提交事务；已有同名同关系 active 默认人物时复用，不重复创建；用户软删除默认人物后，下次请求会创建新的 active 副本。
- `POST /api/auth/demo` 改为复用同一默认 seed 服务，不再走 `create_manual_material()` 或 `run_material_parse_job()`；响应 schema 保持兼容，`demo_persona_id` 继续返回「外婆」id，demo 用户创建后立即拥有「外婆」和「郑木生」两个人物。
- TDD RED：`python -m pytest backend/tests/test_auth.py backend/tests/test_personas.py -q` 先 5 failed，命中 demo 只返回「外婆」、注册用户没有默认人物、重复 list/删除补回/郑木生 seed 内容都缺失。
- 聚焦 GREEN：`python -m pytest backend/tests/test_auth.py backend/tests/test_personas.py -q` 66 passed。
- 全量回归先发现 1 个旧断言需要同步新语义：清空当前账号数据后再请求 `/api/personas` 会补回默认「外婆」和「郑木生」，不再返回空列表；已更新 `backend/tests/test_settings_data.py`，同时确认其他用户已有数据不受影响。
- 收尾验证：`python -m pytest backend/tests/test_settings_data.py::test_clear_current_account_data_soft_deletes_owned_domain_records -q` 1 passed；`python -m pytest backend/tests -q` 259 passed；`python -m json.tool docs/feature-list.json` 退出码 0。
- 服务与浏览器 smoke：`docker compose build backend` 退出码 0；`docker compose up -d --no-deps --force-recreate backend` 退出码 0；`http://localhost:8000/health` 返回 `{"status":"ok"}`；应用内浏览器清空 `localStorage["persona_memory_agent_token"]` 后刷新 `http://localhost:3000/dashboard`，页面自动创建新 demo token，并显示「郑木生」和「外婆」两张人物卡。
- 已同步 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md`、`docs/平台说明.md` 和本进度账本；本次仍遵守仓库规则，未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 遗憾/心愿记忆库候选预提取

- 根据用户计划，本次为 `/personas/{id}/regrets` 和 `/personas/{id}/wishes` 增加空对话开场候选预提取，不新增独立遗憾记录模型、心愿数据模型、CRUD、提醒策略或长期 P1 行动系统。
- 后端新增 `POST /api/personas/{id}/guided-memory-candidates` 和 `guided_memory_extraction` 文本能力；候选只从当前用户当前人物 `confirmed/corrected` 且未删除的 `MemoryCard` 提取，MiniMax/OpenAI-Next 可用时走文本模型，未配置或失败时使用确定性关键词兜底。拒绝、停用、删除、跨用户或待审核记忆不会进入候选。
- `MessageSend` 新增可选 `guided_memory_ids`。用户点选候选并发送后，后端只把这些来源记忆纳入本轮 regrets/wishes guided chat 上下文、`metadata.memory_context.selected_memory_ids` 和 citations；未点选候选时保持原有上下文隔离。
- 前端 `GuidedExperiencePage` 在当前 guided conversation 还没有消息且候选非空时展示候选卡片；点击候选只填充输入框并记录来源记忆 id，不自动发送；空候选时继续展示原 opening message。
- TDD RED：`python -m pytest backend/tests/test_guided_memory.py backend/tests/test_provider_gateway.py backend/tests/test_minimax_provider.py backend/tests/test_openai_next_provider.py -q` 先 7 failed，命中 endpoint 404、`guided_memory_ids` 未生效和 provider capability 缺失；`npm.cmd --prefix frontend run test -- guided-experiences.test.mjs chat.test.mjs` 先 3 failed，命中 API helper、页面候选和发送参数缺失。
- 聚焦 GREEN：同一后端 guided/provider 命令 39 passed；同一前端 guided/chat 命令实际执行当前全量脚本，结果 132 passed。
- 已同步 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md`、`docs/平台说明.md` 和本进度账本。
- 收尾验证：`python -m json.tool docs/feature-list.json` 退出码 0；`python -m pytest backend/tests/test_guided_memory.py backend/tests/test_chat.py backend/tests/test_provider_gateway.py backend/tests/test_minimax_provider.py backend/tests/test_openai_next_provider.py -q` 61 passed；`npm.cmd --prefix frontend run test` 132 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 记忆档案馆默认三段回忆

- 根据用户计划，本次为 `/personas/{id}/memories` 增加后端幂等默认故事 seed：新增 `POST /api/personas/{id}/stories/seed`，不新增数据库表或迁移，默认故事身份写入 `MemoryStory.metadata_json.story_kind=default_memory_story`，并记录 `seed_memory_id` 与 `seed_index`。
- 后端实现：`seed_default_stories()` 只使用 confirmed/corrected 且未删除的真实 `MemoryCard`，优先按现有 reviewed memory 排序选择最多 3 条不同来源；每条默认故事使用对应记忆标题作为 theme，并把该记忆排在候选来源首位。已有 3 条默认故事时不重复生成，已有 1-2 条时只补缺口；无已审核记忆时返回现有 story 列表空态，不在页面加载时抛 400。用户手动 `POST /stories` 仍按输入 theme 追加故事，不计入默认三段。
- 前端实现：`frontend/src/lib/stories.ts` 新增 `ensureDefaultStories(personaId)` 调用 seed endpoint；memories 页加载时从 `listStories()` 改为 `ensureDefaultStories()`，加载文案为“正在整理三段回忆...”，故事区展示全部 stories，不再 `slice(0, 3)`，并移除旧死分支；空态改为提示先去资料页审核记忆。
- TDD RED：`python -m pytest backend/tests/test_stories.py -q` 先 3 failed / 9 passed，均为 `/stories/seed` 404；`npm.cmd --prefix frontend run test -- stories.test.mjs memories.test.mjs` 先 126 passed / 2 failed，命中 `ensureDefaultStories` 未导出和 memories 页仍未使用 seed、仍切片展示。
- 聚焦 GREEN：`python -m pytest backend/tests/test_stories.py -q` 12 passed；`npm.cmd --prefix frontend run test -- stories.test.mjs memories.test.mjs` 因当前脚本执行全量测试，结果 130 passed。
- 已同步 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md`、`docs/平台说明.md` 和本进度账本。
- 收尾验证：`python -m json.tool docs/feature-list.json` 退出码 0；`python -m pytest backend/tests/test_stories.py backend/tests/test_minimax_provider.py backend/tests/test_memory_markdown.py -q` 33 passed；`npm.cmd --prefix frontend run test` 130 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`docker compose up --build -d backend frontend` 退出码 0，backend healthy、frontend started；HTTP/API smoke 中 `/health` 返回 `ok`、`http://localhost:3000` 返回 200，空人物调用 `POST /api/personas/{id}/stories/seed` 返回 200 且 `items=[]`，未触发真实 LLM/TTS。
- 浏览器 smoke：本轮工具发现只暴露 Node REPL，未暴露 in-app Browser 控制工具；未使用外部浏览器绕过该限制。因此未完成“进入 memories 页面前可见三段默认故事、点击后追加关键词故事、移动视口无横向溢出”的浏览器层 smoke。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 uploads 异步解析与同源结构化文档

- 根据用户计划，本次修复两个核心问题：uploads 结构化记忆文档不再展示 latest material job 里的旧 Markdown，而是由当前 active MemoryCard 和 succeeded materials 渲染；资料上传/手动资料/重新解析/job retry 不再同步等待第三方模型链路完成，API 返回 pending/retrying job 后由后台 helper 执行解析。
- 后端改动：`create_manual_material`、`create_uploaded_material`、`queue_material_parse` 只创建 `SourceMaterial + AIJob` 并提交事务；materials/jobs API 用 `BackgroundTasks` 调度 `run_material_parse_job_by_id`；test 环境不自动跑后台任务，测试显式调用 `run_parse_job` 或服务 helper。`run_parse_job` 开始前检查 canceled/deleted 状态，完成 MemoryCard 创建后先把 material 标记为 succeeded，再生成 profile summary/trust job output。
- 文档同源改动：`build_memory_document_payload` 的资料来源只包含 succeeded materials；`_normalize_memory_document_output` 在 service 层忽略 provider 返回的结构化文档，始终从 payload 中的 active MemoryCard 生成 `structured_memory_document_json` 和 `structured_memory_md`；Markdown 不再直接注入 persona_card 基础字段，文档条目 id 来自 MemoryCard。MiniMax/mock `memory_document_generation` provider 契约收紧为只输出 `profile_summary`、trust、理由和建议。
- 记忆抽取丰富度：mock memory extraction 从长文本最多抽取 12 条句子级候选；DashScope memory extraction prompt 明确长文本要拆成原子事实/关系/偏好/习惯/表达/共同经历，文档阶段不补造审核卡片。
- 前端改动：uploads 的结构化文档由 `renderStructuredMemoryMd(memories, materials)` 渲染，不再使用 `latestStructuredMemoryMd(materials)`；提交文件或手动资料后按钮快速恢复，页面显示“资料已加入，后台解析中”，轮询 materials/memories/profile，直到本次 job 进入 succeeded/failed/canceled 或超时提示稍后刷新。旧的固定 timer 假进度和“已完成解析”提交提示已移除。
- TDD/验证：先运行聚焦后端用例复现旧同步断言和 provider 文档补造问题失败；实现后 `python -m pytest backend/tests/test_materials.py backend/tests/test_parsing.py backend/tests/test_profile.py backend/tests/test_provider_gateway.py backend/tests/test_dashscope_provider.py -q` 45 passed；provider 契约调整后 `python -m pytest backend/tests/test_provider_gateway.py backend/tests/test_minimax_provider.py -q` 30 passed；`python -m pytest backend/tests -q` 247 passed；`npm.cmd --prefix frontend run test` 129 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`python -m json.tool docs/feature-list.json` 退出码 0。服务刷新：`docker compose build backend frontend` 退出码 0；`docker compose up -d --no-deps --force-recreate backend frontend` 退出码 0；`http://localhost:8000/health` 返回 200；`/personas/18b88e96-5633-4d75-b77a-0ad1988a846a/uploads` 返回 200；`docker compose ps` 显示 backend healthy、frontend started。应用内浏览器 smoke：uploads 页面可见“资料解析与审核”“结构化记忆文档”“上传珍贵回忆”四宫格、“手动资料”和“记忆可信度”，不显示摘要编辑入口或 `MiniMax`/`strict JSON` 技术错误。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 uploads 已有资料折叠

- 根据用户计划，本次只调整 `/personas/{id}/uploads` 的“已有资料”展示高度，不改后端 API、数据库 schema、资料上传、解析任务、审核卡片或 `MaterialCard` 单卡结构。
- “已有资料”新增本地折叠状态和 `MATERIAL_PREVIEW_COUNT = 2`：资料超过 2 条时默认只显示前 2 条，按钮文案为“展开全部 N 条”；展开后显示全部资料并切换为“收起资料”，再次点击恢复 2 条。
- 折叠按钮使用 `aria-expanded` 与 `aria-controls="existing-materials-list"` 关联列表；资料数不超过 2 条时不显示该按钮。
- TDD RED：先更新 `frontend/tests/materials.test.mjs`，运行 `npm.cmd --prefix frontend run test -- materials.test.mjs` 退出码 1，命中缺少 `MATERIAL_PREVIEW_COUNT = 2`。
- 收尾验证：`npm.cmd --prefix frontend run test -- materials.test.mjs` 127 passed；`npm.cmd --prefix frontend run test` 127 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`python -m json.tool docs/feature-list.json` 退出码 0；`docker compose up --build -d frontend` 退出码 0，backend healthy、frontend started。
- 浏览器 smoke：应用内浏览器检查 `http://localhost:3000/personas/18b88e96-5633-4d75-b77a-0ad1988a846a/uploads`，默认 `visibleCards=2`、按钮“展开全部 7 条”、`aria-expanded=false`；点击后 `visibleCards=7`、按钮“收起资料”、`aria-expanded=true`；再次点击恢复 `visibleCards=2`，全程 `overflowX=0`。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 对话页布局高度与数字人展示

- 根据用户计划，本次只调整 chat / regrets / wishes 共用 `ConversationWorkspace` 布局，不改后端 API、数据库 schema、消息发送、语音、手势、TTS 或 GLB 加载能力。
- `ConversationWorkspace` 已移除 `avatarOpen` 状态、数字人折叠按钮和 `hidden lg:block` 折叠显示逻辑；数字人区域始终渲染可见。默认窄屏按对话框在上、数字人在下堆叠，`xl` 及以上使用左右双栏和 `items-stretch` 保持两侧卡片等高。
- 对话卡片移除 `max-h-[32rem]` 限制，改为 `min-h-[37rem]`、`xl:h-full`；消息列表继续使用 `conversation-scroll` 内部滚动，输入栏继续 `sticky bottom-0` 固定在对话卡片底部。chat 页的 `AvatarStage` 改为 `h-full xl:min-h-[37rem]`。
- TDD RED：先更新 `frontend/tests/ux-polish.test.mjs`，运行 `node --import tsx --test tests/ux-polish.test.mjs` 退出码 1，命中旧实现缺少 `items-stretch` 且仍包含折叠数字人逻辑。
- TDD GREEN：完成组件和 chat 接入调整后，`node --import tsx --test tests/ux-polish.test.mjs` 6 passed。
- 收尾验证：`npm.cmd --prefix frontend run test` 126 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`python -m json.tool docs/feature-list.json > $null` 退出码 0；`docker compose up --build -d frontend` 退出码 0，backend healthy、frontend started。
- 浏览器 smoke：应用内浏览器打开 `/personas/18b88e96-5633-4d75-b77a-0ad1988a846a/chat`，桌面 1280x720 下 `sideBySide=true`、左右高度差 `0px`、消息区高度 `709px`、无「数字人预览」、`overflowX=false`；390x844 下 `stacked=true`、输入框首屏可见可操作、数字人区域直接在对话框下方可见、`overflowX=false`；评论附近 793x860 下 `stacked=true`、无折叠按钮、`overflowX=false`。桌面因当前人物数字人说明文本较长，页面总高度超过一屏；滚动到输入区后 input 可见且 enabled，仍无横向溢出。
- 浏览器 smoke 继续抽查 `/regrets` 与 `/wishes` 390x844：均 `stacked=true`、数字人区域可见、无「数字人预览」、输入框首屏可见可操作、`overflowX=false`。当前 chat 数字人区域有 1 个 canvas；桌面截图中可见数字人区域 396x455 像素采样 `NonWhite=180180/180180`、`SampledUniqueColors=2929`，非空白。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 人物子页单一返回入口

- 根据用户计划，本次不恢复 `PersonaWorkspaceToolbar`、旧大块人物工作台或资料/任务/记忆/对话/声音/3D/遗憾/心愿快速切换，只为人物子页保留单一“返回人物总览”入口。
- 新增 `frontend/src/components/PersonaBackLink.tsx`，使用 `ROUTES.personaDetail(personaId)` 指向当前人物总览页；uploads、jobs、memories、chat、voice、avatar 和 `GuidedExperiencePage` 承载的 regrets/wishes 在页面标题或主工作区之前接入该入口。
- 人物总览页 `/personas/{id}` 不接入 `PersonaBackLink`，继续保留现有“返回我的星空”入口。
- TDD RED：`node --import tsx --test tests/ux-polish.test.mjs` 先退出码 1，命中 `PersonaBackLink.tsx` 尚不存在；新增组件和接入点后同命令 6 passed。
- 收尾验证：`npm.cmd --prefix frontend run test` 126 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`python -m json.tool docs/feature-list.json > $null` 退出码 0；`docker compose up --build -d frontend` 退出码 0，backend healthy、frontend started。
- 浏览器 smoke：应用内浏览器在桌面 1280x720 和移动 390x844 检查 `/uploads`、`/chat`、`/regrets`，每页 `backCount=1`、`visibleBackCount=1`、href 指向 `/personas/18b88e96-5633-4d75-b77a-0ad1988a846a`，点击后回到人物总览；均无“当前星星”和快速切换工具栏文本，`overflowX=false`。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。
- 当前产品介绍入口：顶部导航 `产品介绍` 指向独立 `/product-intro` 星空路演摘编页；首页 `/` 已恢复为简版 `#product-intro` 三卡产品概览。
- 当前产品目标：按 PRD 建设可信人格记忆数字人；当前代码覆盖项目初始化、基础连通、账号认证/API、免注册本地演示、人物创建/记忆空间、资料上传/任务队列、mock/可选 DashScope 真实解析、单资料严格六模块 JSON 记忆抽取、Memory Audit v2 审计/冲突/语义搜索/历史 API、上传解析后的 `memory_document_generation` 结构化记忆 Markdown 与唯一 trust 持久值、Persona Engine 显式画像分析、长期/短期 Markdown 记忆上下文、deterministic/mock fallback 与可选 MiniMax 文本对话、mock/可选 MiniMax 语音、GLB 形象上传与前端展示、视频手势本地识别与 GLB 动作反馈、后端故事/导出/删除/清空账号数据和 provider settings API。当前前端交互以 yawen 星空体验为准；Memory Audit v2 不包含 snapshot、rollback 或 persona drift。
- 当前文本生成 provider 补充：MiniMax 仍是 `chat_llm`、`story_generation`、`memory_context_compression`、`persona_profile_analysis` 和 `memory_document_generation` 的主 provider；本地已可通过 git 忽略的 `.env/runtime.env` 配置 `OPENAI_NEXT_API_KEY`、`OPENAI_NEXT_BASE_URL=https://api.openai-next.com/v1`、`OPENAI_NEXT_MODEL=gpt-5` 和 `OPENAI_NEXT_REQUEST_TIMEOUT_SECONDS=60` 作为 MiniMax 文本失败后的 OpenAI-Next text-only fallback。该 fallback 不用于 TTS、音色克隆、ASR、OCR、图片/视频理解或记忆抽取。
- 当前技术栈：Next.js 15、React 19、Three.js、FastAPI、SQLAlchemy、Alembic、PostgreSQL、Redis、MinIO、Docker Compose、DashScope/Qwen、MiniMax、ffmpeg
- 当前部署入口：本地调试继续使用 `http://localhost:3000` 和 `http://localhost:8000/health`；ECS 直连端口部署使用 `http://<ECS公网IP>:3000` 作为网页远程访问地址、`http://<ECS公网IP>:8000/health` 作为后端健康检查地址。`<ECS公网IP>` 只是占位符，部署时必须替换为阿里云 ECS 实际公网 IPv4；前端 `NEXT_PUBLIC_API_BASE_URL` 在 Docker build 期注入，公网 IP 或后端端口变化后必须重新带 `--build` 启动。
- 当前完整基线验证入口：`docs/init.sh`；仅在用户明确要求时运行，agent 任何情况下都不要主动运行。
- 当前下一步边界：不自动推进 P1/P2 功能点；只在用户明确要求时做已完成功能的验收、修复、文档同步或恢复指定范围开发。若恢复数据设置、模型设置、独立故事页前端入口、Memory Audit snapshot/rollback 或 persona drift，需要重新纳入产品范围并同步 `feature-list.json`。

## Latest Session Update - 2026-07-05 删除人物子页统一工具栏

- 根据用户计划，本次删除人物内统一工具栏：不再展示“返回人物总览”“当前星星”以及资料/任务/记忆/对话/声音/3D/遗憾/心愿快速切换；不新增替代返回按钮、面包屑或快捷切换区。
- 代码改动：删除 `frontend/src/components/PersonaWorkspaceToolbar.tsx`；移除人物总览、uploads、jobs、memories、chat、voice、avatar 以及 regrets/wishes 共用 `GuidedExperiencePage` 的 toolbar import 和 JSX 调用。
- 测试同步：`frontend/tests/ux-polish.test.mjs` 改为断言人物相关页面不得包含 `PersonaWorkspaceToolbar`、`返回人物总览`、`当前星星`，并要求 toolbar 组件文件不存在。
- 文档同步：更新 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md` 和本进度账本，移除紧凑人物工具栏作为当前事实的描述，保留人物详情页下方功能卡片作为内部入口。
- TDD RED：`npm.cmd --prefix frontend run test -- ux-polish.test.mjs` 先退出码 1，命中 `PersonaWorkspaceToolbar.tsx` 仍存在；删除组件和调用点后同名用例进入通过状态。
- 收尾验证：`npm.cmd --prefix frontend run test -- ux-polish.test.mjs memory-space.test.mjs persona.test.mjs routes.test.mjs` 126 passed；`npm.cmd --prefix frontend run test` 126 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`python -m json.tool docs/feature-list.json` 退出码 0；`docker compose up --build -d frontend` 退出码 0。
- 浏览器 smoke：应用内浏览器检查 `http://localhost:3000/personas/18b88e96-5633-4d75-b77a-0ad1988a846a` 和 `/uploads` 子页，均无“返回人物总览”“当前星星”工具栏文本，`overflowX=0`。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 首页首屏 AI 模拟提示卡片删除

- 根据浏览器评论，本次只删除首页首屏标题和两个大 CTA 之间的 `AI 模拟体验：回复基于你上传和审核过的资料生成。` 胶囊提示卡片；两个首屏 CTA、路由、后端 API、人物内功能和 `feature-list.json` 均不改。
- `frontend/app/page.tsx` 已移除该 hero `<p>`；`frontend/tests/homepage-cta.test.mjs` 和 `frontend/tests/ux-polish.test.mjs` 已同步为断言首页不再出现该提示文案。
- TDD RED：`npm.cmd --prefix frontend run test -- homepage-cta.test.mjs` 先退出码 1，命中旧提示卡片仍存在；删除卡片并同步测试后，`node --import tsx --test tests/homepage-cta.test.mjs` 6 passed。
- 验证：`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`rg "AI 模拟体验|回复基于你上传和审核过的资料生成|rounded-full border border-starGold/18" frontend/app/page.tsx` 无命中。
- 当前完整 `npm.cmd --prefix frontend run test` 仍有 1 个无关失败：`frontend/tests/ux-polish.test.mjs` 的 `persona feature pages do not render the persona workspace toolbar` 断言要求 `PersonaWorkspaceToolbar.tsx` 不存在，但当前工作区仍有该组件且多个人物功能页仍引用它；本次未处理人物页 toolbar 范围。
- 浏览器 smoke：`docker compose build frontend` 后 `docker compose up -d --no-deps --force-recreate frontend` 成功，`curl http://localhost:3000/` 无旧提示文案；应用内浏览器新标签复验 `http://localhost:3000/`，`hasAiNotice=false`、`hasNoticeBody=false`、`heroPillCount=0`、两个 CTA 仍存在、横向溢出 0。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 星空前端 UX 路演打磨

- 本次按用户给定计划做前端展示和交互打磨，不新增后端 API、数据库 schema、真实 AI、真实声音或真实 3D 能力，也不恢复登录/注册/设置页或独立 stories 产品入口。
- 全局 `StarNav` 支持当前路由高亮和移动端紧凑菜单；新增紧凑人物工作区工具栏，在人物总览、资料审核、任务、记忆档案馆、主对话、声音、3D、遗憾和心愿页面提供返回人物总览和当前人物子页切换。
- 首页移动端上移标题、CTA 和 AI 模拟体验提示；Dashboard 卡片增加明确“进入星星”主操作；创建页移动端保存操作固定在底部；uploads 优先展示上传/手动资料入口；任务页增加状态摘要；声音和 3D 页面移动端优先展示当前状态与主要操作。
- 主对话、遗憾和心愿页面改用共享对话工作区：消息列表内部滚动、输入栏固定在面板底部、发送后滚动消息容器而不是页面；主对话增加快捷问题 chips，移动端数字人预览收进折叠区。
- 记忆档案馆故事卡片接入已有收藏接口，来源改为可展开摘要；旧 `/personas/{id}/stories` 作为兼容深链重定向到 `/personas/{id}/memories`。
- 新增/调整测试覆盖 `StarNav` 移动菜单、人物工具栏、对话工作区、创建页移动端固定保存操作、stories 深链重定向和 chat 快捷问题；按仓库规则，本次未运行 `docs/init.sh`。
- 收尾验证：`npm.cmd --prefix frontend run test` 126 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，构建包含 `/personas/[id]/stories` 兼容路由；`python -m json.tool docs/feature-list.json > $null` 退出码 0。刷新运行环境时 `docker compose up --build -d frontend` 已构建 frontend 镜像，但启动阶段因 transient backend 容器名冲突退出 1；随后 `docker compose up -d --no-deps frontend` 退出码 0，`docker compose ps` 显示 backend healthy、frontend 运行，`http://localhost:8000/health` 返回 `{\"status\":\"ok\"}`，`http://localhost:3000` 返回 200 且首页包含 “AI 模拟体验”；`/personas/{id}/stories` HTTP 307 重定向到 `/personas/{id}/memories`。

## Latest Session Update - 2026-07-05 结构化记忆文档 JSON 契约修复

- 根因定位：`memory_extraction` 已从单资料识别文本生成严格六模块 JSON 和 MemoryCard，但后续 `memory_document_generation` 仍要求 MiniMax 在 JSON 字段中直接返回大段 `structured_memory_md` Markdown；模型一旦输出 `<think>`、代码块、前后说明或未转义多行 Markdown，旧解析器只做 `json.loads(content.strip())`，三次 repair 后仍会在 uploads 材料卡片展示 `MiniMax memory document response must be strict JSON` 等技术错误。
- 后端修复：`memory_document_generation` 的权威输出改为 `structured_memory_document_json`、`profile_summary`、trust 和 suggestions；MiniMax 文档链路启用 JSON object 响应约束，解析前清理 `<think>`、Markdown fence 和前后说明并提取首个 JSON object，再校验固定六模块结构。`structured_memory_md` 改为后端根据结构化 JSON 确定性渲染，继续写入 job output 供前端兼容展示。
- 可恢复失败处理：如果 provider 文档 JSON 仍不可用，但资料已经生成 ParsedChunk 和 MemoryCard，后端会用已生成的记忆卡片结构构造同样的 document JSON、Markdown、profile_summary 和 trust；provider 错误只保存在 job metadata，不再阻断资料解析或向普通用户展示。
- 前端修复：uploads 材料卡片只展示真正资料解析 failed job 的错误；不再读取或展示 `memory_document_error`、`memory_document_warning`、`MiniMax`、`strict JSON` 等结构化文档 provider 诊断。对于历史 job 中仅由 memory document JSON provider 诊断造成的失败文案，材料卡片也会按用户侧可恢复状态处理，不再显示技术失败。记忆卡片和结构化文档展示仍保留。
- 文档同步：更新 `docs/README.md`、`docs/feature-list.json` 新增 `feat-052`、`docs/prd-checklist.md`、`docs/平台说明.md`、`docs/可信人格记忆Agent_mvp_prd.md` 和本进度账本，统一说明 Markdown 是后端渲染产物，结构化 JSON 是权威数据。
- TDD RED：先运行聚焦用例验证旧实现会失败，包括 MiniMax `<think>` + fenced JSON 解析、provider JSON 失败后的 parse fallback、mock gateway 文档 JSON 输出，以及前端隐藏 provider 技术错误测试。
- 收尾验证：`python -m json.tool docs/feature-list.json` exit 0；`python -m pytest backend/tests/test_provider_gateway.py backend/tests/test_minimax_provider.py backend/tests/test_parsing.py backend/tests/test_materials.py backend/tests/test_profile.py backend/tests/test_memories.py backend/tests/test_memory_markdown.py backend/tests/test_chat.py backend/tests/test_stories.py -q` 99 passed；`python -m pytest backend/tests -q` 245 passed；`npm.cmd --prefix frontend run test` 125 passed；`npm.cmd --prefix frontend run lint` exit 0；`npm.cmd --prefix frontend run build` exit 0。
- 按仓库规则，本次没有运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 OpenAI-Next 文本生成兜底

- 本次新增 OpenAI-Next text-only fallback，不新增数据库迁移、HTTP 路由或前端页面。MiniMax 仍是文本生成主 provider；只有 `chat_llm`、`story_generation`、`memory_context_compression`、`persona_profile_analysis` 和 `memory_document_generation` 的 MiniMax 调用抛错时，且本地配置 `OPENAI_NEXT_API_KEY`、`OPENAI_NEXT_BASE_URL`、`OPENAI_NEXT_MODEL` 后，Provider Gateway 才追加一次 OpenAI-Next `/chat/completions` 兜底。
- OpenAI-Next 不用于 `tts`、`voice_clone`、ASR、OCR、图片/视频理解或 `memory_extraction`。未配置 OpenAI-Next 时保持既有 MiniMax 异常/服务层 fallback 行为；test 环境仍使用 deterministic mock。
- 实现文件：`backend/app/providers/openai_next.py`、`backend/app/providers/gateway.py`、`backend/app/core/config.py`、`backend/app/services/provider_settings.py`。provider settings allowlist 和 GET 报告新增 `openai_next_text_fallback`，响应只显示 configured/missing 和非 secret 设置，不返回原始 key。
- 本地未提交 `.env/runtime.env` 已写入 `OPENAI_NEXT_API_KEY`、`OPENAI_NEXT_BASE_URL=https://api.openai-next.com/v1`、`OPENAI_NEXT_MODEL=gpt-5` 和 `OPENAI_NEXT_REQUEST_TIMEOUT_SECONDS=60`；tracked docs 只记录变量名和占位值，不写真实 key。
- 文档同步：`docs/README.md`、`docs/feature-list.json` 新增 `feat-053`、`docs/prd-checklist.md`、`docs/平台说明.md` 和本进度账本。
- TDD RED：`python -m pytest backend/tests/test_config.py backend/tests/test_provider_settings.py backend/tests/test_openai_next_provider.py backend/tests/test_provider_gateway.py -q` 先失败，命中 `app.providers.openai_next` 缺失。
- 聚焦 GREEN：同一命令随后 29 passed。
- 收尾验证：`python -m json.tool docs/feature-list.json` 退出码 0；`python -m pytest backend/tests -q` 246 passed；`docker compose config` 退出码 0。
- Live OpenAI-Next smoke：旧 OpenAI-Next key 使用 `POST /v1/chat/completions` 和 `from openai import OpenAI` SDK 写法均返回 401 `无效的令牌`；更换本地 `.env/runtime.env` 中的 `OPENAI_NEXT_API_KEY` 后，按 `base_url=https://api.openai-next.com/v1`、`client.chat.completions.create(model=\"gpt-5\")` 复测成功，模型返回 `openai-next-ok`。
- 本次未运行 `docs/init.sh`；按仓库规则只有用户明确要求完整基线验证时才运行。

## Latest Session Update - 2026-07-05 声音页短录音音色克隆失败修复

- 根因定位：最近真实 MiniMax `voice_clone` job 已不再是 `.webm` 格式问题，而是 provider 返回 `MiniMax request failed: voice duration too short`；对应浏览器录音已转成 `voice-sample-recording-1783198053821.wav` / `audio/wav`，实际时长约 6.54 秒。MiniMax voice clone 官方要求待克隆音频至少 10 秒，因此短录音进入克隆阶段后会失败并回退默认 TTS。
- 前端修复：`/personas/{id}/voice` 录音转 WAV 后记录 `AudioBuffer.duration`，创建音色样本前对录音或本地上传文件读取音频时长，低于 10 秒时阻止上传/创建样本并提示“MiniMax 音色克隆要求样本至少 10 秒”；录音预览区显示 WAV 文件大小和时长。克隆失败提示现在会把 MiniMax `voice duration too short` 转成中文可操作说明，不再只显示“音色克隆失败，已回退默认 TTS。”。
- 前端样本选择修复：`latestCloneSourceModel()` 默认优先选择最新 `sample_ready` 样本，避免刷新后反复拿最新 `clone_failed` 短样本重试；仍保留显式 preferred sample id 的重试能力。
- 后端修复：`clone_voice()` 在调用 provider 前对可读 WAV 样本做最少 10 秒预检；短 WAV 会写入 `provider_name=voice_preflight` 的 failed `clone_voice` job，标记样本 `clone_failed` 并回退 selected `default_tts`，不再把明显不符合 MiniMax 要求的短 WAV 发给第三方 provider。现有历史样本若容器重建后本地文件已不可读，会返回“无法读取 WAV 音频时长，请重新录制或上传 mp3/m4a/wav 人声音频。”。
- 文档同步：更新 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md` 和 `docs/平台说明.md`，统一说明声音页上传/录音样本需要满足 MiniMax 至少 10 秒要求，后端存在 `voice_preflight` 短 WAV 预检。
- TDD RED：`node --import tsx --test tests/voice.test.mjs` 先失败 3 项，命中默认选择 `clone_failed`、缺少短音频失败说明和缺少时长预检；`python -m pytest backend/tests/test_voice.py::test_clone_voice_short_wav_fails_before_minimax_and_explains_min_duration -q` 先失败，短 WAV 仍被 mock clone 成功。
- 聚焦 GREEN：`node --import tsx --test tests/voice.test.mjs` 15 passed；`python -m pytest backend/tests/test_voice.py::test_clone_voice_short_wav_fails_before_minimax_and_explains_min_duration -q` 1 passed；`python -m pytest backend/tests/test_voice.py -q` 15 passed；`python -m pytest backend/tests/test_minimax_provider.py -q` 15 passed。
- 收尾验证：`python -m json.tool docs/feature-list.json` 退出码 0；`python -m pytest backend/tests -q` 237 passed；`npm.cmd --prefix frontend run test` 119 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 服务与浏览器 smoke：`docker compose build backend frontend` 退出码 0；`docker compose up -d --no-deps --force-recreate backend frontend` 后 backend healthy、frontend started；`http://localhost:8000/health` 返回 `{"status":"ok"}`，当前 voice 页 HTTP 200。刷新应用内浏览器 `http://localhost:3000/personas/27e4e946-6b92-42a2-982c-fde85b36c284/voice` 后，页面可见“MiniMax 音色克隆要求样本至少 10 秒”，且当前状态没有旧的通用 fallback toast。未接受麦克风权限，未替用户伪造或上传新 TA 音频，也未触发真实 MiniMax 克隆。
- 本次未运行 `docs/init.sh`；按仓库规则只有用户明确要求完整基线验证时才运行。

## Latest Session Update - 2026-07-05 ECS 直连端口部署与远程访问地址同步

- 根据用户确认计划，本次只同步 ECS 直连端口部署配置和文档，不新增 HTTP API、数据库字段、前端产品入口、Nginx、HTTPS、域名或反向代理。最终远程网页地址模板为 `http://<ECS公网IP>:3000`，后端健康检查模板为 `http://<ECS公网IP>:8000/health`；调试阶段仍保留 `http://localhost:3000` 和 `http://localhost:8000/health`。
- `docker-compose.yml` 现在允许通过环境变量覆盖 `FRONTEND_URL`、`BACKEND_URL` 和 `NEXT_PUBLIC_API_BASE_URL`。前端服务把 `NEXT_PUBLIC_API_BASE_URL` 同时传入 build args 和运行期 environment；`frontend/Dockerfile` 在 `npm run build` 前声明并导出 `ARG/ENV NEXT_PUBLIC_API_BASE_URL`，避免 ECS 构建出的客户端仍指向 localhost。
- Compose 继续对外映射前端 `3000` 和后端 `8000`；PostgreSQL、Redis、MinIO API 和 MinIO Console 的宿主端口默认绑定到 `127.0.0.1`，分别为 `15432`、`6379`、`9000`、`9001`。文档明确 ECS 安全组只放行 3000/8000，不对公网放行基础设施端口。
- 恢复并更新根目录 `readme.md`，同步 `docs/README.md`、`docs/平台说明.md`、`docs/prd-checklist.md`、`docs/feature-list.json`、PRD 环境变量示例、`docs/init.sh` 手动提示和 `AGENTS.md` 命令说明。`.env/runtime.env` 仍是不提交文件，部署时需要写入 `FRONTEND_URL=http://<ECS公网IP>:3000`、`BACKEND_URL=http://<ECS公网IP>:8000`、`NEXT_PUBLIC_API_BASE_URL=http://<ECS公网IP>:8000` 和强随机 `JWT_SECRET`，并把 `<ECS公网IP>` 替换为真实公网 IP。
- TDD RED：`python -m pytest backend/tests/test_container_runtime.py -q` 先红，2 failed / 3 passed，命中 Compose 未支持公网 URL 覆盖和前端 Dockerfile 未在 build 期注入 `NEXT_PUBLIC_API_BASE_URL`。
- 聚焦 GREEN：`python -m pytest backend/tests/test_container_runtime.py -q` 5 passed。
- 收尾验证：`python -m json.tool docs/feature-list.json` 退出码 0；`python -m pytest backend/tests/test_container_runtime.py backend/tests/test_health.py -q` 7 passed；`node --import tsx --test tests/routes.test.mjs` 在 `frontend` 目录运行 18 passed；`NEXT_PUBLIC_API_BASE_URL=http://203.0.113.10:8000 npm.cmd --prefix frontend run build` 退出码 0；`docker compose config` 退出码 0；带示例公网变量 `FRONTEND_URL=http://203.0.113.10:3000`、`BACKEND_URL=http://203.0.113.10:8000`、`NEXT_PUBLIC_API_BASE_URL=http://203.0.113.10:8000` 的 `docker compose config` 退出码 0，并确认配置输出包含公网 URL、frontend build arg/runtime env 和基础设施端口 `host_ip: 127.0.0.1`。
- 按仓库规则，本次未运行 `docs/init.sh`。本轮未在真实 ECS 上启动服务，也未提交真实公网 IP、真实密钥或 `.env/runtime.env`。

## Latest Session Update - 2026-07-05 记忆档案馆回忆讲述与语义搜索收口

- 根据用户确认计划，本次只收口 `/personas/{id}/memories` 的“回忆讲述 + 语义搜索”，不恢复审核区、不恢复独立 stories 页面、不新增后端 API、数据模型或迁移。审核/纠错仍在 uploads 相关流程中，memories 页只负责基于已审核记忆讲述故事和检索可追溯记忆卡片。
- 后端 `generate_story()` 现在用用户输入的 theme/关键词刷新并读取长期 Markdown 与普通 chat 短期 Markdown，把 `long_term_memory_md`、`short_term_memory_md`、候选 `source_memory_ids` 和筛选后的 `retrieved_memories` 放入 story generation payload。候选来源只允许 confirmed/corrected 且未删除的 `MemoryCard`；provider 返回不存在、未审核、已删除或越权来源时会丢弃，并回退到本地关键词排序后的来源。
- MiniMax/story 输出处理已收紧：story system prompt 要求中文第一人称、只使用提供的长期/短期记忆与来源记忆、返回 strict JSON 且不得输出思考过程；JSON 解析前会移除完整和未闭合 `<think>`，支持从“思考文本 + JSON”中提取首个 JSON object；plain-text fallback 也先清洗 `<think>`。故事正文入库、列表返回、导出文本和 TTS 输入前统一清洗模型思考块，清洗后为空或明显不是中文时回退为基于来源记忆的 deterministic 中文故事，避免英文 prompt 或 `<think>` 泄漏到页面。
- 语义搜索保持既有 `/api/personas/{id}/audit/search` wire shape，搜索服务会读取长期/短期 Markdown 并结合 `MemoryCard` 的 title/content/source_quote/user_correction/source_location 做排序；长期/短期上下文只辅助命中可追溯 `MemoryCard`，不会把短期对话片段作为独立结果返回。审计事件继续写入 `memory.searched`，metadata 记录 query、top_k、result_memory_ids。
- 前端 memories 页文案已调整为“输入关键词，在长期/短期记忆中查找可追溯来源记忆。”；故事卡片只展示清洗后的故事正文、来源标题和来源位置；语义搜索结果补充来源位置。`storySourceSummary()` 现在按 `标题（来源位置）` 汇总来源。
- 已同步 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md`、`docs/平台说明.md` 和本进度账本，统一口径为 memories 页只做回忆讲述和语义搜索，story/search 读取长期/短期记忆上下文，语义搜索结果仍是可追溯记忆卡片，不新增 stories 页面。
- TDD RED：`python -m pytest backend/tests/test_stories.py backend/tests/test_audit.py backend/tests/test_minimax_provider.py -q` 先红，命中 `<think>` 泄漏、搜索来源位置和 MiniMax parser 约束；`npm.cmd --prefix frontend run test -- stories.test.mjs memories.test.mjs` 先红，命中 stories source location 汇总和 memories 长期/短期搜索文案约束。
- 聚焦 GREEN：`python -m pytest backend/tests/test_stories.py backend/tests/test_audit.py backend/tests/test_minimax_provider.py -q` 32 passed；`npm.cmd --prefix frontend run test -- stories.test.mjs memories.test.mjs` 因当前脚本执行全量测试，结果 116 passed。
- 收尾验证：`python -m json.tool docs/feature-list.json` 退出码 0；`python -m pytest backend/tests/test_stories.py backend/tests/test_audit.py backend/tests/test_minimax_provider.py backend/tests/test_memory_markdown.py -q` 37 passed；`npm.cmd --prefix frontend run test` 117 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 服务验证：`docker compose up --build -d backend frontend` 退出码 0，backend healthy、frontend started；`http://localhost:8000/health` 返回 `{"status":"ok"}`，`http://localhost:3000` HTTP 200。应用内浏览器 smoke 受 Browser URL policy 限制，导航/刷新 `http://localhost:3000/personas/27e4e946-6b92-42a2-982c-fde85b36c284/memories` 被拒绝，未绕过该策略改用外部浏览器；本轮浏览器层交互 smoke 未完成。
- 本次未运行 `docs/init.sh`；按仓库规则只有用户明确要求完整基线验证时才运行。真实 story API smoke 可能触发 MiniMax/TTS provider 调用且耗时较长，本轮未继续重复调用真实 provider，相关清洗、过滤和 fallback 由后端单元测试覆盖。

## Latest Session Update - 2026-07-05 uploads 结构化记忆卡片逐条操作修复

- 根因定位：`frontend/app/personas/[id]/uploads/page.tsx` 的 `MemoryDimensionCard` 以分类为操作容器，旧实现使用 `first = memories[0]` 管理编辑态，并在分类底部提供共享的编辑/删除/确认按钮；这会导致用户无法判断操作作用于哪一条结构化记忆，且编辑默认只针对第一条。
- 修复：分类卡片继续只负责展示维度标题和分组；真实 `MemoryCard` 渲染为每条独立 article，每条内联自己的星标、编辑、删除、确认按钮。编辑态改为 `editingMemoryId`，保存时只更新当前 `memory.id`；删除和确认也只传当前 `memory.id`。同时移除 `memories.slice(0, 3)`，确保该分类下每条结构化信息都可见且可操作。自定义维度仍保持本地维度级操作，因为它不是后端 MemoryCard。
- TDD：新增 `frontend/tests/materials.test.mjs` 用例 `uploads memory audit actions are attached to each parsed memory card`，先红在缺少逐条 action 绑定；实现后聚焦验证 `node --import tsx --test tests/materials.test.mjs` 7 passed。
- 收尾验证：`npm.cmd --prefix frontend run test` 118 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`docker compose build frontend` 和 `docker compose up -d --no-deps --force-recreate frontend` 退出码 0。后端健康检查一度超时导致页面停在加载态，已仅重启 backend 容器，`/health` 返回 `{"status":"ok"}`。
- 浏览器 smoke：刷新 `/personas/18b88e96-5633-4d75-b77a-0ad1988a846a/uploads` 后，基础信息区域 `articleCount=3`，每条 article 均包含自己的「标记/取消重要、编辑、删除、确认」按钮；`scrollWidth=clientWidth=684`，无横向溢出。
- 本次未运行 `docs/init.sh`；按仓库规则只有用户明确要求完整基线验证时才运行。

## Latest Session Update - 2026-07-05 声音页生成模拟音色 Failed to fetch 修复

- 根因定位：浏览器点击 `生成模拟音色` 后，后端日志显示真实 MiniMax voice clone 上传阶段抛出 `MiniMax request failed: invalid params, invalid file ext for voice clone`，异常未被 voice service 转换为结构化失败响应，导致浏览器侧看到 `Failed to fetch`。同时前端 `handleCloneVoice()` 从 `voice_models` 中取第一个 `sample_ready`，而后端列表按创建时间正序返回，容易克隆旧样本而不是刚录音转 WAV 后创建的新样本。
- 修复：`backend/app/services/voice.py` 在 voice clone provider 抛异常时复用现有失败分支，写入 failed job、把源 voice model 标记为 `clone_failed`，并回退到默认 TTS，不再让异常穿透到浏览器。`frontend/src/lib/voice.ts` 新增 `latestCloneSourceModel()`，优先使用刚创建的样本 ID，否则选最新 `sample_ready/clone_failed` 样本；声音页创建样本后记录 `lastCreatedVoiceSampleId`，生成模拟音色时用该样本发起克隆。
- TDD RED/GREEN：新增 `backend/tests/test_voice.py::test_clone_voice_provider_exception_falls_back_to_default_tts`，先红在 provider 异常穿透；新增 `frontend/tests/voice.test.mjs` 的 latest clone source helper 测试，先红在 helper 未导出。实现后聚焦验证通过：`python -m pytest backend/tests/test_voice.py::test_clone_voice_provider_exception_falls_back_to_default_tts -q` 1 passed；`node --import tsx --test tests/voice.test.mjs` 14 passed。
- 收尾验证：`python -m pytest backend/tests/test_voice.py -q` 14 passed；`python -m pytest backend/tests -q` 234 passed；`npm.cmd --prefix frontend run test` 117 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`python -m json.tool docs/feature-list.json` 退出码 0。
- 服务与浏览器 smoke：`docker compose build backend frontend` 退出码 0；`docker compose up -d --no-deps --force-recreate backend frontend` 后 backend healthy、frontend started，`/health` 返回 `{"status":"ok"}`，当前 voice 页 HTTP 200。刷新应用内浏览器 `/personas/27e4e946-6b92-42a2-982c-fde85b36c284/voice` 后 DOM 确认 `Failed to fetch` 不再残留，`生成模拟音色` 按钮可见可点，两步说明仍存在。本次未接受麦克风权限，也未主动触发真实 MiniMax 克隆请求。
- 本次未运行 `docs/init.sh`；按仓库规则只有用户明确要求完整基线验证时才运行。

## Latest Session Update - 2026-07-05 视频手势互动与 GLB 动作反馈

- 根据用户确认计划，本次只做 `/personas/{id}/chat` 前端视频手势互动和 GLB 动作反馈，不新增后端 API、路由、数据库字段或摄像头视频上传/持久化。视频手势模式现在提供开始/停止摄像头、识别状态、最近识别手势、本地隐私提示和进入语音对话按钮；识别结果只存在当前组件状态。
- 新增 `frontend/src/lib/gesture.ts`：接入 `@mediapipe/tasks-vision` GestureRecognizer，归一张开手掌/握拳，使用手部横向轨迹判断挥手，使用画面停留触发 presence，并提供冷却去抖、手势到 `motionIntent` 的映射、用户可读状态文案和 GLB animation clip 名称匹配。MediaPipe wasm URL 固定为已安装版本 `0.10.35`。
- `AvatarStage`/`AvatarPreview` 新增 `motionIntent`。`AvatarPreview` 使用 `THREE.AnimationMixer` 优先播放 GLB 自带 idle/wave/nod/listen/speak 等匹配动画；缺少对应 clip 时使用整体转身、轻摆、点头、靠近等基础动作 fallback，并显示“当前模型不含对应动画，已使用基础动作反馈”提示。
- 聊天页会把视频手势识别结果传给右侧数字人；播放语音消息时仍优先使用 `speaking`，发送等待时使用 `thinking`。本轮不做复杂手语、全身动作捕捉、多人识别、手势触发模型回复、真实 audio envelope 或 viseme 口型同步。
- 已同步范围文档：`docs/README.md`、`docs/feature-list.json` 新增 `feat-050`、`docs/prd-checklist.md`、`docs/平台说明.md` 和本进度账本。修改文件范围：`frontend/src/lib/gesture.ts`、`frontend/src/components/AvatarPreview.tsx`、`frontend/src/components/AvatarStage.tsx`、`frontend/app/personas/[id]/chat/page.tsx`、`frontend/tests/gesture.test.mjs`、`frontend/tests/chat.test.mjs`、`frontend/tests/avatar.test.mjs`、`frontend/package.json`、`frontend/package-lock.json`、上述 docs 文件。
- TDD RED：先运行 `node --import tsx --test tests/gesture.test.mjs tests/chat.test.mjs tests/avatar.test.mjs`，按预期失败，命中缺少 `frontend/src/lib/gesture.js`、聊天页缺少摄像头/gesture integration、`AvatarPreview` 缺少 `AnimationMixer` 和 fallback 约束。
- 聚焦 GREEN：`node --import tsx --test tests/gesture.test.mjs tests/chat.test.mjs tests/avatar.test.mjs` 31 passed；`python -m json.tool docs/feature-list.json` 退出码 0；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 完整前端测试现状：`npm.cmd --prefix frontend run test -- chat.test.mjs avatar.test.mjs` 和 `npm.cmd --prefix frontend run test` 都会运行当前 `tests/*.test.mjs` 全量套件，结果均为 114 passed / 2 failed。失败项是既有、非本轮手势/GLB 文件的源码断言：`tests/memories.test.mjs` 的 “memories page keeps only story telling and semantic search” 期望 memories 页源码包含“长期/短期记忆”；`tests/stories.test.mjs` 的 “story source summary keeps source titles scannable” 期望 `storySourceSummary()` 输出包含 source location。未为本轮视频手势范围顺手修改这些 unrelated 页面/工具函数。
- 服务与浏览器 smoke：`docker compose build frontend` 退出码 0；`docker compose up -d --no-deps --force-recreate frontend` 退出码 0，frontend started。刷新 `http://localhost:3000/personas/27e4e946-6b92-42a2-982c-fde85b36c284/chat` 后切到“视频手势互动”，桌面视口显示“开始摄像头”“本地识别，不上传摄像头画面”“进入语音对话”和 GLB fallback 提示，旧“这里会用于和...”占位文案不存在，`scrollWidth=clientWidth=684`、横向溢出 0；390x844 移动视口同样显示视频手势面板，`scrollWidth=clientWidth=375`、横向溢出 0。未主动接受摄像头权限弹窗，也未上传或保存任何摄像头视频。
- 本次未运行 `docs/init.sh`；按仓库规则只有用户明确要求完整基线验证时才运行。

## Latest Session Update - 2026-07-05 资料导入超时、进度条与 MiniMax JSON 纠错

- 根据用户确认，本次只修复资料导入稳定性和上传资料页反馈，不改变上传时机、后端 API、路由、数据库结构或审核流程。DashScope 默认请求超时从 60 秒调整为 180 秒，并纳入 provider settings allowlist/report；本地 `.env/runtime.env` 如显式写入 `DASHSCOPE_REQUEST_TIMEOUT_SECONDS` 仍会覆盖默认值。
- MiniMax `memory_document_generation` prompt 已收口为结构化 JSON 文档输出：模型返回 `structured_memory_document_json`、`profile_summary`、trust 和 suggestions，后端再确定性渲染 `structured_memory_md`。文档链路使用 JSON object 响应约束，解析前清理 `<think>`、Markdown fence 和前后说明，并从首个 JSON object 做 schema 校验。
- 资料解析失败语义调整：前处理或 `memory_extraction` 失败仍标记 material/job failed；如果 `ParsedChunk` 和 `MemoryCard` 已生成，但全人物结构化文档 provider JSON 仍不可用，则 material/job 记为 succeeded，后端用已生成的记忆卡片结构生成 `structured_memory_document_json`、`structured_memory_md`、`profile_summary` 和 trust，并只在 job metadata 记录 provider 诊断，不在 uploads 资料卡片展示。
- 上传资料页新增阶段式进度条：文件上传和手动资料提交按钮下方显示 `role="progressbar"` 与 `aria-live="polite"` 状态，按“上传/保存资料、等待解析、生成结构化记忆、刷新审核结果、完成”展示客户端阶段；不声明字节级真实进度，也不改异步轮询。材料卡片现在只展示真正 failed job 的具体失败原因，不展示结构化文档 provider 技术诊断。
- 已同步 `docs/README.md`、`docs/prd-checklist.md`、`docs/平台说明.md` 和本进度账本；未更新 `docs/feature-list.json`，因为本次不新增功能切片或改变功能范围；未运行 `docs/init.sh`。
- TDD/验证：先扩展后端 config/provider settings/MiniMax/parsing 测试和前端 uploads 测试并确认 RED；实现后聚焦后端 `python -m pytest backend/tests/test_config.py backend/tests/test_provider_settings.py backend/tests/test_minimax_provider.py backend/tests/test_parsing.py -q` 31 passed，聚焦前端 `node --import tsx --test tests/materials.test.mjs` 6 passed。
- 收尾验证：`python -m pytest backend/tests -q` 227 passed；`npm.cmd --prefix frontend run test` 116 pass / 0 fail；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。

## Latest Session Update - 2026-07-05 声音页录音 WAV 兼容与两步说明

- 根据用户确认，本次保留声音页两个按钮：`上传并创建音色样本` 只负责把上传文件或录音创建为 `sample_ready` 可克隆样本；`生成模拟音色` 继续负责调用现有 `cloneVoice()` / MiniMax voice clone 链路，成功后得到可用于 TTS 的 voice_id。页面在按钮上方补充两步说明，避免把样本创建误解为已经生成可用模拟音色。
- 浏览器录音仍使用 `MediaRecorder` 采集并保留原始 Blob 的本地 audio 预览；停止录音后新增 Web Audio API 解码与 WAV 编码，把提交文件改为 `voice-sample-recording-{timestamp}.wav`、MIME `audio/wav`，再复用现有 `uploadMaterials()` 和 `createVoiceSample()`。转码失败时提示“录音转 WAV 失败，请重新录制或上传 mp3/m4a/wav 音频。”本轮不新增后端 API、数据库字段、后端转码、降噪、音质检测或最长录音限制。
- 后端新增用例覆盖 `voice-sample-recording.webm` 在 MIME 为 `audio/webm` 时仍可创建音频样本；MIME 缺失/`application/octet-stream` 的 `.webm` 仍按 video 资料处理，创建音色样本时返回 `Voice samples require an audio source material`。这保持现有材料类型推断，不把所有 `.webm` 扩大为音频。
- TDD RED：先扩展 `frontend/tests/voice.test.mjs` 与 `backend/tests/test_voice.py`；`node --import tsx --test tests/voice.test.mjs` 按预期 2 failed，命中缺少 WAV 转码函数与两步说明；`python -m pytest backend/tests/test_voice.py -q` 13 passed，说明后端 MIME 行为已满足新增覆盖。
- GREEN 聚焦验证：`node --import tsx --test tests/voice.test.mjs` 13 passed；`python -m pytest backend/tests/test_voice.py -q` 13 passed。
- 收尾验证：`python -m json.tool docs/feature-list.json` 退出码 0；`python -m pytest backend/tests/test_voice.py -q` 13 passed；`node --import tsx --test tests/voice.test.mjs` 13 passed；`npm.cmd --prefix frontend run test` 116 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 收尾过程中 `npm.cmd --prefix frontend run lint` 暴露 chat 页摄像头清理 effect 的 `react-hooks/exhaustive-deps` 警告；已将停止摄像头清理逻辑改为稳定 `useCallback` 并由卸载 effect 显式依赖，未改变视频手势交互语义。
- 浏览器 smoke：当前 `localhost:3000` 由 Docker frontend 容器提供；已执行 `docker compose build frontend` 和 `docker compose up -d --no-deps --force-recreate frontend` 仅重建/重启 frontend。刷新 `/personas/27e4e946-6b92-42a2-982c-fde85b36c284/voice` 后，DOM 确认 `上传并创建音色样本`、`生成模拟音色`、`录制 TA 的人声音频`、`开始录音`、两步说明文案均存在，`#voice-sample-upload` 存在且 `accept=audio/*`，旧 `#audio-material` 不存在。本轮未接受麦克风权限，未上传真实音频、未触发真实 MiniMax 克隆。
- 本次未运行 `docs/init.sh`；按仓库规则只有用户明确要求完整基线验证时才运行。

## Latest Session Update - 2026-07-05 声音页浏览器录音创建音色样本

- 根据浏览器评论，本次在 `/personas/{id}/voice` 第 2 步保留本地音频文件上传，同时新增“录制 TA 的人声音频”入口。页面提示必须提供 TA 的纯净无噪声清晰人声；用户点击“开始录音”后调取浏览器麦克风权限，录音中可停止，停止后显示本地 audio 预览和“重新录制”，用户确认后才上传并创建音色样本。
- 前端复用现有链路，不新增后端 API、数据库字段或迁移：录音 Blob 转为 `voice-sample-recording-{timestamp}.webm` File 后调用 `uploadMaterials()` 生成 audio SourceMaterial，再调用 `createVoiceSample()` 创建 `sample_ready` VoiceModel。选择本地文件会清除录音，完成新录音会清除已选文件，一次只提交一个样本来源；停止/重录/卸载时关闭 `MediaStreamTrack` 并 `URL.revokeObjectURL()`。
- TDD RED：先新增 `frontend/tests/voice.test.mjs` 源码约束后运行 `node --import tsx --test tests/voice.test.mjs`，按预期 1 failed，命中页面缺少 `navigator.mediaDevices.getUserMedia`。
- GREEN/验证：`node --import tsx --test tests/voice.test.mjs` 12 passed；`python -m json.tool docs/feature-list.json` 退出码 0；`python -m pytest backend/tests/test_voice.py -q` 11 passed；`python -m pytest backend/tests/test_minimax_provider.py -q` 10 passed；`npm.cmd --prefix frontend run test` 106 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 服务与浏览器 smoke：`docker compose build frontend; docker compose up -d --no-deps --force-recreate frontend` 退出码 0，刷新当前 voice 页后 `#voice-sample-upload` 存在且 `type=file`、`accept=audio/*`；默认 TTS 下拉存在；“录制 TA 的人声音频”和“开始录音”可见；旧 `#audio-material`、`选择音频资料`、`暂无可用音频资料` 均不存在；横向溢出 0。本次未接受浏览器麦克风权限，未上传真实音频、未触发真实 TTS 或真实音色克隆。
- 已同步 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md`、`docs/平台说明.md` 和本进度账本；本次未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 聊天页语音对话互动接入

- 根据浏览器评论，本次只在 `/personas/{id}/chat` 前端接入既有语音链路，不改后端 API、路由、schema 或数据库。聊天页现在加载 `getVoiceConfig(personaId)`；语音模式会读取当前 selected TTS/模拟音色，已配置时显示“当前语音来源”和“语音输入”按钮，未配置时显示“去声音设置配置 TTS”入口并跳转 `ROUTES.personaVoice(personaId)`。
- `VoiceSurface` 从占位文案升级为浏览器录音交互：点击开始录音、再次点击结束，使用 `navigator.mediaDevices.getUserMedia({ audio: true })` 和 `MediaRecorder` 生成 `audio/webm` 文件，通过 `uploadMaterials()` 上传为音频资料，再调用既有 `sendVoiceMessage(conversation.id, { source_material_id })`。后端完成 ASR -> 文本对话 -> TTS 后，前端刷新消息列表并用返回的 `audio_url` 自动尝试播放，同时保留可手动播放的 audio 控件。
- 语音录制/上传/识别/生成期间复用页面 `sending` 状态，禁用文字发送与重复录音；麦克风不可用、权限拒绝、上传失败或 voice-message 失败时复用当前错误提示区。当前实现不接入 Web Speech API，不做流式 ASR，不处理视频手势 GLB/摄像头功能。
- 新增 `frontend/src/lib/voice.ts` helper `hasChatReadyVoiceConfig()`，只把 selected model 为 `default_tts` 或 `cloned_ready` 视为可进入语音对话；`sample_ready/no_voice/cloning/clone_failed` 不作为聊天页可用声音。
- TDD RED：先扩展 `frontend/tests/voice.test.mjs` 和 `frontend/tests/chat.test.mjs` 后运行聚焦命令，按预期失败：`hasChatReadyVoiceConfig` 尚未导出，聊天页缺少 `getVoiceConfig`、`uploadMaterials`、`sendVoiceMessage`、`MediaRecorder` 和 TTS 配置入口。
- GREEN/验证：`npm.cmd --prefix frontend run test -- voice.test.mjs` 退出码 0，当前脚本实际运行 106 passed；`npm.cmd --prefix frontend run test -- chat.test.mjs` 退出码 0，当前脚本实际运行 106 passed；`npm.cmd --prefix frontend run test` 退出码 0，106 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 服务与浏览器 smoke：`docker compose build frontend; docker compose up -d --no-deps --force-recreate frontend` 退出码 0，frontend started。刷新 `http://localhost:3000/personas/27e4e946-6b92-42a2-982c-fde85b36c284/chat` 后切到“语音对话”，当前已配置 TTS 的 demo 人物显示“当前语音来源”和“语音输入”按钮，旧占位文案不存在；桌面横向溢出 0。移动视口 390x844 下同样显示配置态语音面板，`scrollWidth=clientWidth=375`，横向溢出 0。未擅自接受麦克风权限弹窗，也未为制造 no-TTS 状态改动用户现有 demo 数据；无 TTS 引导路径由 helper/source 测试覆盖。
- 本次修改文件：`frontend/app/personas/[id]/chat/page.tsx`、`frontend/src/lib/voice.ts`、`frontend/tests/chat.test.mjs`、`frontend/tests/voice.test.mjs`、`docs/progress.md`。本次未运行 `docs/init.sh`，未更新 `feature-list.json` 或 `prd-checklist.md`。

## Latest Session Update - 2026-07-05 遗憾对话室与心愿引导上下文隔离

- 根据用户计划，本次为 conversation 增加/收口 `kind` 与 `context_kind` 分流：普通聊天使用 `kind=chat/context_kind=general`，遗憾对话室使用 `kind=regrets`，心愿延续引导使用 `kind=wishes/context_kind=wishes`。旧普通 conversation 不自动拆分，后续 guided 页只加载或创建自己的专属会话。
- 后端 conversation list/create 支持按 `kind` 和 `context_kind` 过滤；`send_text_message` 会按 conversation kind 组装上下文。遗憾对话室使用围绕“有没有什么以前没说的话，今天想慢慢告诉我？”的专属 guided system prompt，引导用户表达道歉、感谢、想念、告别或心结；该路径保留人物基础设定、profile summary 和 confirmed/corrected 长期记忆，但短期 Markdown 只读取 `short_term_memory_regrets.md`，不会读取普通 chat 的“浏览器烟测消息”等短期内容。
- 心愿延续引导使用围绕“你现在有什么想完成的心愿，或者想替我继续做的一件事吗？”的 wishes system prompt，只围绕心愿、替 TA 继续做的一件事和下一步行动发散；该上下文只使用当前 wishes conversation 历史、人物基础信息和 profile 语气资料，不读取普通 chat、遗憾对话等其他 conversation 的短期 Markdown，也不走默认记忆召回/引用。本次仍不实现 P1 心愿持久化、提醒、CRUD 或长期行动系统。
- 前端 `GuidedExperiencePage` 通过 `guidedExperienceConversationKind()` / `guidedExperienceContextKind()` 加载或创建专属 guided conversation；普通 `/chat` 页只加载或创建 `kind=chat` 会话。`sendMessage` 继续复用既有 messages endpoint，不新增消息 mode。
- 迁移链修正为 `0008_conversation_kind.py` 只添加 `kind`，`0009_conversation_context_kind.py` 添加 `context_kind`，避免真实 Alembic 升级重复添加同一列。文档已同步 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md`、`docs/平台说明.md` 和 PRD。
- TDD 记录：后端先用 `python -m pytest backend/tests/test_chat.py backend/tests/test_minimax_provider.py -q` 跑红，命中 `context_kind`、metadata 和 MiniMax wishes prompt 缺口；前端先用 `node --import tsx --test tests/guided-experiences.test.mjs tests/chat.test.mjs` 跑红，命中 helper/API 和 guided page conversation 选择缺口。实现后聚焦验证已通过：`python -m pytest backend/tests/test_chat.py backend/tests/test_memory_markdown.py backend/tests/test_minimax_provider.py -q` 37 passed；`node --import tsx --test tests/guided-experiences.test.mjs tests/chat.test.mjs` 14 passed。
- 收尾验证：`python -m json.tool docs/feature-list.json > $null` 退出码 0；`python -m pytest backend/tests/test_migrations.py -q` 2 passed；`python -m pytest backend/tests/test_chat.py backend/tests/test_memory_markdown.py backend/tests/test_minimax_provider.py -q` 37 passed；`npm.cmd --prefix frontend run test` 103 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。`docker compose up --build -d backend frontend` 镜像构建完成且 backend healthy 后，frontend recreate 命中 Docker container handle `No such container`；随后 `docker compose up -d --no-deps --force-recreate frontend` 恢复，`docker compose ps` 显示 backend healthy、frontend started，`/health` 返回 `{"status":"ok"}`，regrets 页面 HTTP 200。
- 浏览器 smoke：先在普通 `/chat` 发送唯一文本 `普通聊天隔离烟测-*`，再打开 `/regrets`，页面不显示该唯一文本，也不显示旧普通聊天“浏览器烟测消息”；发送 `你好-*` 后，回复围绕“以前没来得及说的话 / 亏欠 / 感谢 / 想念”继续引导，没有出现“吃饭了没有 / 吃过饭没有”这类普通聊天问候。
- 本次仍不运行 `docs/init.sh`；按仓库规则只有用户明确要求完整基线验证时才运行。

## Latest Session Update - 2026-07-05 声音页直接上传纯净人声音频

- 根据浏览器评论，本次把 `/personas/{id}/voice` 第 2 步从“选择音频资料”下拉改为本页直接上传音频；页面提示“必须上传纯净无噪声的人声音频：只包含 TA 的清晰人声，避免背景音乐、多人同时说话和明显环境噪声。”
- 前端不再加载 `listMaterials()` 或显示 `#audio-material`、`选择音频资料`、`暂无可用音频资料`；用户选择 `audio/*` 文件后点击“上传并创建音色样本”，页面复用现有 `uploadMaterials()` 上传为 SourceMaterial，再调用既有 `createVoiceSample()` 创建 `sample_ready` VoiceModel。后端 voice API 和数据库结构未改。
- TDD RED：先新增 `frontend/tests/voice.test.mjs` 源码约束后运行 `node --import tsx --test tests/voice.test.mjs`，按预期 1 failed，命中页面仍缺少 `uploadMaterials` 且保留旧音频资料下拉。
- GREEN/验证：`node --import tsx --test tests/voice.test.mjs` 10 passed；`python -m json.tool docs/feature-list.json > $null` 退出码 0；`python -m pytest backend/tests/test_voice.py -q` 11 passed；`npm.cmd --prefix frontend run test` 103 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 首次因 stale `.next` 缺少 `_app.js.nft.json` 失败，确认目标在 `frontend/.next` 后删除生成目录并重跑，退出码 0。
- 服务与浏览器 smoke：`docker compose build frontend` 退出码 0，`docker compose up -d --no-deps --force-recreate frontend` 退出码 0，backend healthy、frontend started；刷新当前 voice 页后 `#voice-sample-upload` 存在且 `type=file`、`accept=audio/*`、可见，纯净无噪声人声提示和“上传并创建音色样本”可见，旧 `#audio-material`、`选择音频资料`、`暂无可用音频资料` 均不存在，横向溢出 0。本次未上传真实音频、未触发真实 TTS 或真实音色克隆。
- 已同步 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md`、`docs/平台说明.md` 和本进度账本；本次未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 数字人模型主体占比放大

- 根据浏览器反馈，本次调整共享 `AvatarPreview` 的 GLB 取景：把相机高度从 `y=1.35` 降到 `y=0.65`，并把标准化目标尺寸从 `2.45` 提到 `3.15`，让数字人尽量占据展示框主体。该组件由 avatar/chat/regrets/wishes 共享，因此四个页面同样生效。
- `frontend/tests/avatar.test.mjs` 增加源码约束，覆盖共享预览的相机位置和 `targetModelSize=3.15`，避免后续回退到偏小展示。
- 验证：`npm.cmd --prefix frontend run test -- avatar.test.mjs` 退出码 0（当前脚本实际运行全量前端测试，103 passed）；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。`docker compose up --build -d frontend` 的镜像构建成功，但因 compose 依赖重建 backend 后 backend health 超时；查看日志无栈错误，重启 backend 后 health 恢复，再用 `docker compose up -d --no-deps --force-recreate frontend` 启动前端。
- 浏览器 smoke：avatar/chat/regrets/wishes 均有非空 GLB canvas、无“模型加载失败”、横向溢出 0；avatar 页截图确认数字人已占据展示框主体。390x844 移动视口 avatar 页 canvas 293x448、模型加载成功、横向溢出 0，已恢复默认视口。
- 本次未运行 `docs/init.sh`；按仓库规则只有用户明确要求完整基线验证时才运行。

## Latest Session Update - 2026-07-05 数字人展示卡片装饰清理

- 根据浏览器反馈，本次删除 `AvatarStage` 内 GLB 展示区右上方无功能圆形装饰层；该元素只是遗留视觉氛围，不参与模型加载、交互、状态提示或布局，容易被误认为取景框/控制区。
- `frontend/src/components/AvatarStage.tsx` 移除 `right-[7%] top-[8%] h-56 w-56 rounded-full` 绝对定位装饰；`frontend/tests/avatar.test.mjs` 增加源码约束，防止该装饰回到共享 GLB 模型卡片。
- 验证：`npm.cmd --prefix frontend run test -- avatar.test.mjs` 退出码 0（当前脚本实际运行全量前端测试，102 passed）；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`docker compose up --build -d frontend` 退出码 0，backend healthy、frontend started。
- 浏览器 smoke：刷新 `http://localhost:3000/personas/27e4e946-6b92-42a2-982c-fde85b36c284/avatar` 后，装饰圆环 DOM 计数为 0，模型加载成功，无“模型加载失败”，GLB canvas 非空，横向溢出 0。
- 本次未运行 `docs/init.sh`；按仓库规则只有用户明确要求完整基线验证时才运行。

## Latest Session Update - 2026-07-05 GLB meshopt 加载与存储卷修复

- 根据浏览器反馈，本次定位 `/personas/{id}/avatar` 显示“模型加载失败”：后端 `GET /api/avatar-models/{id}/file` 返回 200，GLB header 为 `glTF` v2 且长度匹配；解析 GLB JSON 后发现该模型 `extensionsRequired` 包含 `EXT_meshopt_compression`，当前 `AvatarPreview` 只配置了 `GLTFLoader`，未设置 MeshoptDecoder，导致浏览器端解析失败。
- `frontend/src/components/AvatarPreview.tsx` 已引入 `three/examples/jsm/libs/meshopt_decoder.module.js` 并调用 `loader.setMeshoptDecoder(MeshoptDecoder)`；加载失败回调会输出 console warning，避免后续只剩前端泛化失败提示。`frontend/tests/avatar.test.mjs` 新增源码约束，要求共享 GLB loader 保留 `MeshoptDecoder` 和 `setMeshoptDecoder`。
- 同步修复本地 Compose 存储缺口：`docker-compose.yml` 为 backend 增加 `avatar-model-storage:/app/storage/avatar_models`，避免开发容器重建后 Postgres 中 selected avatar model 记录仍在但本地 GLB 文件丢失。文档已同步 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md` 和 `docs/平台说明.md`。
- 验证：`npm.cmd --prefix frontend run test -- avatar.test.mjs` 退出码 0（当前脚本实际运行全量前端测试，98 passed）；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`python -m json.tool docs/feature-list.json > $null` 退出码 0；`docker compose config` 退出码 0；`docker compose up --build -d backend frontend` 退出码 0，backend healthy、frontend started。
- 浏览器 smoke：重新上传同一个 meshopt GLB 后，avatar 页显示“模型加载成功”，无“模型加载失败”，canvas 非空，横向溢出 0；chat/regrets/wishes 三个共享 `AvatarStage` 页面均有非空 GLB canvas、无失败提示、横向溢出 0；`docker compose restart backend` 后模型文件接口仍返回 200、`model/gltf-binary`、`glTF` header 和完整长度，确认卷内文件未丢；390x844 移动视口 avatar 页 canvas 293x448、模型加载成功、横向溢出 0，已恢复默认视口。
- 本次未运行 `docs/init.sh`；按仓库规则只有用户明确要求完整基线验证时才运行。

## Latest Session Update - 2026-07-05 Uploads 自动档案摘要与结构化信息星标

- 根据用户计划，本次删除 uploads 页手动“档案摘要”编辑卡片；`memory_document_generation` 输出契约新增 `profile_summary`，每次资料解析后自动覆盖 `PersonaProfile.profile_summary`，并继续写入 `structured_memory_md`、trust 和 suggestions。`build_profile_from_memories`、记忆确认/编辑/删除和 Persona Engine profile regenerate 不再覆盖自动摘要或唯一 trust。
- 新增 `MemoryCard.is_important`、Alembic 迁移、schema/API 字段和 uploads 星标按钮；用户可在每条真实结构化记忆上点星标/取消星标，重要记忆在结构化记忆文档 payload、长期记忆 Markdown、Persona Engine payload、story retrieval 和 chat memory selection 中携带并优先排序。
- uploads 文件资料区改为复用创建页“上传珍贵回忆”的四宫格 tile 样式；文件资料和手动资料前端不再暴露“备注”或“重要程度”，前端 helper 只在兼容旧调用时可选发送 `importance`，资料列表也不再展示资料级重要性。
- 人物详情页顶部简介继续读取 `profile.profile_summary`，无摘要时显示“档案摘要将在新的资料上传解析后自动生成。”；`/personas/{id}/profile` 仍只是兼容重定向页，后端 profile API 保留。
- 已更新 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md`、`docs/平台说明.md`、PRD 和本进度账本；本次不运行 `docs/init.sh`，按仓库规则只有用户明确要求完整基线验证时才运行。
- TDD 记录：后端 focused tests 先红后绿，覆盖 provider 输出 `profile_summary`、上传解析写入自动摘要、memory PATCH 星标、摘要不被审核动作覆盖、重要记忆优先进入 Markdown/chat/story；前端源码测试覆盖 uploads 移除摘要卡片/备注/重要程度、四宫格上传、星标切换和 materials helper 可选 importance。
- 收尾验证：`python -m json.tool docs/feature-list.json > $null` 退出码 0；`python -m pytest backend/tests/test_provider_gateway.py backend/tests/test_parsing.py backend/tests/test_materials.py backend/tests/test_profile.py backend/tests/test_memories.py backend/tests/test_memory_markdown.py backend/tests/test_chat.py backend/tests/test_stories.py -q` 70 passed；`python -m pytest backend/tests -q` 211 passed；`npm.cmd --prefix frontend run test` 98 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。浏览器 smoke 尝试使用本机 Chrome 访问 `/personas/{id}/uploads`、人物详情和 `/profile` 深链；`/profile` 深链已重定向到 uploads 且无摘要编辑按钮，但本地后端 `POST /api/auth/demo` 在 12 秒后关闭连接、页面停在“正在加载资料解析结果...”，因此未完成登录后内容 smoke。`/health` 仍为 200，本次未重启或改动用户现有服务，也未运行 `docs/init.sh`。
- 后续问答修正：核对“记忆可信度是否所有页面统一字段”时发现 `GET /profile` 正常路径与 `persona.trust_score` 同步，但 report 组装曾在历史不一致时优先读最新 AI job output。已新增回归测试并改为 profile GET 始终以 `Persona.trust_score` 作为展示分数和等级来源，AI job output 只保留 rationale/suggestions 等说明性证据。验证：新增测试先红后绿；`python -m pytest backend/tests/test_profile.py backend/tests/test_parsing.py backend/tests/test_memories.py -q` 27 passed；`npm.cmd --prefix frontend run test -- memory-space.test.mjs persona.test.mjs profile.test.mjs` 当前脚本全量运行 102 passed；`python -m pytest backend/tests -q` 220 passed。

## Latest Session Update - 2026-07-05 默认 TTS 中文名称与真人声线过滤

- 根据浏览器评论，本次只调整 `/personas/{id}/voice` 默认 TTS 下拉：`voice_id` 前的说明改为中文名称，并按“中文名称：voice_id”展示，例如 `亲切长者：Chinese (Mandarin)_Kind-hearted_Elder`。
- 默认 TTS 静态列表删除非真人相关声线 `Robot_Armor` 和 `Chinese (Mandarin)_Cute_Spirit`；当前保留 32 个 MiniMax 中文普通话真人相关 system voices。后端 `default_tts_voices` 与前端 fallback 常量保持一致。
- TDD RED：`python -m pytest backend/tests/test_voice.py -q` 先 1 failed，命中后端仍返回英文 `Reliable Executive`；`node --import tsx --test tests/voice.test.mjs` 先 3 failed，命中前端仍返回英文标签、`Gentle Senior` 和 `名称 · voice_id`。
- GREEN：同两条聚焦命令已通过，分别为 11 passed 和 9 passed。
- 收尾验证：`python -m json.tool docs/feature-list.json` 退出码 0；`python -m pytest backend/tests/test_voice.py backend/tests/test_minimax_provider.py -q` 21 passed；`npm.cmd --prefix frontend run test` 102 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`git diff --check` 退出码 0，仅输出当前工作区既有 LF-to-CRLF warning。
- 浏览器 smoke：刷新 `http://localhost:3000/personas/27e4e946-6b92-42a2-982c-fde85b36c284/voice` 后，`#default-tts-voice` 为 32 个选项；首项显示 `可靠高管：Chinese (Mandarin)_Reliable_Executive`，包含 `亲切长者：Chinese (Mandarin)_Kind-hearted_Elder`，不包含 `Robot_Armor`、`Chinese (Mandarin)_Cute_Spirit`、英文 `Reliable Executive` 或 `Kind-hearted Elder` 标签，也不再使用 ` · ` 作为下拉分隔符。选择并保存 `Chinese (Mandarin)_Gentle_Senior` 后页面提示 `已使用 温和长辈 默认 TTS。`，声音摘要显示 `系统默认 TTS · 温和长辈 · Chinese (Mandarin)_Gentle_Senior`，语音预览来源显示 `MiniMax speech-2.8-hd · voice_id Chinese (Mandarin)_Gentle_Senior`，横向溢出 0。本次仍未点击“生成语音预览”，避免在可能配置真实 MiniMax key 的本地环境中触发第三方 TTS 调用。

## Latest Session Update - 2026-07-05 MiniMax 默认 TTS 可选音色

- 根据浏览器评论，本次把 `/personas/{id}/voice` 的“选择默认 TTS”从单按钮改成 MiniMax 中文普通话 system voices 静态列表；默认选中 `Chinese (Mandarin)_Kind-hearted_Elder`，保存按钮为“使用所选默认 TTS”。本轮不接入动态 `POST /v1/get_voice`。
- 后端 `GET /voice` 现在返回 `tts_model`、兼容旧调用的 `default_tts_options` 和 `default_tts_voices`；`POST /voice/default-tts` 校验所选 `voice_id`，并把 system voice 保存到 `VoiceModel.model_artifact_url=minimax://system-voice/<urlencoded_voice_id>`，不新增数据库字段或迁移。
- 语音合成时 `_voice_id_for_model()` 和 MiniMax provider 都能解析 `minimax://system-voice/...`，并继续兼容克隆音色 `minimax://voice/...`；未知默认 TTS `voice_id` 返回错误，不静默落到其他声音。
- 前端 `voiceModelSummary()` 和语音预览区显示当前语音来源：默认 TTS 显示 `MiniMax speech-2.8-hd · voice_id ...`，克隆音色显示“用户创建的模拟音色 ID：{voice_model.id}”，若有 MiniMax 克隆 artifact 则补充 clone `voice_id`。
- 已同步 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md` 和本进度账本；本次不运行 `docs/init.sh`，按规则只有用户明确要求完整基线验证时才运行。
- 验证：`python -m json.tool docs/feature-list.json` 退出码 0；`python -m pytest backend/tests/test_voice.py backend/tests/test_minimax_provider.py -q` 19 passed；`node --import tsx --test tests/voice.test.mjs` 9 passed；`npm.cmd --prefix frontend run test -- voice.test.mjs` 98 passed；`npm.cmd --prefix frontend run test` 98 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 服务与浏览器 smoke：`docker compose build backend frontend` 退出码 0，`docker compose up -d --no-deps --force-recreate backend frontend` 后 backend healthy、frontend started；Playwright + 本机 Chrome 打开 demo persona 的 `/voice`，默认 TTS select 当时有 34 个 MiniMax 中文普通话音色，包含 `Chinese (Mandarin)_Kind-hearted_Elder` 和 `Chinese (Mandarin)_Gentle_Senior`；选择 Gentle Senior 后页面显示 `MiniMax speech-2.8-hd · voice_id Chinese (Mandarin)_Gentle_Senior`，API config 返回 `model_artifact_url=minimax://system-voice/Chinese%20%28Mandarin%29_Gentle_Senior`，横向溢出 0。后续“默认 TTS 中文名称与真人声线过滤”切片将该列表收口为 32 个真人相关音色。为避免在可能配置真实 MiniMax key 的本地环境中触发第三方调用，本轮浏览器 smoke 未点击生成语音预览或真实克隆；合成 payload、未知 voice_id 拒绝和克隆来源文案由自动化测试覆盖。

## Latest Session Update - 2026-07-05 GLB 形象上传与展示闭环

- 根据用户确认计划，本次把 `/personas/{id}/avatar` 从选择风格、默认形象、图片资料生成和口型测试收口为单一 GLB 上传流程；当前只支持自包含 `.glb`，不处理 `.gltf` 外链贴图、VRM、动作文件、视频手势驱动、audio envelope 或 viseme 口型同步。
- 后端新增 `POST /api/personas/{id}/avatar/upload` 和 `GET /api/avatar-models/{id}/file`：上传接口只接受 `.glb`，保存到 `storage/avatar_models/{user_id}/{persona_id}/`，创建 selected `uploaded_ready`/`glb`/`user_upload`/`glb_upload` AvatarModel；文件接口按 JWT 用户隔离返回 `model/gltf-binary`；删除人物和清空当前账号数据会同步删除本地 GLB 文件。
- 前端 `frontend/src/lib/avatar.ts` 新增上传 helper、`uploaded_ready` 标签和 GLB URL 解析；`/personas/{id}/avatar` 改为 GLB 上传面板、上传/加载/成功/失败提示、当前模型记录和模型地址展示；`AvatarPreview` 使用 `GLTFLoader` 带 auth header 加载模型、居中缩放、补光、地面阴影和轻微待机旋转；`AvatarStage` 在 avatar/chat/regrets/wishes 共享 GLB 展示，无模型时只显示空态。
- 已同步 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md`、`docs/平台说明.md` 和本进度账本；`feat-047` 记录“GLB 形象上传与前端展示闭环”。旧 default/generate API 保留兼容，但不再作为当前前端流程。
- TDD RED：后端聚焦测试首次运行命中新上传路由缺失，返回 404；前端聚焦测试首次运行命中 `uploadAvatarModel` 与 `API_PATHS.avatar.upload` 缺失。实现后聚焦 GREEN：`python -m pytest backend/tests/test_avatar.py backend/tests/test_personas.py backend/tests/test_settings_data.py -q` 67 passed；`node --import tsx --test tests/avatar.test.mjs tests/routes.test.mjs tests/guided-experiences.test.mjs tests/chat.test.mjs` 40 passed。
- 收尾验证：`python -m json.tool docs/feature-list.json` 退出码 0；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`python -m pytest backend/tests/test_migrations.py -q` 2 passed；`http://localhost:8000/health` 返回 `{"status":"ok"}`。
- 服务与浏览器 smoke：`docker compose up --build -d backend frontend` 首次暴露既有 Alembic revision 链问题，`0007_memory_card_importance.py` 引用了不存在的 `0006_memory_audit_v2_persona_engine` revision；已将 `down_revision` 修正为实际 revision id `0006_audit_persona_engine`，随后同一 compose 命令通过，backend healthy、frontend started。浏览器刷新 `http://localhost:3000/personas/27e4e946-6b92-42a2-982c-fde85b36c284/avatar` 后已是 GLB 流程，旧“选择默认纪念形象 / 图片生成 / 生成 mock 3D 形象”文案不存在，文件 input accept 为 `.glb,model/gltf-binary`，横向溢出 0；上传临时最小 GLB 后状态为“GLB 模型已上传 / 模型加载成功”，canvas 存在，临时本地 GLB 文件已清理。chat/regrets/wishes 均有 GLB canvas、无“默认星空形象”、横向溢出 0；390x844 移动视口 avatar 页 canvas 293x448、模型加载成功、横向溢出 0，已恢复默认视口。
- 记录：`npm.cmd --prefix frontend run test -- avatar.test.mjs routes.test.mjs guided-experiences.test.mjs chat.test.mjs` 会被当前 `package.json` 测试脚本扩展为全量 `tests/*.test.mjs`，因此仍会命中既有、与本次 GLB 改造无关的 stale 源码断言（materials/memories/memory-space）。本轮使用直接 `node --import tsx --test ...` 覆盖指定前端文件。
- 本次未运行 `docs/init.sh`；按仓库规则只有用户明确要求完整基线验证时才运行。

## Latest Session Update - 2026-07-05 对话发送即时反馈

- 根据浏览器评论，本次只调整 `/personas/{id}/chat` 文本对话体验：点击发送后先即时追加用户消息，再显示带转圈图标的 `外婆正在想...` 临时回复，后端返回后用真实消息刷新；人物回复标签从 `外婆的星星` 改为直接显示 `外婆`。
- `handleSend` 现在先捕获 `trimmedDraft`，用它构造 optimistic user message 和 pending persona thinking message，并在等待 `sendMessage` 前清空输入框；发送失败时移除两条临时消息、恢复原输入并显示既有错误提示。
- `ChatSurface` 增加底部滚动锚点，消息数量变化时滚到末尾，确保新消息和思考中状态可见；未改后端 API、路由、schema 或数据库。
- 新增/更新 `frontend/tests/chat.test.mjs` 源码与 helper 约束，覆盖 optimistic/pending message helper、直接人物标签、spinner、输入框提前清空、失败恢复和 `scrollIntoView` 锚点。TDD RED：`npm.cmd --prefix frontend run test -- chat.test.mjs` 先退出码 1，命中旧实现缺少 `trimmedDraft`/提前清空/失败恢复/滚动锚点。
- GREEN 与验证：`npm.cmd --prefix frontend run test -- chat.test.mjs` 88 passed；`npm.cmd --prefix frontend run test` 88 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 浏览器 smoke：先运行 `docker compose up --build -d frontend`，镜像 build 通过但依赖 backend recreate 命中既有容器名冲突；随后用 `docker compose up -d --no-deps --force-recreate frontend` 重启前端。刷新 `http://localhost:3000/personas/27e4e946-6b92-42a2-982c-fde85b36c284/chat` 后发送“浏览器烟测消息”，即时 DOM 显示用户消息、`外婆正在想...`、`.animate-spin`、输入框为空、无 `外婆的星星`、横向溢出 0；最终回复替换临时思考消息且仍无旧标签。390x844 移动视口复验横向溢出 0、无 `外婆的星星`，已恢复默认视口。
- 本次改动文件：`frontend/app/personas/[id]/chat/page.tsx`、`frontend/src/lib/chat.ts`、`frontend/tests/chat.test.mjs`、`docs/progress.md`。
- 本次不改 `feature-list.json` 或 `docs/prd-checklist.md`，不处理视频手势 GLB/摄像头范围，也未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 删除人物详情下一步建议卡片

- 根据浏览器评论，本次只调整 `/personas/{id}` 人物详情页：删除“下一步建议”整张卡片，不改顶部主 CTA、资料概览、资料/记忆/互动功能卡片或后端 API。
- 新增 `frontend/tests/persona.test.mjs` 源码约束，确保人物详情不再包含“下一步建议”或 `primaryAction.description` 的卡片内容，同时保留顶部主 CTA。
- TDD RED：`npm.cmd --prefix frontend run test -- persona.test.mjs` 先退出码 1，命中旧实现仍包含“下一步建议”。
- GREEN 与验证：同命令复跑 85 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 浏览器 smoke：`docker compose up --build -d frontend` 后刷新 `http://localhost:3000/personas/27e4e946-6b92-42a2-982c-fde85b36c284`，页面不再出现“下一步建议”或其说明文案；顶部“开始对话”主按钮仍存在；资料、记忆、互动功能区直接接在资料概览后；横向溢出 0。
- 本次改动文件：`frontend/app/personas/[id]/page.tsx`、`frontend/tests/persona.test.mjs`、`docs/progress.md`。
- 本次不改后端 API、不新增路由、不更新 `feature-list.json`，也未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 人物详情基础信息只显示用户填写项

- 根据浏览器评论，本次继续调整 `/personas/{id}` 人物详情页“资料概览”内的“基础信息”：只保留用户创建资料卡片时填写的年龄、你们的关系和 TA 对你的称呼，移除系统默认写入的说话风格、情绪方式和禁止表达展示。
- 更新 `frontend/tests/persona.test.mjs` 中人物详情源码约束，要求“基础信息”区域包含年龄、关系和称呼，同时不包含说话风格、情绪方式或禁止表达。
- TDD RED：`npm.cmd --prefix frontend run test -- persona.test.mjs` 先退出码 1，命中旧实现仍展示“说话风格”。
- GREEN 与验证：同命令复跑 82 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 浏览器 smoke：`docker compose up --build -d frontend` 后发现本机仍有旧的 `next start -H 0.0.0.0 -p 3000` 进程抢占 3000 并返回旧页面，已停止该旧前端进程后刷新 `http://localhost:3000/personas/27e4e946-6b92-42a2-982c-fde85b36c284`。最终页面显示“基础信息”内有年龄 72 岁、你们的关系外婆、TA 对你的称呼小铭；不再显示说话风格、情绪方式、禁止表达或独立“人格设定”；横向溢出 0。
- 本次改动文件：`frontend/app/personas/[id]/page.tsx`、`frontend/tests/persona.test.mjs`、`docs/progress.md`。
- 本次不改后端 API、不新增路由、不更新 `feature-list.json`，也未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 移除 Profile 页面并迁移档案摘要

- 根据用户计划，本次不删除后端 profile API 或数据能力，但移除独立 `/personas/{id}/profile` 人格档案页面 UI；该深链现在重定向到 `/personas/{id}/uploads`，人物详情功能卡片和 `ROUTES` 不再暴露 profile 入口。
- 注：该轮曾把“档案摘要”卡片迁入 uploads；已被 2026-07-05 Uploads 自动档案摘要与结构化信息星标覆盖，当前 uploads 不再提供手动保存或从已审核记忆重生成摘要。
- `/personas/{id}` 顶部简介改为展示 `profile.profile_summary`；当前无摘要空态为“档案摘要将在新的资料上传解析后自动生成。”，不再在该位置展示创建人物时填写的 `short_bio`。
- TDD RED（该轮历史记录，已被后续自动摘要方案覆盖）：先更新前端测试后运行 `npm.cmd --prefix frontend run test`，按预期 5 failed，覆盖 profile route 不应暴露、workspace 不应包含 `/profile`、人物详情应读取 `profile_summary`、profile 页面应只做 redirect。
- 聚焦 GREEN：实现后 `npm.cmd --prefix frontend run test` 84 passed；收尾前当前工作区前端测试总数更新为 88 passed。
- 改动文件：`frontend/app/personas/[id]/uploads/page.tsx`、`frontend/app/personas/[id]/profile/page.tsx`、`frontend/app/personas/[id]/page.tsx`、`frontend/app/page.tsx`、`frontend/app/dashboard/page.tsx`、`frontend/src/lib/routes.ts`、`frontend/src/lib/memory-space.ts`、前端相关测试和 docs harness。
- 收尾验证：`python -m json.tool docs/feature-list.json` 退出码 0；`npm.cmd --prefix frontend run test` 88 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 浏览器 smoke（该轮历史记录，已被后续自动摘要方案覆盖）：当时验证 profile 深链重定向和人物详情不再出现“人格档案”入口；当前摘要生成与 uploads 展示以本轮自动摘要规则为准。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 独立产品介绍页与首页还原

- 根据用户计划，本次把上一轮嵌入首页 `#product-intro` 的路演展示移到独立 `/product-intro` 页面；首页恢复为原简版三卡产品概览，包含“把重要的人，整理成可信的星光档案。”、“创建档案”、“补充资料”和“开启陪伴”。
- 顶部导航 `产品介绍` 已从 `/#product-intro` 改为 `/product-intro`；`docs/展览路演材料.html` 仍是 docs 静态源材料，产品页只使用精选摘编，不使用 iframe、`dangerouslySetInnerHTML`、复制 style 块或旧 HTML class。
- `/product-intro` 使用现有 `StarShell`、`StarNav`、`StarPanel`、`FeatureTile`、`star-button`、`text-starGold`、`text-starCream` 和 `text-starMist`，展示“让记忆不止于回忆”、“为什么需要这个产品”、“我们提供什么”、“核心能力”、“演示闭环”和“技术与可信机制”；文案避免微信/QQ 一键导入、生产级 VRM/视频通话、硬延迟等未验证承诺，声音/3D 按当前 demo/mock 能力表述。
- 已新增/更新源码测试：`frontend/tests/product-intro.test.mjs`、`frontend/tests/homepage-cta.test.mjs`、`frontend/tests/memory-space.test.mjs`、`frontend/tests/routes.test.mjs`，覆盖独立页面、首页还原、导航目标、禁止原始 HTML 嵌入和禁止旧路演 class/未支持声明。
- TDD RED：`npm.cmd --prefix frontend run test -- homepage-cta.test.mjs memory-space.test.mjs routes.test.mjs product-intro.test.mjs` 先退出码 1，命中首页仍是路演展示、导航仍为 `/#product-intro`、`ROUTES.productIntro` 缺失、`frontend/app/product-intro/page.tsx` 缺失。GREEN 后同命令 82 passed。
- 收尾验证：`python -m json.tool docs/feature-list.json` 退出码 0；`npm.cmd --prefix frontend run test` 82 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，构建包含静态 `/product-intro` 路由。
- 浏览器 smoke：`docker compose up --build -d frontend` 后检查 `/` 与 `/product-intro`。1280x720 和 390x844 下顶部导航 `产品介绍` 均指向 `/product-intro`；首页存在还原后的简版产品介绍且不含路演重文案；产品介绍页存在路演摘编内容；横向溢出 0、目标块 overlap 检查为空、iframe 数量 0、旧 `hero`/`section-title`/`pain-card`/`caps-card` class 为空、未支持声明检查为 false。
- 同步文档：`docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md`、`docs/平台说明.md` 和本进度账本已更新；本次不改后端 API，不新增后端路由，不运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 人物详情基础信息并入资料概览

- 根据浏览器评论，本次只调整 `/personas/{id}` 人物详情页展示：删除独立“人格设定”卡片，把年龄、你们的关系、TA 对你的称呼、说话风格、情绪方式和禁止表达并入上方“资料概览”的“基础信息”区域；资料统计和资料建议继续保留。
- 新增 `frontend/tests/persona.test.mjs` 源码约束，确保人物详情不再包含“人格设定”，且“资料概览”源码区域包含基础信息和核心字段。
- TDD RED：`npm.cmd --prefix frontend run test -- persona.test.mjs` 先退出码 1，命中旧页面仍包含“人格设定”。
- GREEN 与验证：同命令复跑 78 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 浏览器 smoke：`docker compose up --build -d frontend` 后刷新 `http://localhost:3000/personas/27e4e946-6b92-42a2-982c-fde85b36c284`，资料概览内存在基础信息、年龄 72 岁、关系、称呼、说话风格、情绪方式和禁止表达，页面不再出现“人格设定”，默认视口横向溢出 0；移动 390x844 下同样无“人格设定”、基础信息仍在资料概览内、横向溢出 0。临时移动视口已恢复默认。
- 本次改动文件：`frontend/app/personas/[id]/page.tsx`、`frontend/tests/persona.test.mjs`、`docs/progress.md`。
- 本次不改后端 API、不新增路由、不更新 `feature-list.json`，也未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 资料识别文本统一结构化解析

- 根据用户确认的计划，本次把资料解析链路收口为“单资料识别文本 -> 严格六模块 JSON memory_extraction -> 待审核 MemoryCard -> 全人物 memory_document_generation 汇总 Markdown/trust”：照片、视频、声音和文字仍先走既有 OCR/图片理解、视频理解、ASR 或文本抽取，并统一写入 `ParsedChunk.content`。
- `memory_extraction` 的 mock 和 DashScope adapter 现在输出 `structured_memory_json`，固定模块为 `basic_fact`、`relationship`、`preference`、`habit`、`expression_style`、`shared_event`；解析服务在写入 MemoryCard 前校验该结构，旧扁平 `memories` 输出会让 parse job 失败并记录错误，缺少来源证据的候选只进入 warnings/unclassified，不直接入库。
- parse job output_json 新增 `structured_memory_json` 和 `memory_extraction_provider_*`，MemoryCard evidence 记录 `structured_memory_source`、模块名和结构化解析 warnings；`memory_document_generation` 仍保留为全人物结构化 Markdown 与唯一 trust 汇总阶段。
- 同步文档：`docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md`、`docs/平台说明.md` 和本进度账本已更新为单资料严格 JSON 抽取 + 全人物汇总链路。
- TDD RED：`python -m pytest backend/tests/test_provider_gateway.py::test_mock_memory_extraction_returns_strict_module_json backend/tests/test_parsing.py::test_parse_job_uses_strict_module_json_for_memory_cards backend/tests/test_parsing.py::test_parse_job_fails_when_memory_extraction_lacks_strict_json -q` 先 3 failed，暴露 mock 无 `structured_memory_json`、解析层不接受新结构和旧格式未被拒绝。
- 聚焦 GREEN：同命令 3 passed；`python -m pytest backend/tests/test_dashscope_provider.py -q` 4 passed；`python -m pytest backend/tests/test_provider_gateway.py backend/tests/test_parsing.py backend/tests/test_profile.py backend/tests/test_memories.py backend/tests/test_dashscope_provider.py -q` 38 passed。
- 收尾验证：`python -m json.tool docs/feature-list.json` 退出码 0；`python -m pytest backend/tests -q` 201 passed；`npm.cmd --prefix frontend run test` 77 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 本次不新增数据库表、不新增 HTTP 路由、不改变上传时机、不运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 我的星空星星删除入口

- 根据浏览器评论，本次给 `/dashboard` 的“我的星空”星星卡增加删除入口：每张卡保留进入人物详情的点击区域，并新增独立 `删除星星` 按钮；点击后通过浏览器确认，再调用现有 `DELETE /api/personas/{id}`，成功后从列表移除。
- 新增 `frontend/src/lib/persona.ts` 的 `deletePersona(id)` helper，复用既有 `API_PATHS.personas.detail(id)` 和 auth header；不改后端路由、数据库或删除语义。
- 新增 `frontend/tests/dashboard-delete.test.mjs`，TDD RED 先验证 helper 和按钮缺失，GREEN 后覆盖 DELETE 请求、确认弹窗和 Dashboard 删除按钮源码约束。
- 已执行验证：`node --import tsx --test tests/dashboard-delete.test.mjs` 2 passed；`python -m json.tool docs/feature-list.json` 退出码 0；`npm.cmd --prefix frontend run test` 76 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 浏览器 smoke：`docker compose up --build -d frontend` 后刷新 `http://localhost:3000/dashboard`，删除按钮可见且无横向溢出；按用户要求删除 `a's'd`、`123`、`asd`、`abc`、`你好` 五颗星星，刷新后只剩 `外婆` 一颗星星。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 Uploads 承接记忆审核与唯一可信度

- 根据用户计划，本次把资料解析结果审查从 `/personas/{id}/memories` 迁到 `/personas/{id}/uploads`：创建星星成功后跳转 uploads；uploads 同页提供资料上传、结构化记忆 Markdown、分类记忆卡片确认/编辑/删除、自定义维度、“记忆可信度”和“完成审核，点亮星星”；完成审核后留在 uploads 并显示成功提示。
- `/personas/{id}/memories` 已收窄为“让TA讲几段回忆”和语义搜索；删除审核卡片、可信度、档案健康分、待审核、开放冲突、冲突中心、最近事件/历史等页面展示。Dashboard、人物详情和 profile 页面也不再展示 trust 数字、可信度组成或重新计算按钮。
- 后端 Provider Gateway 新增 `memory_document_generation`，mock 和 MiniMax 文本 LLM 路径均支持；资料解析后基于当前 active materials、parsed chunks 和 memory cards 生成 `structured_memory_md`、`trust_score`、`trust_level`、`trust_rationale` 和 `suggestions`，写入解析/可信度 job output_json，并更新 `persona.trust_score`。profile GET、记忆确认/编辑/删除、profile 编辑/重生成只刷新档案/长期 Markdown，不覆盖 trust；`POST /recalculate-trust` 保留兼容但重新运行同一生成链路。
- 已完成 TDD：后端 provider/parsing/profile/memories 测试先红后绿；前端 persona/memories/memory-space/homepage 源码测试约束创建跳转 uploads、memories 页面禁用审核/trust 文案、trust 展示只剩 uploads。
- 收尾验证通过：`python -m json.tool docs/feature-list.json > $null` 退出码 0；`python -m pytest backend/tests/test_provider_gateway.py backend/tests/test_parsing.py backend/tests/test_materials.py backend/tests/test_profile.py backend/tests/test_memories.py -q` 40 passed；`python -m pytest backend/tests -q` 201 passed；`npm.cmd --prefix frontend run test` 76 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。浏览器 smoke 已覆盖创建页提交后跳转 uploads、uploads 唯一“记忆可信度”/审核卡片/点亮按钮、点亮后留在 uploads；headless Chrome smoke 覆盖 memories 仅保留“让TA讲”和语义搜索且无审核/trust 禁用词，Dashboard/人物详情/profile/memories 不展示“可信度”。
- 浏览器 smoke 过程中发现 `get_or_create_profile` 并发创建 profile 时可能触发 `persona_profiles.persona_id` 唯一键冲突；已新增 `test_get_or_create_profile_recovers_from_concurrent_insert` 红绿测试，并在 `backend/app/services/profile.py` 用 nested transaction 处理并发插入后重新读取已创建 profile。
- 改动文件：`backend/app/providers/gateway.py`、`backend/app/providers/minimax.py`、`backend/app/services/parsing.py`、`backend/app/services/profile.py`、`backend/app/api/routes/profile.py`、`backend/app/services/data_exports.py`、后端相关测试、`frontend/app/personas/[id]/uploads/page.tsx`、`frontend/app/personas/[id]/memories/page.tsx`、`frontend/app/personas/[id]/profile/page.tsx`、`frontend/app/personas/[id]/page.tsx`、`frontend/app/dashboard/page.tsx`、`frontend/app/personas/new/page.tsx`、`frontend/src/lib/persona.ts`、`frontend/src/lib/memory-space.ts`、前端相关测试和 docs harness。

## Latest Session Update - 2026-07-05 首页记忆审核说明文案

- 根据浏览器评论，本次只调整首页 `#memory-review` 区块的一句说明文案，不改后端 API、路由、人物内记忆档案馆能力或 `feature-list.json`。
- 旧文案从“记忆档案馆用于...”改为偏功能性的“审核流程支持确认、修正、停用或删除资料解析出的记忆，并查看每条记忆的来源、冲突和历史。进入审核前，需要先选择一个人物档案。”，避免把功能描述写成“记忆档案馆”这个对象在做事。
- 已新增 `homepage-cta.test.mjs` 约束首页记忆审核文案：`#memory-review` 不再包含旧的 `记忆档案馆用于`，且必须包含新的功能型说明。
- 改动文件：`frontend/app/page.tsx`、`frontend/tests/homepage-cta.test.mjs`、`docs/progress.md`。
- TDD RED：`npm.cmd --prefix frontend run test -- homepage-cta.test.mjs` 退出码 1，命中旧文案仍存在；GREEN 后同命令 70 passed。
- 已执行验证：`npm.cmd --prefix frontend run test` 70 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`rg "记忆档案馆用于" frontend/app/page.tsx` 无旧文案命中。
- 浏览器 smoke：`docker compose up --build -d frontend` 后复验 `http://localhost:3000/`，`#memory-review=true`、新文案存在、旧文案不存在、横向溢出 0。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 首页双 CTA 完全统一样式

- 根据浏览器评论，本次只调整首页首屏两个 CTA：`创建属于TA的星星` 与 `进入我的星空` 风格完全统一。
- 首页 hero CTA 继续共享 `home-hero-actions` / `home-hero-action` 尺寸布局；两个按钮现在都使用同一组 `star-button star-cta home-hero-action` class，不再保留 `home-hero-secondary` 次级样式或独立背景、边框、阴影。
- `homepage-cta.test.mjs` 已更新为断言两个 hero CTA 的 className 完全一致、桌面固定同宽、不再出现旧的 `sm:min-w-[12.5rem]` 或 `home-hero-secondary`。
- 已执行 TDD：`npm.cmd --prefix frontend run test -- homepage-cta.test.mjs` 先退出码 1，命中两个按钮 class 不一致；实现后同命令 69 passed。
- 已执行检查：`npm.cmd --prefix frontend run test` 69 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 浏览器 smoke：`docker compose up --build -d frontend` 后复验 `http://localhost:3000/`。默认桌面视口下两个 hero CTA 的 className、背景色、背景图、边框色、阴影、颜色、字重、padding、宽高和 top 均一致，mismatches 为空，均为 248x48、widthDelta 0、heightDelta 0、topDelta 0、横向溢出 0；390x844 移动视口下两个 CTA className、背景、边框、阴影和宽高也完全一致，纵向堆叠，mismatches 为空，横向溢出 0。临时 viewport 已恢复默认。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 创建星星页保存进度条

- 根据浏览器评论，本次只调整 `/personas/new` 保存过程提示：按钮下方从单行状态文本改为进度条形式，并在进度条下方展示当前阶段说明。
- 新增 `buildCreatePersonaProgress` 前端 helper，将创建阶段映射到可访问进度条文案和百分比：准备演示会话 20%、保存资料卡片 45%、上传回忆文件 75%、进入记忆审核 95%；上传阶段继续显示“正在上传 X 个回忆文件...”。
- 创建页保存状态改为 `CreatePersonaProcessingStage`，渲染 `role="progressbar"`、`aria-live="polite"`、`aria-valuenow` 和 `aria-valuetext`；后端 API、创建 payload、上传时机和上传失败恢复入口不变。
- TDD RED：`npm.cmd --prefix frontend run test -- persona.test.mjs` 退出码 1，按预期暴露 `buildCreatePersonaProgress is not a function`。
- 聚焦 GREEN：`node --import tsx --test tests/persona.test.mjs` 在 `frontend/` 下退出码 0，6 passed。
- 完整前端验证：`npm.cmd --prefix frontend run test` 退出码 0，68 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，`/personas/new` 构建通过。
- 浏览器 smoke：使用当前构建临时 `next start` 端口 3110 验证 `/personas/new`；桌面视口无文件提交后立即出现 `role="progressbar"`，`aria-valuenow=20`，阶段说明为“正在准备演示会话...”且位于进度条下方，横向溢出 0；移动 390x844 下同样出现进度条和阶段说明，横向溢出 0。应用内浏览器不支持安全注入本地文件到 file input，上传数量用 helper 单测覆盖。
- 临时 3110 服务已停止，本次仍遵守仓库规则，未运行 `docs/init.sh`，未更新 `feature-list.json`。

## Latest Session Update - 2026-07-05 删除人物工作台导航

- 根据用户给定计划，本次删除所有人物相关页面的整块人物工作台区域，包括标题、分组按钮、当前页 active 状态和返回人物工作台按钮；不新增替代面包屑、返回链接或轻量人物内页导航。
- 人物详情页继续保留下方资料、记忆、互动功能卡片，作为进入资料上传、资料任务、记忆档案馆、人格档案、星星对话、遗憾对话室、心愿延续系统、声音和 3D 形象的主要入口。
- 前端移除 `StarSite.tsx` 中的 `PersonaWorkspaceNav` 组件定义，移除各人物页面调用；`getPersonaWorkspaceNavGroups()` 保留用于人物详情页功能卡片。
- 新增/调整 `frontend/tests/memory-space.test.mjs` 约束人物功能页源码不再包含 `<PersonaWorkspaceNav>` 调用、`人物工作台导航` 或 `返回人物工作台` 文案。
- 已执行验证：`python -m json.tool docs/feature-list.json` 退出码 0；`npm.cmd --prefix frontend run test` 69 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 浏览器 smoke：使用 `POST /api/auth/demo` 生成 demo token 后访问 `http://localhost:3000`。745x860 下 `/personas/{id}` 无人物工作台块、无返回人物工作台按钮，可见“下一步建议”和资料/记忆/互动功能卡片，横向溢出 0；`/uploads`、`/jobs`、`/memories`、`/profile`、`/chat`、`/regrets`、`/wishes`、`/voice`、`/avatar` 均无人物工作台块或返回人物工作台按钮，横向溢出 0；移动 390x844 下人物总览和 chat 横向溢出均为 0。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-05 首页 CTA 编排优化

- 根据用户给定计划，本次只调整首页首屏 CTA 展示：`创建属于TA的星星` 与 `进入我的星空` 已合并为同一首屏按钮组；桌面端并排展示，移动端上下排列且宽度一致。
- `#memory-review` 区块已移除单独的 `进入我的星空` 按钮，只保留记忆审核说明文案；路由、顶部导航和后端 API 均未改变，两个 CTA 仍分别指向 `/personas/new` 与 `/dashboard`。
- 新增 `frontend/tests/homepage-cta.test.mjs` 约束首页首屏 CTA 分组和 `#memory-review` 去重；同时补齐 `StarSite` 中当前人物页面已引用的 `PersonaWorkspaceNav` 导出，避免干净构建时人物功能页导入失败。
- 已执行验证：`npm.cmd --prefix frontend run test` 67 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 浏览器 smoke：停止旧 Docker frontend 后，用当前本地构建启动 `next start` 到 `http://localhost:3000/`；桌面 1280x720 与移动 390x844 下两个 CTA 均在首屏可见、目标 href 正确、按钮不重叠、横向溢出 0；点击 `创建属于TA的星星` 到 `/personas/new`，点击 `进入我的星空` 到 `/dashboard`；`#memory-review` 内 `a[href="/dashboard"]` 数量为 0 且无 `进入我的星空` 文案。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。`docker compose up --build -d frontend` 曾暴露当前未跟踪前端组件状态在 Docker build context 中不稳定，因此本轮浏览器验收使用本地 Next production server；backend 容器保持运行。

## Latest Session Update - 2026-07-05 创建星星页评论修复

- 根据浏览器评论，本次只调整 `/personas/new` 创建星星页前端体验，不改后端 API、不改上传时机、不运行 `docs/init.sh`。
- `TA 是我的` 已从关系下拉框改为自由输入框，placeholder 为“例如：妈妈、外婆、朋友、老师”，仍写入既有 `relationship_to_user` payload；必填错误文案已同步。
- 备注区标题改为“有关TA的一切都可以写在这里”，placeholder 改为“TA的兴趣爱好、性格特征等”，创建资料卡片简介中的前缀同步为“有关TA的一切：”。
- 上传区在选择文件后展示“已选择待上传的回忆”清单，按照片/视频/声音/文字展示文件名、MIME 类型或扩展名和格式化大小；真实上传仍发生在点击保存并成功创建 persona 后。
- 保存按钮下方新增 `aria-live="polite"` 实时处理提示，覆盖“正在准备演示会话... / 正在保存资料卡片... / 正在上传 X 个回忆文件... / 正在进入记忆审核...”阶段文案；上传失败时保留既有“去补传资料”恢复入口。
- TDD RED：`npm.cmd --prefix frontend run test -- persona.test.mjs materials.test.mjs` 退出码 1，按预期暴露 `buildCreatePersonaShortBio` 和 `describeSelectedUploadFiles` 缺失。
- 聚焦 GREEN：同命令退出码 0，63 passed。
- 完整前端验证：`npm.cmd --prefix frontend run test` 退出码 0，63 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，`/personas/new` 构建通过。
- 浏览器 smoke：既有 `localhost:3000` 服务仍是旧资产，因此在临时 `next start` 端口 3107 验证当前构建；桌面检查确认 `TA是我的` 为 input、旧关系 select 不存在、备注标题和 placeholder 正确、4 个 file input 存在、横向溢出 0；点击保存后按钮下方出现“正在准备演示会话...”实时提示且无页面错误；移动 390x844 检查确认字段可见且横向溢出 0。Codex in-app Browser 不支持真实文件上传，已用 helper 单测覆盖已选文件清单的类型/名称/大小展示逻辑。
- 临时 3105/3106/3107 服务已停止，in-app browser 已返回 `http://localhost:3000/personas/new`。

## Latest Session Update - 2026-07-05 首页底部星光故事区删除

- 根据浏览器评论，本次只删除首页最底部 `#star-stories` 独立“星光故事”展示区，包括标题、说明、“创建档案”和“查看已有星星”按钮。
- 首页上方首屏、`#product-intro` 产品介绍、`#memory-review` 记忆审核说明和顶部导航保持不变；人物内 `/personas/{id}/memories` 记忆档案馆的回忆讲述能力继续保留。
- 本次不改后端 API、不改路由、不恢复独立 `/personas/{id}/stories` 页面，也不更新 `feature-list.json`。
- 已新增前端源码约束测试，防止首页再次渲染独立 `star-stories` 区块；TDD RED 为 `npm.cmd --prefix frontend run test -- memory-space.test.mjs` 退出码 1，命中旧 `star-stories` 区块；GREEN 后同命令 64 passed。
- 已执行检查：`rg "star-stories|星光故事|查看已有星星" frontend/app/page.tsx` 无命中；`npm.cmd --prefix frontend run test` 64 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 浏览器 smoke：首次刷新 `http://localhost:3000/` 发现仍为旧前端资产，随后运行 `docker compose up --build -d frontend` 重建服务；复验 `#product-intro=true`、`#memory-review=true`、`#star-stories=false`、`星光故事=false`、`查看已有星星=false`、`创建属于TA的星星=true`，横向溢出 0。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-04 三类体验页面拆分与对话页收口

- 根据用户给定计划，本次保留 `/`、`/dashboard`、`/personas/new`、`/personas/{id}` 和当前人物内功能页 URL，不改后端 API，不恢复 `/login`、`/register`、`/settings/data`、`/settings/providers` 或独立 `/personas/{id}/stories` 前端入口。
- `MEMORY_SPACE_NAV_ITEMS` 已同步为产品级四入口：`首页 -> /`、`产品介绍 -> /#product-intro`、`创建档案 -> /personas/new`、`我的星空 -> /dashboard`；全局顶部导航不再展示 `记忆审核` 或 `星光故事`。
- 当时新增的人物内分组入口已在 2026-07-05 用户反馈后删除；当前只保留人物详情页下方资料、记忆、互动功能卡片作为进入资料上传、资料任务、记忆档案馆、人格档案、星星对话、遗憾对话室、心愿延续系统、声音和 3D 形象的入口。
- 人物详情页从原先平铺功能入口改为“下一步建议 + 分组功能区”，主 CTA 按状态优先级展示：无资料时补充资料，有待审核记忆时审核记忆，审核完成后开始对话；完整功能入口仍保留在工作台分组中。
- 创建星星页只在页面内部展示 `资料卡片 -> 上传回忆 -> 保存并进入审核` 阶段流程，创建成功后继续进入 `/personas/{id}/memories`，不把创建阶段放入全局导航。
- 对话页收口为纯对话工作区：`/personas/{id}/chat` 只保留文字、视频手势、语音三种对话模式、输入框和侧边 `AvatarStage` 数字人；遗憾对话室和心愿延续系统拆为 `/personas/{id}/regrets` 与 `/personas/{id}/wishes` 轻量引导页，复用现有 conversation/message API，不新增后端心愿数据模型或提醒策略。
- 记忆档案馆继续使用 `/personas/{id}/memories`，页面标题为“记忆档案馆”，保留分类审核、可信度横幅、6 维度卡片、审计仪表盘、语义搜索、冲突中心和历史时间线，并承接来源可追溯的回忆讲述展示；仍不恢复独立 `/personas/{id}/stories` 页面。
- 已完成 TDD RED/GREEN：先更新 routes、chat、guided-experiences 和 memory-space 测试，初次运行暴露缺少 regrets/wishes 路由、guided helper、口型 helper 和工作台分组入口；实现后聚焦测试通过。
- 已执行检查：`python -m json.tool docs/feature-list.json` 退出码 0；`npm.cmd --prefix frontend run test` 61 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 浏览器 smoke：使用系统 Chrome + Playwright 访问当前 `http://localhost:3000` 和 `http://localhost:8000` demo API。971x860 视口下 `/personas/{id}/chat` 无“共同回忆”故事面板、无三功能卡片文案，侧边 `AvatarStage` 数字人可见且与输入区并排；`/personas/{id}/memories` 可见“记忆档案馆”、回忆讲述区、“让TA讲一段回忆”和语义搜索区；`/personas/{id}/regrets` 先问“以前没说的话”，`/personas/{id}/wishes` 先问“想完成的心愿”。两页实际提交输入后均显示用户消息、出现人物回复标记且无发送错误。移动 390x844 下 chat/memories/regrets/wishes 横向溢出均为 0。
- 本次仍遵守仓库规则，未运行 `docs/init.sh`。

## Previous Session Update - 2026-07-04 Homepage Tabs and Motion

- 根据用户确认的首页锚点方案，本次只调整首页和共享前端导航，不恢复 `/login`、`/register`、`/settings/data`、`/settings/providers` 或独立 `/personas/{id}/stories` 页面，不新增后端 API，不扩大产品范围。
- 首页顶部 tab 已统一为 `首页`、`产品介绍`、`创建档案`、`记忆审核`、`星光故事`；`产品介绍`、`记忆审核` 和 `星光故事` 指向首页锚点，`创建档案` 继续指向 `/personas/new`。移动端顶部 tab 保持可见且无横向页面溢出。
- 首屏 `StarPlanetScene` 只调大当前星球视觉运动参数：主 group yaw/pitch、星球 wobble、星环 wobble 和粒子漂移幅度更明显；未改 `AvatarPreview` 或对话/形象页 3D 预览。
- 首页新增 `#product-intro`、`#memory-review`、`#star-stories` 三个锚点区块，分别说明产品闭环、记忆审核入口和基于已审核记忆的星光故事体验；后续三类体验拆分后，回忆讲述由记忆档案馆承接，不恢复独立 stories 页面。
- PRD 前端覆盖核对：当前显式页面覆盖 Dashboard、创建人物、人物详情、资料上传、解析任务、记忆审计、人格档案、数字人对话、声音设置和形象设置；故事、数据设置、模型设置只有后端 API/helper 或对话页入口承接，非独立页面；登录/注册 UI、设置页和独立 stories 页是当前星空前端产品取舍；P1/P2 主动关怀、心愿延续、邀请家人和付费页仍暂缓/未覆盖。
- 已执行 TDD RED/GREEN：先更新 `frontend/tests/memory-space.test.mjs` 断言五个 tab 与 href，`npm.cmd --prefix frontend run test -- memory-space.test.mjs` 初次失败于旧三项导航；实现后同命令 56 passed。
- 完整前端验证：`npm.cmd --prefix frontend run test` 56 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，构建路由仍不包含 login/register/settings/stories。
- 浏览器 smoke：因既有 `localhost:3000` 服务是旧资产，另从当前工作区启动 `npm.cmd exec next dev -- -p 3100`，验证 `http://localhost:3100/`。桌面 1280x720：五个 tab 标签和 href 正确、三个锚点存在、canvas 数量 1、横向溢出 0、截图采样 `BrightSamples=6102/7722`、`ColorBuckets=121`；移动 390x844：五个 tab 均在视口内、href 正确、锚点存在、canvas 数量 1、横向溢出 0、截图采样 `BrightSamples=8118/9165`、`ColorBuckets=96`。
- 本次遵守仓库规则，未运行 `docs/init.sh`。

## Latest Session Update - 2026-07-04 数字人交互与审核界面视觉对齐

- 根据用户计划，本次继续以当前工作区为基础，不直接合并 `yawen`，不按本轮计划编辑 `backend/`，只收口对话页数字人交互、审核页视觉和对应文档。
- 对话页按参考图改为左侧三模式对话区、右侧大幅 `AvatarStage` 数字人舞台；`loadChat()` 读取现有 avatar config，优先展示 selected 可渲染 AvatarModel，其次展示可显示 preview image，否则回退星空人像占位。形象页复用同一 `AvatarStage`，选择默认形象或 mock 生成后回到对话页即可替换右侧占位。
- 记忆审核页标题改为“记忆解析与审核”，首屏保留可信度横幅、重新解析/新增维度按钮、6 个维度卡片和底部“完成审核，点亮星星”CTA；维度确认/删除只由前端循环调用现有 `confirmMemory`/`deleteMemory`，编辑仍只更新单条现有记忆，不新增后端维度模型。
- 新增前端 helper 测试覆盖 avatar display source 优先级、可用 preview image 判断和维度批量动作目标选择；同步 `docs/README.md`、`docs/feature-list.json`、`docs/prd-checklist.md` 和 `docs/平台说明.md`，明确本轮是前端视觉与交互收口，后端能力边界不变。
- 验证通过：`python -m json.tool docs/feature-list.json` 退出码 0；`npm.cmd --prefix frontend run test` 退出码 0，56 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0。
- 浏览器 smoke 通过：本轮先在临时端口 3102 对当前源码执行 Playwright smoke，随后停止旧 3000 node 进程并运行 `docker compose up --build -d frontend`，在 `http://localhost:3000` 复验通过；覆盖对话页三种互动模式、默认星空占位、形象页选择默认纪念形象、回到对话页后数字人 canvas 非空、记忆解析与审核页可信度横幅/6 维卡片/底部 CTA，以及 1365x768 与 390x844 视口无横向溢出；smoke demo persona 均已通过现有 DELETE API 清理，临时 3102 dev server 已停止。
- 后端守卫：`backend/` 在本轮开始前已经存在大量工作区脏改；任务前保存的 backend 快照与最终快照哈希不一致，比较发现差异集中在 `backend/app/schemas/profile.py` 和 `backend/app/services/persona_engine_prompt.py` 两个路径相对该快照的状态变化。本轮未用 `apply_patch` 或 shell 写入编辑 `backend/`，未按本任务修改后端 API/逻辑；这些后端差异已按边界风险记录，未擅自回滚。

## Latest Session Update - 2026-07-04 Markdown Memory Context

- 根据用户计划，停用并移除 embedding 运行入口：删除本地 GPU embedding worker/provider/service 和 `backend/requirements-embedding.txt`，解析、手动记忆、纠错和聊天不再写入或读取 embedding；`memory_cards.embedding*` 字段和 Alembic `0004` 保留兼容旧库。
- 新增 `backend/app/services/memory_markdown.py`：长期记忆写入 `storage/memory_context/{persona_id}/long_term_memory.md`，只包含 confirmed/corrected 且未删除记忆；短期记忆写入 `short_term_memory.md`，按人物聚合所有未删除会话消息；删除人物和清空账号会移除对应 memory_context 缓存。
- `send_text_message` 改为读取长期/短期 Markdown，上下文过长时调用 Provider Gateway `memory_context_compression`，失败时确定性截断兜底；`message_citations` 来自 selected memory ids；metadata 保留兼容 `retrieval` 字段但来源为 `memory_markdown`。
- Provider settings 不再返回 `local_gpu`，写入 `EMBEDDING_PROVIDER`、`LOCAL_EMBEDDING_*` 或 `LOCAL_GPU_WORKER_URL` 返回 400；MiniMax/OpenAI-compatible provider capabilities 增加 `memory_context_compression`。
- 验证中顺手修复阻断基线的问题：`test_audit.py` 改为普通同目录导入并放宽与当前自动解析/时间线排序一致的断言；`test_profile.py` 对齐 persona engine mock summary；`frontend/src/lib/avatar.ts` 去掉错误 type guard；记忆审计页保留已有 audit 子组件定义；Alembic `0006` revision id 缩短为 `0006_audit_persona_engine`，避免 PostgreSQL `alembic_version.version_num VARCHAR(32)` 启动失败。
- 已执行检查：聚焦后端 `python -m pytest backend/tests/test_chat.py backend/tests/test_memories.py backend/tests/test_parsing.py backend/tests/test_provider_settings.py backend/tests/test_config.py backend/tests/test_memory_markdown.py backend/tests/test_provider_gateway.py backend/tests/test_minimax_provider.py backend/tests/test_personas.py::test_delete_persona_soft_deletes_prd_related_records backend/tests/test_settings_data.py::test_clear_current_account_data_soft_deletes_owned_domain_records -q` 56 passed；`python -m pytest backend/tests -q` 194 passed；`npm.cmd --prefix frontend run test` 56 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`python -m json.tool docs/feature-list.json` 退出码 0；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，194 backend tests、56 frontend tests、frontend lint/build 和 Compose config 均通过；`docker compose up --build -d backend frontend` 退出码 0，backend healthy、frontend started。
- 浏览器/API 验收：创建测试人物和 confirmed 记忆后，聊天 metadata 为 `provider=minimax`、`capability=chat_llm`、`memory_context.source=memory_markdown`，`selected_memory_ids` 与 `message_citations` 指向同一记忆；容器内 `long_term_memory.md` 与 `short_term_memory.md` 均包含 `MD-CONTEXT-ACCEPTANCE`；in-app Browser 打开 `/personas/1de5db0a-ec9c-4846-a2ac-a35a80c1cf6b/chat`，页面展示测试人物和基于 Markdown 记忆的回复，未出现 `<think>`。

## Latest Session Update - 2026-07-04 Memory Audit v2 星空集成

- 根据用户计划，本次不直接合并 `origin/jinru`，只吸收 `Memory_Audit_v2`、`Persona_Engine_System_Prompt.md` 和 `展览路演材料.html` 的设计/内容，并按当前项目 FastAPI/SQLAlchemy/Next.js 星空风格重写。
- 后端新增 Memory Audit v2：扩展 `audit_logs`，新增 `memory_conflicts` 和 0006 增量迁移；新增 audit logs/summary/report/dashboard/conflicts/resolve/search/history API；所有 audit API 复用 JWT 用户隔离，跨用户访问返回 404。
- 审计事件已接入记忆创建、编辑、确认、拒绝、停用、删除，对话记忆引用和纠错，profile 手动编辑、重生成和可信度变化，story 引用记忆，以及记忆搜索；写入都参与当前事务，不使用不存在的 `"system"` 外键。
- Persona Engine prompt 已归档为 `docs/Persona_Engine_System_Prompt.md`，代码从文档加载 prompt 并新增 `persona_profile_analysis` provider capability；显式 `POST /api/personas/{id}/profile/regenerate` 保存完整 `persona_engine_json` 和生成时间，解析失败回退 deterministic profile 并记录 fallback，不影响聊天 prompt 或自动记忆审核刷新。
- 前端 `/personas/{id}/memories` 已升级为星空主题“记忆档案馆”：保留分类审核卡片和“完成审核，点亮星星”流程，新增审计仪表盘、语义搜索、冲突中心、最近事件和单条记忆历史；未新增独立 `/audit` 页面。
- `docs/展览路演材料.html` 已归档为 docs 静态资料；`docs/feature-list.json` 新增 `feat-043` 记录本次集成，因为当前账本中 `feat-042` 已用于长期/短期记忆 Markdown。
- 已完成的聚焦验证：`python -m pytest backend/tests/test_audit.py backend/tests/test_profile.py::test_profile_regenerate_stores_persona_engine_json_and_records_job backend/tests/test_provider_gateway.py::test_mock_gateway_returns_persona_profile_analysis backend/tests/test_provider_gateway.py::test_minimax_gateway_routes_persona_profile_analysis_when_configured backend/tests/test_minimax_provider.py::test_minimax_persona_profile_analysis_uses_persona_engine_prompt backend/tests/test_migrations.py::test_memory_audit_v2_migration_uses_incremental_explicit_operations -q` 11 passed；`npm.cmd --prefix frontend run test -- routes.test.mjs audit.test.mjs memories.test.mjs` 56 passed。
- 完整验证通过：`python -m json.tool docs/feature-list.json > $null` 退出码 0；`python -m pytest backend/tests/test_audit.py backend/tests/test_profile.py backend/tests/test_provider_gateway.py backend/tests/test_minimax_provider.py backend/tests/test_migrations.py -q` 34 passed；`python -m pytest backend/tests -q` 194 passed；`npm.cmd --prefix frontend run test` 56 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`docker compose config > $null` 退出码 0。
- 浏览器 smoke 通过：使用临时 demo persona 打开 `http://localhost:3000/personas/{id}/memories`，桌面视口确认“记忆档案馆”、审计仪表盘、语义搜索、冲突中心和最近事件可见；提交“馄饨”搜索后结果可见，点击搜索结果可切换到记忆历史并显示创建/确认事件，冲突中心“已处理”按钮可把开放冲突处理为已按用户处理；移动视口下搜索结果、冲突中心和时间线可见，检测到 0 个 StarPanel 重叠、0 个文本溢出且无横向滚动。临时 smoke persona 已通过 DELETE API 清理，浏览器临时 token 已清除并重置视口。
- 本次仍遵守仓库规则，不主动运行 `docs/init.sh`。

## Latest Session Update - 2026-07-04 yawen 星空前端交互迁移

- 根据用户计划，本次不直接合并 `yawen`，以当前工作区为基础迁移 `origin/yawen` 前端视觉和交互，并保持 `backend/` 逻辑不变。
- 前端已迁移星空首页、全局布局/样式、Dashboard、创建星星页、人物详情、资料上传、任务、记忆审计、档案、对话、声音和 3D 页面；删除登录/注册页面、数据设置页、模型设置页和独立 stories 页面入口。
- `frontend/src/lib/auth.ts` 保留 `startDemoSession()` 并新增/使用 `ensureDemoSession()`：无 token 时调用现有 `POST /api/auth/demo`，已有 token 静默复用；UI 不展示账号入口或登录态差异。
- 创建星星页保留当前后端必需的 `age`，payload 继续写入 `language=zh-CN`、默认说话风格、情绪边界和禁用表达；创建成功后调用现有 `uploadMaterials()` 上传已选照片/视频/声音/文字文件，上传失败时保留已创建 persona 并提示去资料上传页补传。
- yawen 未闭环的视频手势互动仍为前端体验；后续三类体验拆分后，遗憾对话室和心愿延续引导已作为独立前端页复用现有 messages endpoint，并通过 conversation kind/context_kind 隔离普通聊天、遗憾对话和心愿引导上下文；不新增后端遗憾记录模型、心愿模型或提醒策略。
- `docs/feature-list.json` 新增 `feat-041`，并将旧 MemorySpace 前端、独立 stories 前端、`/settings/data` 和 `/settings/providers` 前端页面切片标记为被星空前端替换；后端导出/删除、provider settings 和 stories API 仍保持既有状态。
- 应用路由层已移除旧 `DemoEntry`、`MemorySpace` 页面壳、登录/注册页面、设置页面和独立 stories 页面；`frontend/src/components/DemoEntry.tsx` 与 `frontend/src/components/MemorySpace.tsx` 已删除，`frontend/app/globals.css` 清理不再使用的 `memory-*` 样式块。
- 验证通过：`npm.cmd --prefix frontend run test` 退出码 0，50 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，构建路由只包含 `/`、`/dashboard`、`/personas/new`、`/personas/{id}`、uploads/jobs/memories/profile/chat/voice/avatar，不包含 login/register/settings/stories；`python -m json.tool docs/feature-list.json` 退出码 0。
- 浏览器烟测通过：临时 Playwright Chromium 打开 `http://localhost:3000/`，确认星空首页、创建入口和 StarPlanetScene canvas 非空；清空 token 后进入 `/personas/new`，提交年龄 72 和文本资料，前端自动获取 demo token、创建 persona、上传资料并跳转记忆审计页；后端读取确认 persona `age=72`、`language=zh-CN`、默认说话风格存在且资料数为 1；记忆审计页新增维度交互可用；对话页三种互动模式、记忆档案馆、遗憾对话室和心愿延续入口可见；烟测 persona 已通过正式 DELETE API 清理。
- 构建首次在 dev server 正在写入 `.next` 时遇到 stale page module 收集错误；停止当前 Next dev server、删除 `frontend/.next` 后重建通过。
- 本次不运行 `docs/init.sh`，因为当前仓库规则要求仅在用户明确要求完整基线时运行；后端测试未运行，后端未在本任务中编辑，收尾用 backend diff 守卫确认无新增后端改动。

## Latest Session Update - 2026-07-04 Init Harness User-Requested Only

- 根据用户最新指令，`docs/init.sh` 现在定义为“只有用户明确要求才需要跑”的完整基线验证入口；agent 不因收尾、发布/合并前、启动/验证链路变化、改动较大或需要完整基线证据而主动运行它。
- `AGENTS.md` 已同步：Commands、Editing Guidance 和 Validation Expectations 均改为“仅用户明确要求时运行 `docs/init.sh`”；修改 `docs/init.sh` 本身时也只做静态检查或文本审阅，除非用户明确要求完整自检。
- `docs/README.md` 已同步：文档地图、当前状态、统一 harness 和维护流程均明确 `docs/init.sh` 不主动运行，其他场景使用与改动直接相关的单项验证。
- `docs/平台说明.md` 和 `docs/prd-checklist.md` 已同步：`docs/init.sh` 不再作为普通验证命令组或默认 harness，自检表格改为“仅用户明确要求”。
- 本次不改后端、前端、Compose 或 `docs/init.sh` 脚本行为；遵守该规则，不运行 `docs/init.sh`。
- 已执行轻量验证：`python -m json.tool docs/feature-list.json` 退出码 0；针对旧策略关键词的 `rg` 检查在当前规则文档中无命中；`git diff --check -- AGENTS.md docs/README.md docs/progress.md docs/平台说明.md docs/prd-checklist.md` 退出码 0，仅有既有 LF/CRLF working-copy warning。

## Latest Session Update - 2026-07-04 Chat Think Block Cleanup

- 根据浏览器评论，聊天页不应向用户展示模型 `<think>` 推理过程；本次在后端聊天输出边界处理，而不是只做前端隐藏。
- `backend/app/services/chat.py` 在保存新的 persona 回复前剥离 `<think>...</think>` 推理块；如果模型只返回推理块导致清洗后为空，则回退到本地 deterministic draft reply。
- `message_response()` 返回 persona 消息时也剥离 `<think>` 推理块，覆盖已存历史消息、消息列表和复用该响应结构的对话导出；用户消息原文不做此类过滤。
- `run_chat_gateway()` 传入历史对话时也会对 persona 历史消息使用同一清洗逻辑，避免旧推理文本再次进入下一轮真实 LLM 上下文。
- 已执行 RED/GREEN：新增 `test_send_text_message_strips_model_thinking_from_real_llm_reply` 和 `test_list_messages_strips_model_thinking_from_existing_persona_message`，修复前 2 failed，修复后 2 passed；随后 `python -m pytest backend/tests/test_chat.py -q` 16 passed。
- 完整验证：`python -m json.tool docs/feature-list.json > $null` 退出码 0；`python -m pytest backend/tests/test_exports.py -q` 4 passed；`python -m pytest backend/tests -q` 181 passed；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，181 backend tests、50 frontend tests、frontend lint/build 和 `docker compose config` 均通过。
- 浏览器验收：`docker compose up --build -d backend` 退出码 0 后打开 `http://localhost:3000/personas/8163ecfa-0c65-47e3-a8ce-52116f5beb96/chat`，当前 4 条消息正文中 `hasThinkTag=false`、`hasPrivateReasoning=false`，原先泄漏的英文推理块不再显示。
- `git diff --check -- backend/app/services/chat.py backend/tests/test_chat.py docs/可信人格记忆Agent_mvp_prd.md docs/feature-list.json docs/prd-checklist.md docs/progress.md` 退出码 0，仅有既有 LF/CRLF working-copy warning。

## Latest Session Update - 2026-07-04 Init Harness Policy Cleanup

- 根据用户指令，删除本仓库“每次收尾默认运行 `docs/init.sh`”的要求；`docs/init.sh` 保留为完整基线验证入口，仅在用户明确要求时运行。
- `AGENTS.md` 的 Constraint Workflow、Commands、Editing Guidance 和 Validation Expectations 已改为按改动范围运行最小必要验证；文档/规则变更优先使用 JSON、脚本语法或 `rg` 等轻量检查。
- `docs/README.md` 的文档地图、Harness 分工、当前状态、统一 harness 和维护流程已同步：普通文档、局部后端或局部前端改动不再要求默认跑完整 harness。
- 本次属于 agent 规则与文档维护，不改后端、前端、Compose 或 `docs/init.sh` 脚本行为；按新规则不运行完整 `docs/init.sh`。
- 已执行轻量验证：`python -m json.tool docs/feature-list.json` 退出码 0；针对旧的强制 `docs/init.sh` 收尾规则运行 `rg` 检查无命中；`git diff --check -- AGENTS.md docs/README.md docs/progress.md` 退出码 0，仅有既有 LF/CRLF working-copy warning。

## Latest Session Update - 2026-07-04 Create Persona Defaults Cleanup

- 根据浏览器评论，`/personas/new` 不再展示“主要语言”输入框，也不再展示“说话风格与边界”区块；用户只填写类型、基础资料、关系和称呼。
- 前端 `PersonaDraft` 改为只包含用户可填写字段；创建 payload 固定写入 `language=zh-CN`，并写入系统默认 `speaking_style`、`emotional_style` 和 `forbidden_expressions`。
- 后端 `PersonaCreate` 省略 `language` 时默认 `zh-CN`，创建或更新传入非 `zh-CN` 语言值会返回 422；保留 response、数据库列和 prompt_context 读取链路。
- 已执行聚焦 RED/GREEN：`python -m pytest backend/tests/test_personas.py -q` 先失败于省略 language 不能创建和非中文未被拒绝，修复后 57 passed；`npm.cmd --prefix frontend run test -- persona.test.mjs` 先失败于隐藏字段仍被 required 和 payload builder 缺失，修复后 63 passed。
- 完整验证：`python -m json.tool docs/feature-list.json` 退出码 0；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，179 backend tests、63 frontend tests、frontend lint/build 和 `docker compose config` 均通过。
- 浏览器验收：`docker compose up --build -d frontend` 退出码 0 后刷新 `http://localhost:3000/personas/new`，DOM 检查确认无“主要语言”“说话风格与边界”“说话风格”“情绪方式”“禁止表达”，当前只剩 8 个用户输入控件；浏览器提交测试人物后数据库确认 `language=zh-CN` 且默认风格边界已写入，随后已软删除该测试人物并返回创建页。

## Latest Session Update - 2026-07-04 DashScope Recheck With Current Key

- 根据用户确认，当前 `.env/runtime.env` 已配置 DashScope key，且业务空间已具备当前模型调用资格；本次仅做脱敏配置检查，不在日志或文档中回显原始 key。
- 脱敏配置检查确认：`DEFAULT_LLM_PROVIDER=dashscope`，`DASHSCOPE_API_KEY` 已设置，region 为 `cn-beijing`，workspace 为 `ws-oyohscx3hl0sgsdz`，当前模型为 `QWEN_TEXT_MODEL=qwen-plus`、`QWEN_VISION_MODEL=qwen3.7-plus`、`QWEN_OCR_MODEL=qwen-vl-ocr-latest`、`QWEN_ASR_MODEL=qwen3-asr-flash`。
- 已强制重建并重启 backend：`docker compose up --build -d --force-recreate backend` 退出码 0；`http://localhost:8000/health` 返回 200。
- 复跑 `python backend/scripts/real_multimodal_smoke.py --sample-mode public --backend-url http://localhost:8000` 退出码 0；结果文件 `.smoke/real-multimodal/results/20260704-180621.json` 记录 provider report 中 DashScope configured，text、image、audio、video、pdf、docx、doc 七类样本均 `parse_status=succeeded`、job `status=succeeded`，provider 为 `dashscope`/`third_party`，生成 ParsedChunk 与 source-backed MemoryCard，`errors=[]`。
- 当前结论：此前 `403 AccessDenied.Unpurchased` 已解除；公网样本闭环不是代码阻断，当前 key、业务空间和模型资格可支撑真实 DashScope 多模态解析 smoke。

## Latest Session Update - 2026-07-04 MiniMax Text LLM Verification

- 按用户要求检查所有文本对话相关 LLM 调用：此前 `chat_llm` 和 `story_generation` 仍主要走 mock/local 路径；本轮将非 test 环境下的 `chat_llm` 与 `story_generation` 统一接到 env 中 MiniMax/OpenAI-compatible 配置，使用 MiniMax `/chat/completions` 和 `OPENAI_MODEL`，未配置或 `APP_ENV=test` 时保留 deterministic mock fallback。
- 更新 `backend/app/providers/minimax.py`、`backend/app/providers/gateway.py`、`backend/app/services/chat.py` 和 `backend/app/services/provider_settings.py`：MiniMax provider 增加 `chat_llm`/`story_generation`，Provider Gateway 路由文本 LLM 能力到 MiniMax，模型设置接口展示 MiniMax 文本能力，chat service 对真实 LLM 回复继续执行 persona 禁用表达过滤；story generation 支持模型返回严格 JSON，也支持普通文本回退为带来源记忆的故事内容。
- 真实调用检查不输出密钥：本地配置显示 MiniMax key 已配置、base URL 为 MiniMax OpenAI-compatible、chat model 为 `MiniMax-M3`。直接 provider smoke 中 `chat_llm` 和 `story_generation` 均返回 trace id；Docker backend 重建后 `/health` 返回 200；真实 API smoke 中文本对话 metadata 为 `provider=minimax`、`capability=chat_llm`，故事生成 metadata 为 `provider=minimax`、`capability=story_generation`，并返回 source memory ids 和 audio URL。
- 已执行检查：RED `python -m pytest backend/tests/test_minimax_provider.py backend/tests/test_provider_gateway.py -q` 先失败于 MiniMax 未支持文本能力，RED `python -m pytest backend/tests/test_chat.py::test_send_text_message_sanitizes_real_llm_reply -q` 先失败于真实 LLM 回复未过滤禁用表达，RED `python -m pytest backend/tests/test_minimax_provider.py::test_minimax_story_generation_falls_back_when_model_returns_plain_text -q` 先失败于真实模型返回非 JSON；修复后 `python -m pytest backend/tests/test_minimax_provider.py backend/tests/test_provider_gateway.py backend/tests/test_chat.py backend/tests/test_stories.py backend/tests/test_provider_settings.py backend/tests/test_config.py -q` 40 passed；直连 MiniMax smoke 使用 env 中 `MiniMax-M3`，`chat_llm` 与 `story_generation` 均返回 trace id；真实 API smoke 返回 chat `provider=minimax`/`capability=chat_llm`、story `provider=minimax`/`capability=story_generation`；`python -m json.tool docs/feature-list.json > $null` 退出码 0；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，required files、JSON validation、177 backend tests、62 frontend tests、frontend lint、frontend build 和 `docker compose config` 均通过；`git diff --check -- ...` 退出码 0，仅 LF-to-CRLF working-copy warnings。

## Latest Session Update - 2026-07-04 DashScope 403 Documentation Cleanup

- 核对本地真实多模态 smoke 结果：`.smoke/real-multimodal/results/20260704-160242.json` 中 image/audio/video/pdf/docx 曾被 DashScope `403 AccessDenied.Unpurchased` 阻断；最新 `.smoke/real-multimodal/results/20260704-170719.json` 中 text、image、audio、video、pdf、docx、doc 七类样本均 `parse_status=succeeded`、job `status=succeeded`，provider 为 `dashscope`/`third_party`，`errors=[]`。
- 修正文档陈旧结论：`docs/平台说明.md` 不再声明最近一次完整烟测仍被 403 阻断，改为记录 2026-07-04 完整 smoke 已通过，并保留遇到 `AccessDenied.Unpurchased` 时需开通百炼服务、确认实名认证、业务空间/API Key/region 匹配和模型权限后重启 backend 复跑；`docs/prd-checklist.md` 不再把 DashScope 公网样本 smoke 阻断项列为待补齐。
- 本次不改后端 adapter 或 smoke 脚本；根因属于 DashScope 账号/模型调用资格，而不是仓库解析代码缺口。
- 已执行检查：`python -m json.tool docs/feature-list.json` 退出码 0；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 首次 120 秒超时，随后以更长超时复跑退出码 0，required files、JSON validation、176 backend tests、62 frontend tests、frontend lint、frontend build 和 `docker compose config` 均通过。

## Latest Session Update - 2026-07-04 Real Multimodal Smoke Verification Follow-up

- 根据用户反馈 DashScope 权限已解决，强制重建/重启 backend 以重新加载 `.env/runtime.env`，`http://localhost:8000/health` 返回 200。
- 复跑 `python backend/scripts/real_multimodal_smoke.py --sample-mode public --backend-url http://localhost:8000` 退出码 0；结果文件 `.smoke/real-multimodal/results/20260704-170719.json` 记录 text/image/audio/video/pdf/docx/doc 七类样本均 `parse_status=succeeded`、job `status=succeeded`，provider 为 `dashscope`/`third_party`，生成 ParsedChunk 与 source-backed MemoryCard，`errors=[]`。
- `docs/feature-list.json` 中 `feat-039` 从 `blocked` 调整为 `completed`；`docs/prd-checklist.md` 的 M3-AC-008 和 `docs/README.md` 残余风险同步更新为真实完整 smoke 已通过。P1/P2 暂缓边界不变。
- 已执行检查：`docker compose up --build -d --force-recreate backend` 退出码 0；`http://localhost:8000/health` 返回 200；`python backend/scripts/real_multimodal_smoke.py --sample-mode public --backend-url http://localhost:8000` 退出码 0；`python -m json.tool docs/feature-list.json > $null` 退出码 0，当前状态为 38 completed / 1 deferred；`python -m pytest backend/tests/test_dashscope_provider.py backend/tests/test_material_extractors.py backend/tests/test_real_multimodal_smoke.py -q` 12 passed；`docker compose config > $null` 退出码 0；`git diff --check -- docs/feature-list.json docs/prd-checklist.md docs/README.md docs/progress.md` 退出码 0，仅 LF-to-CRLF working-copy warnings。
- 完整统一验证已复跑：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，required files、JSON validation、172 backend tests、62 frontend tests、frontend lint、frontend build 和 `docker compose config` 均通过。

## Previous Session Update - 2026-07-04 Pause P1/P2 Feature Development

- 根据用户最新指令，暂时不再开发 P1/P2 功能点；已完成的 Milestone 0-8、provider settings、本地 embedding、真实多模态烟测脚本和 P1 age 必填基础闭环全部保留。
- 撤回本轮刚开始但未完成的 P1 自定义人格档案维度切片残留：未保留 `custom_dimensions` schema/model/API/page/test 变更，避免留下半成品或失败测试。
- `docs/feature-list.json` 中 `feat-036` 从 `planned` 调整为 `deferred`，表示自定义人格档案维度、AI 主动关怀、心愿延续及其他 P1/P2 功能点暂缓；`feat-038` age 必填功能仍保持 `completed`。
- 本次轻量检查：`rg -n "custom_dimensions|custom_profile_dimensions|format_custom_profile_dimensions|纪念日陪伴方式" backend frontend` 无命中（退出码 1，表示未找到）；`npm.cmd --prefix frontend run test -- profile.test.mjs` 62 passed；`npm.cmd --prefix frontend run build` 退出码 0。

## Previous Session Update - 2026-07-04 Local GPU bge-m3 Embedding Verification

- 完成本地 GPU bge-m3 embedding 接入收口：主 FastAPI 后端继续不直接加载 torch/FlagEmbedding，只通过 `LOCAL_GPU_WORKER_URL` 调用 `backend/app/local_embedding_worker.py`；worker 不可用、未配置、请求失败或维度不匹配时，聊天检索回退 deterministic lexical retrieval。
- 记忆写入链路已覆盖解析生成记忆、手动创建记忆、title/content 编辑和 `correct-memory` 纠错刷新 embedding；status-only 变更不刷新 embedding。`memory_cards` 新增 embedding JSON、provider/model/hash/updated_at 元数据和 Alembic 迁移。
- Provider settings 后端 allowlist、状态报告和前端 `/settings/providers` 已展示/保存 `local_gpu` embedding 配置；本地 ignored `.env/runtime.env` 已追加非密钥 embedding 运行变量，未把真实密钥写入 tracked 文件。
- 为当前全量后端测试补回缺失的 `backend/scripts/real_multimodal_smoke.py` 最小脚本入口，使既有 smoke 测试可收集并通过；该脚本不接入主服务路径。
- 保持范围边界：本轮不把 `chat_llm`/`story_generation` 切到 MiniMax，不实现 sparse/multi-vector、pgvector ANN index、真实 3D provider 或生产级 secret manager；真实 GPU worker 质量仍需在本机 CUDA 环境安装 `backend/requirements-embedding.txt` 后单独验收。
- 已执行检查：RED `python -m pytest backend/tests/test_config.py backend/tests/test_provider_settings.py backend/tests/test_local_embedding_provider.py backend/tests/test_chat.py backend/tests/test_parsing.py backend/tests/test_memories.py -q` 失败于缺少 `app.providers.local_embedding`；实现后同命令 34 passed；`python -m pytest backend/tests/test_real_multimodal_smoke.py -q` 6 passed；`DEFAULT_LLM_PROVIDER=mock python -m pytest backend/tests -q` 172 passed in 674.17s；`npm.cmd --prefix frontend run test` 62 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`docker compose config` 退出码 0；`python -m json.tool docs/feature-list.json` 退出码 0；`git diff --check` 退出码 0（仅 LF-to-CRLF working-copy warnings）；`DEFAULT_LLM_PROVIDER=mock & "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，required files、JSON、172 backend tests、62 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 Real Multimodal Public-Sample Smoke

- 修正 DashScope adapter 真实请求形态：Qwen3-ASR 改为单一 `input_audio` content item + `asr_options`；视频整段 fallback 改为 `video_url`；关键帧列表提高到 `fps=0.5` 且少于 4 帧时回退整段视频，避免 DashScope sequence image 最小帧数错误。
- 新增 `backend/scripts/real_multimodal_smoke.py`：下载 Project Gutenberg 文本、Wikimedia Commons 图片、LibriVox/Internet Archive 公版音频和 Wikimedia/USGS 视频；从文本派生 PDF/DOCX/DOC；通过 host ffmpeg 或 backend Docker 镜像裁剪视频；经真实上传 API 校验 provider、parse job、ParsedChunk id 和 source-backed MemoryCard；输出 `.smoke/real-multimodal/results/*.json` 并脱敏 provider secret 状态。
- 明确当前 PRD 边界：PDF/DOC/DOCX 只做本地文本抽取，不做扫描 PDF OCR；音频本阶段只覆盖 ASR 和基础 `sample_metadata`，不做 VAD、说话人分离或关键片段质量筛选；视频本阶段只覆盖音频提取、ASR、关键帧采样、视觉摘要和基础时间戳，不做稳定场景切分。
- 真实烟测记录：`docker compose up --build -d backend` 后运行 `python backend/scripts/real_multimodal_smoke.py --sample-mode public --backend-url http://localhost:8000`。最近结果写入 `.smoke/real-multimodal/results/20260704-160242.json`：text 与 DOC 成功通过 DashScope；前一次结果 `.smoke/real-multimodal/results/20260704-155929.json` 中 audio ASR 成功通过 DashScope；完整 smoke 仍被 DashScope `403 AccessDenied.Unpurchased` 阻断，错误体为 `Access to model denied. Please make sure you are eligible for using the model.`，需要开通或替换当前 OCR/VL/ASR/文本模型后复跑。
- 已执行检查：`python -m pytest backend/tests/test_dashscope_provider.py backend/tests/test_material_extractors.py backend/tests/test_real_multimodal_smoke.py -q`，12 passed；`docker compose up --build -d backend` 成功；`http://localhost:8000/health` 返回 200。

## Previous Session Update - 2026-07-04 Persona Age Required Field

- 新增 `Persona.age` 基础闭环：后端模型、Pydantic create/update/read schema、Persona API 响应、demo seed、profile export snapshot 和 Alembic 迁移 `0005_persona_age.py` 支持用户填写的年龄/享年；迁移列保持 nullable 以兼容既有数据，新建/更新 schema 要求 1..150。
- 前端 `/personas/new` 新增年龄/享年输入，`validatePersonaDraft` 将 age 纳入必填和范围校验，创建 payload 转为整数；人物详情页展示年龄/享年。
- profile/profile export 的 `basic_facts` 在用户未手动覆盖该维度时注入 `source=persona_card` 的 age fact，使 PRD 基础事实维度可以读取创建人物资料卡片中的年龄；用户手动编辑 `basic_facts` 后不再自动覆盖。
- 保持范围边界：本次不实现头像文件上传、出生年份替代表单、自定义人格档案维度、AI 主动关怀、心愿延续或新的模型链路。
- 已执行检查：RED `python -m pytest backend/tests/test_personas.py backend/tests/test_models.py -q` 失败于后端接受缺失/null/越界 age、响应缺少 age 和 schema 缺少列；RED `npm.cmd --prefix frontend run test -- persona.test.mjs` 失败于 missingFields 未包含 age；实现后 `python -m pytest backend/tests/test_personas.py backend/tests/test_models.py backend/tests/test_auth.py -q` 63 passed，`npm.cmd --prefix frontend run test -- persona.test.mjs` 62 passed；随后 RED `python -m pytest backend/tests/test_profile.py::test_profile_basic_facts_include_user_filled_age_from_persona_card backend/tests/test_exports.py::test_export_profile_returns_watermarked_profile_snapshot -q` 失败于 profile basic_facts 缺少 age，修复后 `python -m pytest backend/tests/test_profile.py backend/tests/test_exports.py -q` 13 passed。

## Previous Session Update - 2026-07-04 Local GPU bge-m3 Embedding

- 新增本机 GPU embedding worker：`backend/app/local_embedding_worker.py` 提供 `GET /health` 和 `POST /embeddings`，默认模型 `BAAI/bge-m3`、1024 维 dense embedding；`backend/requirements-embedding.txt` 单独放置 FlagEmbedding/torch 重依赖，主 FastAPI 后端不直接加载 torch。
- 后端配置新增 `EMBEDDING_PROVIDER`、`LOCAL_EMBEDDING_MODEL`、`LOCAL_EMBEDDING_DIMENSIONS`、`LOCAL_EMBEDDING_BATCH_SIZE` 和 `LOCAL_GPU_WORKER_URL`；`GET/PUT /api/settings/providers` 与前端 `/settings/providers` 已展示/保存 local_gpu embedding 配置，响应不涉及新密钥。
- `memory_cards` 新增 embedding JSON、model/provider/text hash/updated_at 元数据和 Alembic 迁移；解析生成记忆、手动创建记忆、title/content 编辑、chat correct-memory 会尝试写入或刷新 embedding，status-only 变更不会重写。
- `retrieve_memories()` 优先使用本地 bge-m3 cosine 向量召回，候选规则为 cosine >= 0.35 或词法 overlap > 0；存在 confirmed/corrected 候选时仍只在事实记忆中排序；worker 未配置、不可用、请求失败或维度不匹配时回退原 deterministic lexical retrieval。
- 保持范围边界：本轮不把 `chat_llm`/`story_generation` 切到 MiniMax，不实现 sparse/multi-vector、pgvector ANN index、真实 3D provider 或生产级 secret manager；真实 GPU worker 质量需在本机 CUDA 环境安装 embedding requirements 后单独验收。
- 已执行检查：先跑 RED `python -m pytest backend/tests/test_config.py backend/tests/test_provider_settings.py backend/tests/test_local_embedding_provider.py backend/tests/test_chat.py backend/tests/test_parsing.py backend/tests/test_memories.py -q` 失败于缺少 `app.providers.local_embedding`；实现后同命令 GREEN，34 passed。

## Previous Session Update - 2026-07-04 Data Settings Browser Smoke

- 以服务级 Docker Compose 拓扑重建并启动当前本地代码，确认 backend healthy、frontend started。
- 使用临时账号和临时人物通过后端 API 预置资料、已确认记忆、对话和引用，再在真实 Chrome/Playwright 页面打开 `/settings/data`。
- 浏览器 smoke 覆盖：点击「导出档案」「导出记忆」「导出对话」并验证下载 JSON 的 `export_type`、文件名和 AI 模拟水印；点击「删除对话」「删除资料」「删除人物」后分别验证导出/详情/人物接口返回 404；另用第二个临时账号点击「清空当前账号数据」，验证 `/api/auth/me` 仍可用且 `/api/personas` 返回空列表。
- 调试记录：首次 browser launch 失败是 Playwright 自带 Chromium 未安装；改用系统 Chrome channel 后继续。第二个账号分支初次未显示新人物，根因为同一 Playwright context 的 `addInitScript` 在导航时把 localStorage 重设为第一个 token；改用新的 browser context 后通过。
- 保持范围边界：本次不新增产品能力，不实现真实 MinIO/S3 bucket object 删除、向量索引清理、审计回放、复杂合规审核或生产级 secret manager。
- 已执行检查：`docker compose up --build -d` 在延长等待后完成并替换 backend/frontend/worker 容器；`/settings/data` service-backed browser smoke 通过，导出下载 3 个 JSON 均含水印，删除对话/资料/人物后对应 API 均返回 404，清空账号后 token 仍可访问 `/api/auth/me` 且人物列表为空；`python -m json.tool docs/feature-list.json` 退出码 0；`git diff --check` 退出码 0（仅 LF-to-CRLF working-copy warnings）；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，required files、JSON、155 backend tests、61 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 P1 PRD Scope Alignment

- PRD 创建人物模块已明确「资料卡片」指人物基础资料卡片，不等同于后续上传的 SourceMaterial 或系统抽取的记忆卡片。
- PRD `7.2.2` 必填字段表新增 `age`，类型为 `integer`，说明为用户填写的年龄/享年，不由系统推断。
- PRD 人格档案模块新增自定义维度，要求用户可新增、编辑、删除自定义档案维度，且自定义维度优先视为用户手动补充内容。
- PRD 新增 P1 `7.13 AI 主动关怀模块` 和 `7.14 心愿延续系统`，并在页面清单与 V1.1 规划中补充入口；两项均明确不属于当前已完成 Milestone 0-8。
- `docs/feature-list.json` 新增 `feat-036`，状态为 `planned`；`docs/prd-checklist.md` 新增 P1 planned 对照项并记录后端、前端、数据库、API、任务调度和模型链路均未实现；`docs/README.md` 只在残余风险中补充 P1 未实现说明。
- 已执行检查：`python -m json.tool docs/feature-list.json` 退出码 0；`rg "主动关怀|心愿延续|资料卡片|自定义维度|\\| age \\|" docs` 命中 PRD、feature-list、prd-checklist 和 README，且 P1 模块在 checklist/README 中标为 planned 或未实现；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，required files、JSON、146 backend tests、61 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 Local Material File Cleanup

- 新增 `backend/app/services/material_storage.py`，只清理受管本地 `storage/materials/...` 路径，忽略 URL 或越界路径，避免误删非资料文件。
- `DELETE /api/materials/{id}` 在资料软删除提交后删除对应本地上传文件；人物删除和清空当前账号数据通过 `backend/app/services/data_management.py` 返回被软删除资料的 `storage_url`，路由在数据库提交后统一清理本地文件。
- 新增/扩展后端测试覆盖：直接删除上传资料会删除本地文件；删除人物会删除其本地资料文件；清空当前账号数据会删除当前账号文件但保留其他用户文件。
- 保持范围边界：本次不实现真实 MinIO/S3 bucket object 删除、向量索引清理、审计回放、复杂合规审核、后台重试清理任务或真实模型质量。
- 已执行检查：`python -m pytest backend/tests/test_materials.py::test_delete_uploaded_material_removes_local_storage_file backend/tests/test_personas.py::test_delete_persona_soft_deletes_prd_related_records backend/tests/test_settings_data.py::test_clear_current_account_data_soft_deletes_owned_domain_records -q` RED 后 GREEN，最终 3 passed；`python -m pytest backend/tests/test_materials.py backend/tests/test_personas.py backend/tests/test_settings_data.py backend/tests/test_jobs.py backend/tests/test_parsing.py backend/tests/test_exports.py backend/tests/test_chat.py backend/tests/test_voice.py backend/tests/test_avatar.py backend/tests/test_stories.py -q` 102 passed。

## Previous Session Update - 2026-07-04 Provider Settings Frontend Page

- 新增 `/settings/providers` 页面，登录后读取 `GET /api/settings/providers`，展示 mock、DashScope/Qwen、MiniMax、OpenAI-compatible、Tripo 和本地 GPU worker 的 configured/missing 状态、capabilities、非 secret 设置和 runtime env 存在状态。
- 新增 `frontend/src/lib/provider-settings.ts`，封装模型设置路由、API path、表单字段、payload 构造、状态摘要、secret 状态文案、provider settings GET/PUT 调用。
- 全局登录态导航新增「模型设置」入口；路由/API path 测试覆盖 `/settings/providers` 和 `/api/settings/providers`。
- 表单只提交非空字段；密钥输入默认空，留空不会覆盖已保存密钥，避免误删本地 `.env/runtime.env` 中的 key；页面和 helper 不展示后端原始 API key。
- 保持范围边界：本次不实现生产级 secret manager、在线密钥分发、真实 provider 质量验收、公开模型市场或复杂权限审批。
- 已执行检查：`npm.cmd --prefix frontend run test -- provider-settings.test.mjs routes.test.mjs memory-space.test.mjs` RED 后 GREEN，最终 61 passed；`npm.cmd --prefix frontend run test` 61 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，Next.js build 包含 `/settings/providers`；`python -m json.tool docs/feature-list.json` 退出码 0；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，required files、JSON、145 backend tests、61 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 Provider Settings Backend API

- 新增 `GET /api/settings/providers`，当前 JWT 用户可读取 mock、DashScope/Qwen、MiniMax、OpenAI-compatible、Tripo 和本地 GPU worker 的 configured/missing 状态、capabilities 与非 secret 配置字段。
- 新增 `PUT /api/settings/providers`，只允许写入 allowlist 运行变量到本地 ignored `.env/runtime.env`；写入后清理 settings cache，使后续 provider gateway 读取最新配置。
- 响应永不返回原始 API key，只返回 `configured`/`missing` 状态；未知运行变量返回 400 且不会创建 runtime env 文件。
- 保持范围边界：本次不实现前端 `/settings/providers` 页面、生产级 secret manager、真实 provider 质量验收、在线密钥分发或公开模型市场。
- 已执行检查：`python -m pytest backend/tests/test_provider_settings.py -q` RED 后 GREEN 3 passed；`python -m pytest backend/tests/test_provider_settings.py backend/tests/test_config.py backend/tests/test_provider_gateway.py backend/tests/test_minimax_provider.py -q` 15 passed；`python -m pytest backend/tests -q` 145 passed；`python -m json.tool docs/feature-list.json` 退出码 0；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，required files、JSON、145 backend tests、57 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 MiniMax Voice Provider

- 新增 `backend/app/providers/minimax.py`，通过 MiniMax HTTP API 支持 `tts` 和 `voice_clone`：TTS 调用 `/v1/t2a_v2` 返回 URL；音色复刻先上传本地音频样本到 `/v1/files/upload`，再调用 `/v1/voice_clone` 返回 `minimax://voice/{voice_id}` 和预览音频。
- 扩展 `backend/app/core/config.py`：支持 `MINIMAX_API_KEY`/`MINIMAX_BASE_URL`，并在 `OPENAI_BASE_URL=https://api.minimaxi.com/v1` 时复用 MiniMax OpenAI 兼容 key；本地 `.env/runtime.env` 只追加非密钥 MiniMax 模型和默认音色配置，真实 key 仍留在 ignored runtime env。
- 扩展 `backend/app/providers/gateway.py` 和 `backend/app/services/voice.py`：非 test env 且 MiniMax 已配置时，`tts`/`voice_clone` 走 `third_party/minimax`；未配置或 `APP_ENV=test` 时继续 deterministic mock fallback；voice jobs 和 voice models 记录真实 provider metadata。
- 新增/扩展测试覆盖配置别名读取、MiniMax HTTP 请求形状、gateway 真实/测试环境路由、语音合成和音色复刻 provider metadata。
- 真实冒烟：使用 LibriVox Short Poetry Collection 277 的 Public Domain 短诗 MP3（约 69 秒，551,193 bytes）做音色复刻样本；MiniMax 默认 TTS 返回 HTTP audio URL 和 trace id；MiniMax `voice_clone` 返回临时 `minimax://voice/...` artifact 与 preview URL；再用该复刻音色调用 TTS 也返回 HTTP audio URL 和 trace id。
- 已执行检查：`python -m pytest backend/tests/test_config.py backend/tests/test_provider_gateway.py backend/tests/test_minimax_provider.py backend/tests/test_voice.py -q` 22 passed；`python -m json.tool docs/feature-list.json` 退出码 0；`DEFAULT_LLM_PROVIDER=mock` 下 `python -m pytest backend/tests -q` 142 passed；`docker compose config` 退出码 0；`DEFAULT_LLM_PROVIDER=mock` 下 `& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，required files、JSON、142 backend tests、57 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 Milestone 8 Task 11 Frontend Data Settings

- 新增 `/settings/data` 页面，登录后集中读取当前账号的人物、资料和对话，并提供档案 JSON、记忆 JSON、对话 JSON 导出入口。
- 新增 `frontend/src/lib/data-settings.ts`，封装数据设置路由、导出下载构造、数量摘要、删除人物、删除资料、删除对话和清空当前账号数据调用；导出文件保留后端返回的文件名与 AI 模拟水印。
- 全局登录态导航新增「数据设置」入口；路由/API path 测试覆盖 `/settings/data`、profile/memories/conversation export、`DELETE /api/conversations/{id}` 和 `DELETE /api/settings/data`。
- 页面支持删除人物、资料、单条对话和清空当前账号人物域数据，并明确当前为软删除、账号本身仍可继续使用；单条记忆删除仍通过既有 `/personas/{id}/memories` 审计页完成。
- 保持范围边界：本次不实现对象存储物理清理、向量索引清理、审计回放、版本查看、复杂合规审核或真实模型质量。
- 已执行检查：`npm.cmd --prefix frontend run test -- data-settings.test.mjs routes.test.mjs memory-space.test.mjs` RED 后 GREEN，最终 57 passed；`npm.cmd --prefix frontend run test` 57 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，Next.js build 包含 `/settings/data`；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，当前 Real Multimodal Parsing Provider banner、required files、JSON、142 backend tests、57 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 Milestone 8 Task 10 Backend Clear Account Data

- 新增 `DELETE /api/settings/data`，按当前 JWT 用户隔离清空当前账号域数据，但不删除用户账号本身，当前 token 仍可读取 `/api/auth/me`。
- 抽取 `backend/app/services/data_management.py`，让删除人物和清空账号复用同一 PRD 软删除规则；清空账号会软删除该用户所有人物及其资料、解析块、记忆、档案、对话、消息、引用、声音模型、3D 模型、AI Job 和回忆故事。
- 同步修复验证时暴露的 provider 边界：DashScope 记忆抽取返回非 PRD 分类时归一到 PRD enum 或 `unknown`；voice-message ASR payload 补充 `storage_url`；后端单元测试强制 `DEFAULT_LLM_PROVIDER=mock`，避免受本地 `.env/runtime.env` 真实 provider 波动影响。
- 保持范围边界：本次不实现前端 `/settings/data` 页面、对象存储物理清理、向量索引清理、审计回放、版本查看或复杂合规审核。
- 已执行检查：`python -m pytest backend/tests/test_settings_data.py -q` RED 后 GREEN 1 passed；`python -m pytest backend/tests/test_provider_gateway.py::test_dashscope_memory_candidates_normalize_to_prd_categories -q` RED 后 GREEN 1 passed；`python -m pytest backend/tests/test_chat.py backend/tests/test_exports.py -q` 修复 provider 边界后 14 passed；`python -m pytest backend/tests/test_settings_data.py backend/tests/test_personas.py backend/tests/test_jobs.py backend/tests/test_materials.py backend/tests/test_provider_gateway.py backend/tests/test_parsing.py -q` 69 passed；`python -m pytest backend/tests -q` 135 passed；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，当前 Real Multimodal Parsing Provider banner、required files、JSON、135 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 DashScope Runtime Configuration

- 本地未提交 `.env/runtime.env` 已配置 `DEFAULT_LLM_PROVIDER=dashscope`、华北2（北京）业务空间 ID、DashScope compatible base URL 和 Qwen 多模态解析模型；真实密钥仍保留在 ignored runtime env 中，不写入 tracked docs。
- `docker-compose.yml` 新增可选 `./.env/runtime.env` `env_file`，backend 与 worker 服务在该文件存在时自动加载 provider 配置；同时移除 Compose 中会强制覆盖 runtime env 的 mock/blank provider 变量。
- 保持范围边界：本次只启用已有 DashScope 多模态解析路径，覆盖 `text_parser`、`ocr`、`image_understanding`、`asr`、`video_understanding` 和 `memory_extraction`；Chat/Story LLM、TTS、音色克隆、真实 3D 和 embedding 检索仍未接真实 provider。
- 已执行检查：脱敏配置读取确认 provider=`dashscope`、key 已配置、workspace=`ws-oyohscx3hl0sgsdz`、vision model=`qwen3.7-plus` 和 compatible base URL 正确；`docker compose config` 退出码 0；`python -m pytest backend/tests/test_config.py backend/tests/test_provider_gateway.py -q` 6 passed；`DEFAULT_LLM_PROVIDER=mock` 下运行 `& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，134 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过，避免测试期间发起付费真实 provider 调用。
- 下一步如需验证真实调用：用一张图片或短视频上传触发 parse job，确认 job provider 为 `dashscope`，并检查生成的 `ParsedChunk` 与待审核 `MemoryCard`。

## Previous Session Update - 2026-07-04 Milestone 8 Task 9 Backend Conversation Delete

- 新增 `DELETE /api/conversations/{id}`，复用当前用户 conversation 隔离，软删除单条对话。
- `backend/app/services/chat.py` 新增 conversation tombstone helper，同步软删除该 conversation 下的 messages 与 message citations；引用列表过滤已删除 citation。
- `backend/app/services/data_exports.py` 导出 conversation 时只读取未删除 messages；删除后 conversation export 通过现有 `get_conversation_or_404` 返回 404。
- 新增后端测试覆盖：删除后 conversation 不再出现在人物会话列表；messages/export/citations 均不再可读；conversation、user/persona messages 和 citation 均写入 `deleted_at`。
- 保持范围边界：本次不实现前端 `/settings/data` 页面、清空当前账号数据、对象存储物理清理、向量索引清理、审计回放或复杂合规审核。
- 已执行检查：`python -m pytest backend/tests/test_chat.py::test_delete_conversation_soft_deletes_messages_and_citations -q` RED 后 GREEN 1 passed；`python -m pytest backend/tests/test_chat.py backend/tests/test_exports.py -q` 14 passed；`python -m pytest backend/tests -q` 133 passed；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，当前 Real Multimodal Parsing Provider banner、required files、JSON、133 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 Milestone 8 Task 8 Backend Persona Delete Cascade

- 新增 `backend/alembic/versions/0003_soft_delete_related_records.py`，为 parsed chunks、persona profiles、messages、message citations、voice models、avatar models 和 AI jobs 补齐 `deleted_at` tombstone。
- 扩展 `DELETE /api/personas/{id}`：删除当前用户当前人物时同步软删除 source materials、parsed chunks、memory cards、persona profile、conversations、messages、message citations、voice models、avatar models、AI jobs 和 memory stories。
- 更新任务读取边界：`/api/jobs/{id}` 和相关任务列表只返回未删除 AI Job，避免人物删除后仍可按 job id 读取已删除任务。
- 新增后端级联删除测试，覆盖 PRD 7.12.2 关联记录 tombstone、跨当前用户隔离入口和删除后任务详情 404。
- 保持范围边界：本次不实现前端 `/settings/data` 页面、单条对话删除、清空当前账号数据、对象存储物理清理、向量索引清理、审计回放或复杂合规审核。
- 已执行检查：`python -m pytest backend/tests/test_personas.py::test_delete_persona_soft_deletes_prd_related_records -q` RED 后 GREEN 1 passed；`python -m pytest backend/tests/test_personas.py backend/tests/test_materials.py backend/tests/test_memories.py backend/tests/test_chat.py backend/tests/test_jobs.py backend/tests/test_voice.py backend/tests/test_avatar.py backend/tests/test_stories.py backend/tests/test_exports.py -q` 99 passed；`python -m pytest backend/tests -q` 132 passed；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，当前 Real Multimodal Parsing Provider banner、required files、JSON、132 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 Milestone 8 Task 7 Backend Data Export

- 新增 `backend/app/api/routes/data_exports.py`、`backend/app/services/data_exports.py` 和 `backend/app/schemas/data_export.py`，并在 `backend/app/main.py` 注册 exports router。
- 新增 `GET /api/personas/{id}/export/profile`，返回当前用户当前人物的 persona/profile/trust JSON snapshot、确定性文件名和「AI 模拟」水印说明。
- 新增 `GET /api/personas/{id}/export/memories`，返回当前人物未删除 memory cards，保留来源字段和「AI 模拟」水印说明。
- 新增 `GET /api/conversations/{id}/export`，返回当前用户对话、按时间排序的 messages 和 citations，跨用户访问返回 404。
- 保持范围边界：本次不实现前端 `/settings/data` 页面、删除关键数据、真实模型质量或复杂合规审核。
- 已执行检查：`python -m pytest backend/tests/test_exports.py -q` RED 后 GREEN 4 passed；`python -m pytest backend/tests/test_exports.py backend/tests/test_profile.py backend/tests/test_memories.py backend/tests/test_chat.py -q` 26 passed；`python -m pytest backend/tests -q` 131 passed；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，当前 Real Multimodal Parsing Provider banner、required files、JSON、131 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 Milestone 8 Task 6 Frontend Story Audio Download

- `frontend/src/lib/api.ts` 新增 `API_PATHS.stories.exportAudio(personaId, storyId)`，对齐后端 `GET /api/personas/{id}/export/story/{story_id}/audio`。
- `frontend/src/lib/stories.ts` 新增 `StoryAudioFileDownload`、`storyAudioFileExportAvailable`、`buildStoryAudioFileDownload` 和 `downloadStoryAudioFile`，下载后端 mock WAV blob 并保留 AI simulation / 非 TA 真实声音提示。
- `/personas/{id}/stories` 故事卡片将音频操作从打开 mock `audio_url` 改为「导出音频」，下载 `story-{story_id}.wav`，成功提示包含 mock/非真实声音说明和文件名。
- 保持范围边界：本次不实现真实 TTS/音色质量、删除关键数据、审计回放或完整 Demo flow。
- 已执行检查：`npm.cmd --prefix frontend run test -- stories.test.mjs routes.test.mjs` RED 后 GREEN 53 passed；`npm.cmd --prefix frontend run test` 53 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 首次暴露 `downloadBlobFile` 内未定义 `blob`，修复为 `download.blob` 后又遇到 stale `.next` 缺失 `.nft.json` 生成物，删除生成目录并重建后退出码 0，`/personas/[id]/stories` 构建通过；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，当前 Real Multimodal Parsing Provider banner、required files、JSON、127 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 Milestone 8 Task 5 Backend Story Audio Export

- 新增 `GET /api/personas/{id}/export/story/{story_id}/audio`，复用当前用户和人物隔离，返回 `audio/wav` attachment。
- `backend/app/services/stories.py` 新增 deterministic mock WAV 生成：文件名为 `story-{story_id}.wav`，WAV INFO metadata 和 `X-AI-Simulation-Notice` 响应头均标注这是 AI simulation mock TTS audio、不是 TA 的真实声音。
- 保持范围边界：本次不实现前端直接下载按钮、真实 TTS/音色质量、真实 Story LLM、删除关键数据或完整 Demo flow。
- 同步修复全量后端测试暴露的 Provider Gateway 回归：注入 fake DashScope client 时不再要求 provider metadata 属性；`run_parse_job` 使用 gateway 返回的 `provider_type`，避免第三方 provider job 被硬记为 `mock`。
- 已执行检查：`python -m pytest backend/tests/test_stories.py -q` RED 后 GREEN 6 passed；`python -m pytest backend/tests/test_provider_gateway.py backend/tests/test_parsing.py::test_parse_job_records_third_party_provider_from_gateway -q` 回归修复后 4 passed；`python -m pytest backend/tests -q` 127 passed；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，当前 Real Multimodal Parsing Provider banner、required files、JSON、127 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 Real Multimodal Parsing Provider

- 扩展 `backend/app/core/config.py` 和 `docker-compose.yml`，新增 DashScope/Qwen、Tripo、CosyVoice 相关环境变量；默认仍为 `DEFAULT_LLM_PROVIDER=mock`，未配置 `DASHSCOPE_API_KEY` 时不会调用第三方。
- 新增 `backend/app/providers/dashscope.py`，通过统一 `ProviderGateway` 支持 `text_parser`、`ocr`、`image_understanding`、`asr`、`video_understanding` 和 `memory_extraction` 的 DashScope/Qwen 调用；`chat_llm`、`story_generation`、`tts`、`extract_voice_sample`、`voice_clone` 和 `avatar_3d` 暂不接真实 provider。
- 新增 `backend/app/services/material_extractors.py`：PDF 使用 `pypdf`，DOCX 读取 `word/document.xml`，DOC 优先 `antiword`/LibreOffice，失败时记录 best-effort metadata；后端容器安装 `ffmpeg` 和 `antiword`。
- `backend/app/services/parsing.py` 现在向 provider payload 传入 `storage_url`/`mime_type`，将本地文本抽取 metadata 写入 `ParsedChunk.metadata`，并把 parse job、memory evidence 的 `provider_type`/`provider_name` 记录清楚；配置真实 provider 后第三方请求失败会沿用现有 failed job 路径。
- 新增/扩展测试覆盖 DashScope/Tripo 配置读取、mock fallback、DashScope gateway 路由、第三方 provider job 记录和 DOCX 文本抽取。
- 保持范围边界：本次不实现真实 TTS、真实音色克隆、真实 Chat/Story LLM、真实 embedding 检索、真实 Tripo 3D 或真实音频导出质量。
- 已执行检查：`python -m pytest backend/tests/test_config.py backend/tests/test_provider_gateway.py backend/tests/test_parsing.py backend/tests/test_material_extractors.py -q` 10 passed；`python -m json.tool docs/feature-list.json` 退出码 0；`python -m pytest backend/tests -q` 127 passed；`npm.cmd --prefix frontend run test` 53 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0；`docker compose config` 退出码 0；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，required files、JSON、127 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 Frontend UX Polish

- 新增 `MemoryGlobalHeader`，全局导航按 auth token 切换：未登录显示「产品介绍」「登录」「立即体验示例」，已登录显示「记忆空间」「创建人物」「退出」；移动端改为单按钮菜单，路由变化后自动收起。
- 首页移动端压缩首屏，CTA 和 AI 提醒优先可见；桌面端右侧视觉层叠收敛为主图、声音卡和回复气泡。
- 人物记忆空间首屏主操作改为「开始对话」和「听 TA 讲个故事」，资料、记忆、档案、声音和 3D 入口降为行动卡。
- `/personas/{id}/chat` 改为 chat 工作区：顶部工具栏紧凑化，消息列表独立滚动，输入区保持在面板底部；移动端优先显示消息和输入，人物设定/数字人状态折叠；快捷问题可一键填入输入框。
- 对话来源与纠错默认折叠为「回复依据 N 条」，完整 ID、quote 和纠错 textarea 放进展开区；语音消息入口收进折叠面板，无音频资料时直接提供上传入口。
- 修复并复验当前运行环境中 `/personas/{id}/stories` 404 问题：前端构建包含 `/personas/[id]/stories`，`docker compose up --build -d frontend` 后 HTTP 返回 200，浏览器可生成故事、显示 mock 音频并收藏。
- 新增/扩展测试覆盖登录态导航、快捷问题、折叠式来源摘要和音频播放判断；本次改动不新增后端 API、数据库 schema、真实 AI、真实声音、真实 3D 或真实音频导出能力。
- 浏览器复验：1280x720 对话页发送后输入框/发送按钮仍可见且消息列表滚到底；人物空间首屏可见「开始对话」「听 TA 讲个故事」；390x844 首页 CTA 首屏可见、移动菜单无「登录」泄漏、对话页无横向溢出且发送后仍可操作。
- 本次改动文件：`frontend/src/components/MemoryGlobalHeader.tsx`、`frontend/src/lib/memory-space.ts`、`frontend/src/lib/chat.ts`、`frontend/app/layout.tsx`、`frontend/app/page.tsx`、`frontend/app/personas/[id]/page.tsx`、`frontend/app/personas/[id]/chat/page.tsx`、`frontend/tests/memory-space.test.mjs`、`frontend/tests/chat.test.mjs`、`docs/feature-list.json`、`docs/progress.md`、`docs/README.md`、`docs/prd-checklist.md`。
- 已执行检查：`python -m json.tool docs/feature-list.json` 退出码 0；`docker compose config` 退出码 0；`npm.cmd --prefix frontend run test` 53 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，构建包含 `/personas/[id]/stories`；`docker compose up --build -d frontend` 退出码 0，backend healthy、frontend started；HTTP smoke：`/`、`/health`、`/personas/{id}/stories` 均返回 200；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，Real Multimodal Parsing Provider banner、required files、JSON、127 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 Milestone 8 Task 4 Frontend Story Export

- `frontend/src/lib/api.ts` 新增 `API_PATHS.stories.export(personaId, storyId)`，对齐 PRD `GET /api/personas/{id}/export/story/{story_id}`。
- `frontend/src/lib/stories.ts` 新增 `MemoryStoryExportResponse`、`exportStory`、`buildStoryTextDownload`、`buildStoryAudioExportAction` 和 `storyAudioExportAvailable`。
- `/personas/{id}/stories` 故事卡片新增「导出文本」和「打开音频」按钮；文本导出使用浏览器 `.txt` 下载，音频按钮打开后端返回的 mock `audio_url` 并保留 mock/非真实声音提示。
- 新增/扩展 frontend tests，覆盖 export path、文本下载 payload、mock audio action 和 audio availability。
- 保持范围边界：本次不实现真实音频二进制文件、删除关键数据、真实故事生成质量、真实 TTS 音质或完整 Demo flow。
- 已执行检查：`npm.cmd --prefix frontend run test -- stories.test.mjs routes.test.mjs` RED 后 GREEN 53 passed；`npm.cmd --prefix frontend run test` 53 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，构建包含 `/personas/[id]/stories`；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，Milestone 8 Task 4 banner、required files、JSON、121 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

## Previous Session Update - 2026-07-04 Milestone 8 Task 3 Backend Story Export

- 新增 `GET /api/personas/{id}/export/story/{story_id}`，复用当前用户和人物隔离；跨用户或 story 不属于该 persona 时返回 404。
- 新增 `MemoryStoryExportResponse` 和 `export_story` service，返回 story id、persona id、主题、标题、`export_text`、text 文件名、mock `audio_url`、audio 文件名、mock 音频提示、source memory IDs 和来源记忆。
- `export_text` 包含故事标题、主题、正文、来源记忆和默认 TTS/mock 音频提示，不伪造真实 WAV 文件。
- 新增 story export 后端测试，覆盖导出内容、来源记忆、mock audio metadata、跨用户隔离和 persona/story 不匹配 404。
- 保持范围边界：本次不实现前端下载按钮、真实音频二进制文件、删除关键数据、真实故事生成质量、真实 TTS 音质或完整 Demo flow。
- 已执行检查：`python -m pytest backend/tests/test_stories.py -q` RED 404 后 GREEN 5 passed；`python -m pytest backend/tests -q` 121 passed；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，后端 121 passed、前端 52 passed、lint/build 和 Compose config 通过。

## Previous Session Update - 2026-07-04 Milestone 8 Task 2 Frontend Stories

- 新增前端 `/personas/{id}/stories` 回忆讲述页，登录后加载人物与故事列表，支持选择童年、生日、旅行、家常、鼓励、道别或节日主题生成故事。
- 新增 `frontend/src/lib/stories.ts`，统一 stories API helper、PRD 主题、payload、收藏 payload、来源摘要和音频可用性判断；`frontend/src/lib/api.ts` 与 `frontend/src/lib/routes.ts` 新增 story 路径。
- 人物记忆空间新增「听 TA 讲个故事」入口；故事页展示第一人称内容、来源记忆、mock audio 播放控件和收藏切换，并明确当前仍依赖已确认/已修正记忆与 mock provider。
- 新增 `frontend/tests/stories.test.mjs` 并扩展 routes 测试，覆盖 story route、API path、PRD 主题、payload、来源摘要和 audio 判断。
- 保持范围边界：本次不实现故事文本/音频导出、删除关键数据、真实故事生成质量、真实 TTS 音质或完整 Demo flow。
- 已执行检查：`npm.cmd --prefix frontend run test -- stories.test.mjs routes.test.mjs` 49 passed；`npm.cmd --prefix frontend run test` 52 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，构建包含 `/personas/[id]/stories`；`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，后端 119 passed、前端 52 passed、lint/build 和 Compose config 通过。

## Previous Session Update - 2026-07-04 Milestone 8 Task 1 Backend Stories

- 新增 `memory_stories` 模型和 Alembic 迁移，存储人物故事、主题、内容、mock audio URL、来源记忆、收藏状态和 provider/job metadata。
- 新增 `GET/POST /api/personas/{id}/stories` 和 `POST /api/stories/{id}/favorite`，复用用户隔离；跨用户故事列表、生成和收藏返回 404。
- 故事生成只读取 confirmed/corrected 且未删除记忆；没有已审核记忆时返回 400，pending/rejected/disabled/deleted 记忆不会进入故事内容或来源。
- `ProviderGateway` 新增 mock `story_generation` capability，生成第一人称、使用用户称呼、只串联已传入的审核记忆，并返回 source memory IDs/source memory 摘录。
- 每次故事生成同步创建 succeeded `generate_story` AI Job，再调用 mock `tts` 创建 succeeded `synthesize_speech` AI Job；返回 `mock://tts/...wav` audio URL，并保留默认 TTS 提示 metadata。
- 保持范围边界：本次不实现前端 `/personas/{id}/stories` 页面、故事文本/音频导出、删除关键数据、真实故事生成质量、真实 TTS 音质或完整 Demo flow。

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
- Milestone 8 后端故事基础闭环已接入：`memory_stories` 表、stories list/generate/favorite API、mock `story_generation` Provider Gateway、source memory 追溯、mock TTS audio URL、`generate_story` 和 `synthesize_speech` AI Jobs。
- Task 3 已接入 Dockerfile、Compose 拓扑、统一 harness 和 Milestone 0 文档说明。
- Task 3 review fix 已补齐 tracked PRD、自启动迁移 entrypoint、Docker context 忽略文件和 PRD checklist 清理。
- Compose 中只包含变量名、空白 provider 配置和开发默认值，不包含真实密钥。

### What's In Progress

- 真实多模态解析 provider 已接入并通过公网样本端到端烟测；后续仅在模型、账号或解析链路变化后复跑。
- MiniMax TTS/音色复刻和文本 Chat/Story LLM provider 已接入并完成真实冒烟；前端仍缺少真实音色试听确认 flow，故事 mock WAV 文件导出仍未转存 MiniMax 真实音频 URL。
- Milestone 8 数据设置页已接入；真实 GLB/3D provider 质量不作为当前 mock MVP 阻塞。

### What's Next

1. Provider key、模型名或账号权限变化后，复跑 DashScope 多模态烟测和 MiniMax 文本/语音 smoke，确认 provider metadata、trace id 和 job 状态仍正常。
2. Milestone 8 后续验收：继续跟进真实 MinIO/S3 bucket object 删除和向量索引清理。
3. 后续扩展 embedding 或 3D Provider 时，继续保持 provider gateway 和 mock/真实 provider 测试；MiniMax Chat/Story/TTS/音色链路后续补前端试听确认、真实质量评估与真实音频转存，不直接在业务代码中散落模型调用。
4. 跟进当前前端依赖树中的 2 个 moderate severity npm audit findings，避免使用 `npm audit fix --force` 进行破坏性升级。

## Session Impact Checklist

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| 是否改变产品行为 | 是 | 本次会话新增可选 MiniMax 文本 Chat/Story LLM provider；配置 key/base URL 与 `OPENAI_MODEL` 后，文本对话和回忆讲述可返回真实 MiniMax 生成内容。 |
| 是否改变代码逻辑 | 是 | 扩展 MiniMax provider、gateway、chat service 和 provider settings；test env 和未配置 key/model 时保留 mock fallback。 |
| 是否改变启动命令 | 否 | 本地拓扑仍使用 `docker compose up --build`；统一验证入口仍为 `docs/init.sh`。如需真实解析、文本 LLM 或语音，需要本地未提交环境变量。 |
| 是否更新功能范围账本 | 是 | 新增 `feat-040` 记录 MiniMax 文本 Chat/Story LLM 接入与烟测。 |
| 是否更新交接记录 | 是 | 本文件记录 MiniMax 文本 LLM provider 实现、真实冒烟、验证证据和残余风险。 |

## Blockers / Risks

- 本次已运行首页、免注册进入外婆记忆空间和文本对话的真实浏览器烟测；Milestone 7 形象设置页与聊天页数字人区域已运行临时 mock API 浏览器烟测和桌面/移动 canvas 区域像素检查；Milestone 2 上传页、任务页、Milestone 3 记忆审计页、Milestone 4 profile/trust 页、Milestone 6 voice 前端和 Milestone 8 回忆讲述页仍主要依赖自动化测试、lint、build、Compose 配置和 harness 证据。
- 2026-07-04 本地已完成一次 `docker compose up --build -d` 服务级烟测；后续如重启服务，仍应确认本机端口 3000、8000、15432（或 `POSTGRES_HOST_PORT` 指定端口）、6379、9000、9001 未被占用。
- 当前前端依赖树存在 2 个 moderate severity npm audit findings；本任务未改依赖版本，未执行破坏性 `npm audit fix --force`。
- 已新增 `.gitignore` 忽略常见本地生成物和 `.env/`；仍需注意不要手动强制 staging 真实密钥或生成目录。
- 当前资料解析、OCR、ASR、图片理解、视频分析和记忆抽取可选 DashScope provider，但默认仍是 deterministic mock；文本 chat、story generation、TTS 和音色克隆可选 MiniMax provider，默认未配置时仍为 mock；3D 仍使用 mock Provider Gateway/local 输出，不代表真实 3D 模型质量。
- 当前人格档案聚合和可信度重算只使用 deterministic local 规则，不代表真实 provider profile quality。
- Milestone 6 已接入前端录音、声音设置页和 mock/可选 MiniMax 语音播放；本次完成后端真实 MiniMax API 冒烟，仍未运行真实浏览器连接后端的完整语音端到端 smoke。
- Milestone 7 目前完成后端 avatar API、前端 Three.js mock 头像/半身预览和聊天页播放状态口型联动；真实 GLB 加载、真实音频音量包络/viseme 口型同步和真实 3D provider 质量仍未实现。
- 本地一键演示入口、后端故事生成/收藏/导出 API、后端 mock WAV 音频文件导出 API、后端档案/记忆/对话 JSON 导出 API、后端人物删除级联软删除、后端单条对话软删除、后端清空当前账号数据、前端回忆讲述页、前端故事导出入口、前端 mock WAV 音频下载入口、前端数据设置页、MiniMax 文本 Chat/Story LLM 和 MiniMax TTS/音色复刻 provider 已实现；真实 LLM 长期质量、embedding 检索质量、MiniMax 前端端到端体验和真实 3D 质量仍需继续验收。

## Evidence of Completion

- MiniMax voice provider focused GREEN：`python -m pytest backend/tests/test_config.py backend/tests/test_provider_gateway.py backend/tests/test_minimax_provider.py backend/tests/test_voice.py -q` 退出码 0，22 passed。
- MiniMax backend verification：`DEFAULT_LLM_PROVIDER=mock python -m pytest backend/tests -q` 退出码 0，142 passed。
- MiniMax real TTS smoke：本地 MiniMax runtime env configured=true；默认音色 `speech-2.8-hd` 调用 `/v1/t2a_v2` 返回 HTTP audio URL 与 trace id。
- MiniMax real voice clone smoke：下载 LibriVox Short Poetry Collection 277 Public Domain 短诗 MP3 样本（约 69 秒，551,193 bytes），`voice_clone` 返回 succeeded、临时 `minimax://voice/...` artifact 与 preview HTTP URL。
- MiniMax cloned voice TTS smoke：使用本次复刻返回的 `minimax://voice/...` artifact 再次调用 TTS，返回 HTTP audio URL 与 trace id。
- MiniMax final harness：`DEFAULT_LLM_PROVIDER=mock & "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，required files、JSON、142 backend tests、57 frontend tests、frontend lint/build、Compose config 均通过。
- Milestone 8 Task 11 RED：`npm.cmd --prefix frontend run test -- data-settings.test.mjs routes.test.mjs memory-space.test.mjs` 退出码 1，按预期暴露 `frontend/src/lib/data-settings.ts`、`ROUTES.settingsData`、data export API paths 和登录态「数据设置」导航尚未实现。
- Milestone 8 Task 11 focused GREEN：`npm.cmd --prefix frontend run test -- data-settings.test.mjs routes.test.mjs memory-space.test.mjs` 退出码 0，57 passed。
- Milestone 8 Task 11 frontend verification：`npm.cmd --prefix frontend run test` 退出码 0，57 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，Next.js build 包含 `/settings/data`。
- Milestone 8 Task 11 final harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，当前 Real Multimodal Parsing Provider banner、required files、JSON、142 backend tests、57 frontend tests、frontend lint/build、Compose config 均通过。
- Milestone 8 Task 10 RED：`python -m pytest backend/tests/test_settings_data.py -q` 退出码 1，按预期暴露 `DELETE /api/settings/data` 尚不存在。
- Milestone 8 Task 10 provider boundary RED：`python -m pytest backend/tests/test_provider_gateway.py::test_dashscope_memory_candidates_normalize_to_prd_categories -q` 退出码 1，按预期暴露 DashScope 记忆分类仍直通非 PRD enum；`python -m pytest backend/tests/test_chat.py backend/tests/test_exports.py -q` 退出码 1，暴露本地 runtime 真实 provider 会让单元测试触发非确定输出和 ASR storage_url 边界。
- Milestone 8 Task 10 focused GREEN：`python -m pytest backend/tests/test_settings_data.py -q` 退出码 0，1 passed；`python -m pytest backend/tests/test_provider_gateway.py::test_dashscope_memory_candidates_normalize_to_prd_categories -q` 退出码 0，1 passed；`python -m pytest backend/tests/test_chat.py backend/tests/test_exports.py -q` 退出码 0，14 passed。
- Milestone 8 Task 10 adjacent backend verification：`python -m pytest backend/tests/test_settings_data.py backend/tests/test_personas.py backend/tests/test_jobs.py backend/tests/test_materials.py backend/tests/test_provider_gateway.py backend/tests/test_parsing.py -q` 退出码 0，69 passed。
- Milestone 8 Task 10 backend verification：`python -m pytest backend/tests -q` 退出码 0，135 passed。
- Milestone 8 Task 10 final harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，当前 Real Multimodal Parsing Provider banner、required files、JSON、135 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

- Milestone 8 Task 9 RED：`python -m pytest backend/tests/test_chat.py::test_delete_conversation_soft_deletes_messages_and_citations -q` 退出码 1，按预期暴露 `DELETE /api/conversations/{id}` 尚不存在。
- Milestone 8 Task 9 focused GREEN：`python -m pytest backend/tests/test_chat.py::test_delete_conversation_soft_deletes_messages_and_citations -q` 退出码 0，1 passed。
- Milestone 8 Task 9 adjacent backend verification：`python -m pytest backend/tests/test_chat.py backend/tests/test_exports.py -q` 退出码 0，14 passed。
- Milestone 8 Task 9 backend verification：`python -m pytest backend/tests -q` 退出码 0，133 passed。
- Milestone 8 Task 9 final harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，当前 Real Multimodal Parsing Provider banner、required files、JSON、133 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

- Milestone 8 Task 8 RED：`python -m pytest backend/tests/test_personas.py::test_delete_persona_soft_deletes_prd_related_records -q` 首次退出码 1，按预期暴露删除人物后 SourceMaterial 仍未 soft delete；补充 direct job 读取断言后再次退出码 1，按预期暴露已删除 AI Job 仍可由 `/api/jobs/{id}` 读取。
- Milestone 8 Task 8 focused GREEN：`python -m pytest backend/tests/test_personas.py::test_delete_persona_soft_deletes_prd_related_records -q` 退出码 0，1 passed。
- Milestone 8 Task 8 adjacent backend verification：`python -m pytest backend/tests/test_personas.py backend/tests/test_materials.py backend/tests/test_memories.py backend/tests/test_chat.py backend/tests/test_jobs.py backend/tests/test_voice.py backend/tests/test_avatar.py backend/tests/test_stories.py backend/tests/test_exports.py -q` 退出码 0，99 passed。
- Milestone 8 Task 8 backend verification：`python -m pytest backend/tests -q` 退出码 0，132 passed。
- Milestone 8 Task 8 final harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，当前 Real Multimodal Parsing Provider banner、required files、JSON、132 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

- Milestone 8 Task 7 RED：`python -m pytest backend/tests/test_exports.py -q` 退出码 1，3 failed / 1 passed，按预期暴露 profile/memories/conversation export routes 尚不存在。
- Milestone 8 Task 7 focused GREEN：`python -m pytest backend/tests/test_exports.py -q` 退出码 0，4 passed。
- Milestone 8 Task 7 adjacent backend verification：`python -m pytest backend/tests/test_exports.py backend/tests/test_profile.py backend/tests/test_memories.py backend/tests/test_chat.py -q` 退出码 0，26 passed。
- Milestone 8 Task 7 backend verification：`python -m pytest backend/tests -q` 退出码 0，131 passed。
- Milestone 8 Task 7 final harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，当前 Real Multimodal Parsing Provider banner、required files、JSON、131 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

- Milestone 8 Task 6 RED：`npm.cmd --prefix frontend run test -- stories.test.mjs routes.test.mjs` 退出码 1，2 failed，按预期暴露 `API_PATHS.stories.exportAudio` 和 audio file download helper 尚不存在。
- Milestone 8 Task 6 focused GREEN：`npm.cmd --prefix frontend run test -- stories.test.mjs routes.test.mjs` 退出码 0，53 passed。
- Milestone 8 Task 6 frontend verification：`npm.cmd --prefix frontend run test` 退出码 0，53 passed；`npm.cmd --prefix frontend run lint` 退出码 0。
- Milestone 8 Task 6 build fix loop：`npm.cmd --prefix frontend run build` 先因 `downloadBlobFile` 使用未定义 `blob` 失败；修复为 `download.blob` 后遇到 stale `.next` 缺失 `.nft.json` 生成物，删除生成目录并重建后退出码 0，`/personas/[id]/stories` 构建通过。
- Milestone 8 Task 6 final harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，当前 Real Multimodal Parsing Provider banner、required files、JSON、127 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

- Milestone 8 Task 5 RED：`python -m pytest backend/tests/test_stories.py -q` 退出码 1，1 failed / 5 passed，按预期暴露故事音频文件导出 route 尚不存在。
- Milestone 8 Task 5 focused GREEN：`python -m pytest backend/tests/test_stories.py -q` 退出码 0，6 passed。
- Milestone 8 Task 5 provider regression check：`python -m pytest backend/tests/test_provider_gateway.py backend/tests/test_parsing.py::test_parse_job_records_third_party_provider_from_gateway -q` 退出码 0，4 passed。
- Milestone 8 Task 5 backend verification：`python -m pytest backend/tests -q` 退出码 0，127 passed。
- Milestone 8 Task 5 final harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，当前 Real Multimodal Parsing Provider banner、required files、JSON、127 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

- Milestone 8 Task 4 RED：`npm.cmd --prefix frontend run test -- stories.test.mjs routes.test.mjs` 退出码 1，2 failed，按预期暴露 `API_PATHS.stories.export` 和 story export helpers 尚不存在。
- Milestone 8 Task 4 focused GREEN：`npm.cmd --prefix frontend run test -- stories.test.mjs routes.test.mjs` 退出码 0，53 passed。
- Milestone 8 Task 4 frontend verification：`npm.cmd --prefix frontend run test` 退出码 0，53 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，`/personas/[id]/stories` 构建通过。
- Milestone 8 Task 4 final harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，Milestone 8 Task 4 banner、required files、JSON、121 backend tests、53 frontend tests、frontend lint/build、Compose config 均通过。

- Milestone 8 Task 3 RED：`python -m pytest backend/tests/test_stories.py -q` 退出码 1，1 failed / 4 passed，按预期暴露 story export route 尚不存在。
- Milestone 8 Task 3 focused GREEN：`python -m pytest backend/tests/test_stories.py -q` 退出码 0，5 passed。
- Milestone 8 Task 3 backend verification：`python -m pytest backend/tests -q` 退出码 0，121 passed。
- Milestone 8 Task 3 final harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，Milestone 8 Task 3 banner、required files、JSON、121 backend tests、52 frontend tests、frontend lint/build、Compose config 均通过。

- Milestone 8 Task 2 RED：`npm.cmd --prefix frontend run test -- stories.test.mjs routes.test.mjs` 退出码 1，3 failed，按预期暴露 `ROUTES.personaStories`、`API_PATHS.stories` 和 `frontend/src/lib/stories.ts` 尚不存在。
- Milestone 8 Task 2 focused GREEN：`npm.cmd --prefix frontend run test -- stories.test.mjs routes.test.mjs` 退出码 0，49 passed。
- Milestone 8 Task 2 frontend verification：`npm.cmd --prefix frontend run test` 退出码 0，52 passed；`npm.cmd --prefix frontend run lint` 退出码 0；`npm.cmd --prefix frontend run build` 退出码 0，`/personas/[id]/stories` 构建通过。
- Milestone 8 Task 2 final harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，Milestone 8 Task 2 banner、required files、JSON、119 backend tests、52 frontend tests、frontend lint/build、Compose config 均通过。

- Milestone 8 Task 1 RED：`python -m pytest backend/tests/test_stories.py -q` 退出码 1，3 failed，按预期暴露 stories routes 尚不存在。
- Milestone 8 Task 1 focused GREEN：`python -m pytest backend/tests/test_stories.py -q` 退出码 0，3 passed。
- Milestone 8 Task 1 backend verification：`python -m pytest backend/tests -q` 退出码 0，119 passed。
- Milestone 8 Task 1 final harness：`& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh` 退出码 0，Milestone 8 Task 1 banner、required files、JSON、119 backend tests、44 frontend tests、frontend lint/build、Compose config 均通过。

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
