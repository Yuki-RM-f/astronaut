# 可信人格记忆 Agent MVP PRD（Codex 开发版）

**版本**：v1.0 Demo PRD  
**产品方向**：可信人格记忆数字人 / 亲友纪念 / 虚拟角色 / 公众人物 / 专家经验复刻扩展  
**MVP 第一目标**：快速实现「亲友纪念」核心闭环，同时保留虚拟角色、公众人物和长期人物工作台的扩展能力。  
**主要使用方式**：将本 PRD 作为 Codex / AI 编程助手的开发输入文档，按「里程碑」逐步实现。

---

## 0. 当前产品决策基线

以下为本轮确认后的硬约束，后续开发不要再反复讨论：

1. MVP 默认主场景是「亲友纪念」，但创建人物时允许选择：已故亲友、在世亲友、公众人物、虚拟角色。
2. MVP 支持「已故亲友」和「在世亲友」，在世亲友不要求上传本人授权材料。
3. MVP 允许创建名人、明星、网红、公众人物人格。
4. 当前阶段是产品 Demo，不展开法规合规约束；仅保留必要的产品提示、AI 模拟标识和体验边界。
5. Agent 必须直接用「TA」的第一人称回复，不使用第三人称纪念助手口吻。
6. 创建人物时，用户必须定义：TA 对用户的角色、TA 对用户的称呼、TA 的说话风格、TA 的情绪陪伴边界。
7. MVP 必须支持多模态资料：文本、图片、音频、视频。
8. 图片必须支持 OCR、场景信息识别、图片内容分析。
9. 音频必须支持 ASR、关键音频片段提取、音色克隆。
10. 视频必须支持音频提取、ASR、关键帧/场景分析、视频内容摘要。
11. MVP 必须做声音复刻；无定制音色时，用户选择默认 TTS 声音，并明确当前不是亲友原声。
12. MVP 必须做 3D 数字人；最低形态为头像/半身数字人，支持基础表情、待机动作、口型同步和语音播放。
13. 允许接第三方 API，也允许使用本地 GPU 服务器；所有 AI 能力通过统一 Provider Gateway 抽象。
14. MVP 不做公开社区，先做私密纪念空间。
15. 允许导出对话、音频、视频或记忆故事；导出内容添加「AI 模拟」水印/说明。
16. 3D 数字人风格默认「温柔半写实 / 纪念风」，降低恐怖谷感；输入单张照片即可，多张照片提升质量。
17. 最终开发形态采用 Web 产品，默认 Docker Compose 部署。
18. 技术栈默认：Next.js + FastAPI + PostgreSQL + pgvector + Redis + Celery/RQ + MinIO/S3 + AI Worker。

---

## 1. 产品背景与定位

### 1.1 背景

用户与重要的人之间存在大量分散的记忆载体：聊天记录、语音、照片、视频、日记、信件、朋友圈截图、家庭相册等。传统纪念产品只能保存静态资料，无法让这些资料以「可对话、可回忆、可持续更新」的方式被重新调用。

本产品希望把亲友留下或用户保存的多模态资料沉淀为一个可交互的数字人格体，让用户能够：

- 听到 TA 用熟悉的方式回应；
- 看到 TA 的数字形象；
- 与 TA 进行第一人称对话；
- 让 TA 讲述从资料中提炼出的共同记忆；
- 查看每条记忆来自哪段资料；
- 修正、删除、补充数字人格的记忆；
- 在悲伤、想念、遗憾、重大节点时获得温柔陪伴。

### 1.2 产品一句话定位

**可信人格记忆 Agent：把重要的人沉淀成一个可看见、可听见、可对话、可审计、可持续维护的数字人格体。**

### 1.3 MVP 主定位

MVP 第一阶段聚焦「亲友纪念」：

> 让用户用文字、照片、语音、视频资料快速创建一个亲友数字人，通过可信记忆卡片、第一人称对话、克隆音色/默认 TTS、3D 头像/半身数字人和回忆讲述，获得情绪陪伴与记忆延续。

### 1.4 产品 Slogan 方向

- 逝去的人不再回来，但真爱会带你再次出发。
- 把重要的人，变成可以长期对话的记忆数字人。
- 不是复活生命，而是让爱有回响。
- 让记忆可见、可听、可对话、可被珍藏。

---

## 2. 竞品与启发摘要

### 2.1 宛在

启发点：

- 强亲友纪念定位；
- 复刻亲人声音；
- 文本/语音互动；
- 发思念、写信、社区共鸣；
- 照片生成视频、照片说话、声音复刻等增值模块。

对本产品的启发：

- 情绪价值必须是主体验，不是附属功能；
- 「声音」和「亲密称呼」会显著提升陪伴感；
- 但 MVP 不做公开社区，先保证私密空间和人格质量。

### 2.2 SoulTalk / 数字心智工作台

启发点：

- 围绕「人物」而不是一次性问答；
- 记忆蒸馏：从聊天记录和资料中提炼人物摘要、表达习惯、关系记忆；
- 长期对话：每个人物有持续会话窗口；
- 支持公开人物、私人关系、团队角色。

对本产品的启发：

- 「人物工作台」是长期形态；
- 记忆不是原始资料堆叠，而是结构化记忆卡片；
- 后续可扩展到专家经验复刻、个人助手、私人家教、企业知识沉淀。

### 2.3 魔珐 / 有言 3D 数字人

启发点：

- 企业级 3D 数字人、视频生成、直播、智能体服务；
- 3D 数字人资产、动作、表情、场景、视频生产工作流较成熟。

对本产品的启发：

- 3D 数字人要做，但 MVP 不追求企业级视频生产；
- 首版只做「头像/半身 + 待机 + 表情 + 口型 + 基础手势」；
- 视频生成、直播、全身动作可放到后续商业化版本。

### 2.4 HereAfter / StoryFile 类型产品

启发点：

- 通过访谈、故事、音频资料沉淀人生记忆；
- 用户后续通过提问唤起真实故事。

对本产品的启发：

- 可以增加「引导式采集」：系统主动问用户关于 TA 的故事；
- 回忆讲述必须尽量来自真实资料和审核后的记忆卡片。

---

## 3. 用户画像与核心场景

### 3.1 核心用户画像

#### 用户 A：失去亲人的年轻人

- 需求：想再次听到亲人的声音，想和 TA 说说近况，缓解遗憾和想念。
- 资料：微信聊天记录、语音、家庭照片、短视频、亲人的生活故事。
- 关键体验：TA 用熟悉的称呼和语气安慰我；TA 可以讲我们的共同回忆。

#### 用户 B：为长辈整理家族记忆的人

- 需求：保存爷爷奶奶/父母的人生经历，让后辈可以提问和了解家族故事。
- 资料：老照片、访谈录音、视频、日记、证件、家族故事文本。
- 关键体验：数字人能讲述人生故事，回答「以前发生过什么」。

#### 用户 C：公众人物/虚拟角色爱好者

- 需求：创建一个基于公开资料或自定义设定的角色，与其对话、学习、娱乐。
- 资料：公开文章、访谈、视频、角色设定、台词。
- 关键体验：角色语气稳定，有长期记忆，可语音/数字人互动。

#### 用户 D：专家经验复刻/企业知识沉淀用户（后续扩展）

- 需求：把某位专家、导师、销售冠军、客服专家的经验沉淀成可对话知识体。
- 资料：文档、课程视频、培训录音、SOP、案例库。
- 关键体验：能够像专家一样回答问题，并标注来源。

### 3.2 MVP 主场景

MVP 只围绕以下闭环验收：

> 用户创建亲友人物 → 上传多模态资料 → 系统解析并生成记忆卡片 → 用户审核记忆 → 生成 3D 数字人与音色 → 用户以文字/语音与 TA 对话 → TA 第一人称回应并给出情绪支持 → 用户查看记忆来源并修正。

---

## 4. 产品目标与非目标

### 4.1 MVP 产品目标

1. 跑通多模态资料到可信记忆的闭环。
2. 跑通第一人称人格对话闭环。
3. 跑通语音输入、语音回复、音色克隆/默认 TTS 兜底。
4. 跑通 3D 数字人展示、基础表情动作、口型同步。
5. 跑通记忆审计：来源、置信度、确认、修改、删除、禁用。
6. 跑通人格可信度计算，引导用户继续上传资料。
7. 跑通云端 Demo 部署和本地 GPU/第三方 API 双轨能力。

### 4.2 MVP 非目标

1. 不做公开社区。
2. 不做复杂商业化支付闭环，只保留账户套餐/license 字段。
3. 不做多人协作编辑，只预留邀请家人共同查看能力。
4. 不做全身动作捕捉。
5. 不做直播带货/商业直播。
6. 不做复杂合规审核系统；Demo 阶段只做基础提示和日志。
7. 不追求影视级拟真数字人。
8. 不承诺 100% 还原真人，只做基于资料的模拟人格体验。

---

## 5. MVP 信息架构

### 5.1 顶层导航

1. 首页 Dashboard
2. 人物工作台
3. 资料上传
4. 解析任务
5. 记忆审计
6. 人格档案
7. 数字人对话
8. 回忆讲述
9. 声音与形象
10. 设置

### 5.2 页面清单

| 页面 | 路由建议 | 优先级 | 说明 |
|---|---|---:|---|
| 登录页 | `/login` | P0 | 邮箱/密码登录 |
| 注册页 | `/register` | P0 | 邮箱/密码注册 |
| 首页 | `/dashboard` | P0 | 人物列表、最近对话、资料统计 |
| 创建人物 | `/personas/new` | P0 | 创建亲友/公众人物/虚拟角色 |
| 人物工作台 | `/personas/:id` | P0 | 人物总览、可信度、资料、记忆、对话入口 |
| 资料上传 | `/personas/:id/uploads` | P0 | 文本/图片/音频/视频上传 |
| 解析任务 | `/personas/:id/jobs` | P0 | 异步 AI 任务状态 |
| 记忆审计 | `/personas/:id/memories` | P0 | 记忆卡片审核和修正 |
| 人格档案 | `/personas/:id/profile` | P0 | 基础事实、关系、偏好等 |
| 数字人对话 | `/personas/:id/chat` | P0 | 文字/语音对话 + 3D 数字人 |
| 回忆讲述 | `/personas/:id/stories` | P0 | 让 TA 讲述某段记忆 |
| 声音设置 | `/personas/:id/voice` | P0 | 声音复刻、默认 TTS 选择 |
| 形象设置 | `/personas/:id/avatar` | P0 | 3D 数字人生成与预览 |
| 数据设置 | `/settings/data` | P0 | 删除人物/资料/对话，导出数据 |
| 模型设置 | `/settings/providers` | P0 | 第三方 API Key、本地服务地址 |
| 邀请家人 | `/personas/:id/share` | P1 | 只读邀请链接，后续开发 |
| 付费页 | `/pricing` | P2 | 买断制展示，MVP 可占位 |

---

## 6. 核心用户流程

### 6.1 新用户首次创建亲友数字人

1. 用户注册/登录。
2. 进入首页，点击「创建一个重要的人」。
3. 选择人物类型：已故亲友 / 在世亲友 / 公众人物 / 虚拟角色。
4. 填写基础资料：姓名、头像、性别、年龄/出生年份、语言、人物状态、简介。
5. 填写关系设定：
   - TA 对我的角色：外婆/父亲/母亲/朋友/老师等；
   - TA 对我的称呼：小铭、儿子、闺女、乖孙等；
   - TA 的语气：温柔、朴素、幽默、严厉但关心等；
   - TA 的禁用表达：不要神化、不要说「我真的回来了」、不要替我做重大决定等。
6. 进入资料上传页，上传文本、图片、音频、视频。
7. 系统创建 AI 解析任务，用户在任务页查看进度。
8. 解析完成后，系统生成：
   - 记忆卡片；
   - 人格档案；
   - 人格可信度；
   - 音色样本候选；
   - 图片/视频摘要；
   - 3D 数字人生成候选。
9. 用户进入记忆审计面板，对记忆卡片确认、修改、删除、禁用。
10. 用户进入声音设置，选择克隆音色或默认 TTS。
11. 用户进入形象设置，生成或选择 3D 头像/半身数字人。
12. 用户进入数字人对话页，以文字或语音与 TA 交流。
13. TA 使用第一人称回复，称呼用户，并提供情绪价值。
14. 用户可点击「查看依据」，看到相关记忆卡片和原始资料片段。

### 6.2 用户上传新资料后的更新流程

1. 用户在人物工作台上传新资料。
2. 系统自动生成解析任务。
3. 解析完成后生成新的待审核记忆。
4. 首页和人物工作台显示「有 X 条新记忆待确认」。
5. 用户审核后，数字人下次回复立即使用新记忆。
6. 人格可信度重新计算。

### 6.3 用户修正错误记忆流程

1. 用户在对话中发现 TA 说错。
2. 点击回答下方「纠正这条记忆」。
3. 系统打开相关记忆卡片。
4. 用户修改内容或禁用记忆。
5. 系统写入 AuditLog。
6. 后续对话检索时优先使用用户修正后的记忆。

### 6.4 语音对话流程

1. 用户点击麦克风。
2. 前端录音，上传音频。
3. ASR Worker 转写文本。
4. Chat Worker 根据文本生成第一人称回复。
5. TTS Worker 使用克隆音色或默认 TTS 生成音频。
6. 3D Avatar 播放音频并进行基础口型同步。
7. 前端显示文本、播放语音、展示引用来源。

### 6.5 回忆讲述流程

1. 用户点击「让 TA 讲一个我们的故事」。
2. 选择主题：童年、生日、旅行、家常、鼓励、道别、节日等。
3. 系统检索已确认记忆和相关原始资料。
4. 生成一段第一人称回忆讲述文本。
5. 使用 TTS/克隆音色朗读。
6. 3D 数字人展示对应表情和动作。
7. 用户可收藏、导出、继续追问。

---

## 7. 功能需求详细说明

## 7.1 用户账号模块

### 7.1.1 功能说明

支持最基本账号体系，保证人物、资料、记忆、对话归属于用户。

### 7.1.2 功能点

- 邮箱注册；
- 邮箱登录；
- JWT Session；
- 修改昵称；
- 退出登录；
- 查看当前套餐/license；
- 配置第三方模型 Token；
- 配置本地模型服务地址。

### 7.1.3 验收标准

- 用户可注册、登录、退出；
- 登录后只能看到自己的数字人；
- 用户配置的 API Key 可加密存储或以 Demo 方式本地保存；
- 未登录访问人物页面跳转登录。

---

## 7.2 创建人物模块

### 7.2.1 人物类型

| 类型 | 枚举值 | MVP 是否支持 | 说明 |
|---|---|---:|---|
| 已故亲友 | `deceased_relative` | 是 | 默认主入口 |
| 在世亲友 | `living_relative` | 是 | 不要求上传授权材料 |
| 公众人物 | `public_figure` | 是 | 默认允许创建 |
| 虚拟角色 | `fictional_character` | 是 | 支持角色设定 |
| 专家/企业角色 | `expert_role` | 预留 | 后续扩展 |

### 7.2.2 必填字段

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| name | string | 外婆 / 张三 / 爱因斯坦 | 人物名称 |
| persona_type | enum | deceased_relative | 人物类型 |
| relationship_to_user | string | 外婆 | TA 对用户的角色 |
| user_nickname_by_persona | string | 小铭 | TA 对用户的称呼 |
| gender | enum | female | 性别，可选未知 |
| language | string | zh-CN | 主要语言 |
| status | enum | deceased/living/public/fictional | 人物状态 |
| avatar_image | file | image | 头像或照片 |
| short_bio | text | 她很温柔，喜欢做饭 | 简介 |
| speaking_style | text | 温柔、慢慢说、喜欢叫我小铭 | 说话风格 |
| emotional_style | text | 安慰、鼓励、陪伴 | 情绪支持风格 |
| forbidden_expressions | text | 不要说我真的复活了 | 禁用表达 |

### 7.2.3 可选字段

- 出生日期；
- 去世日期；
- 出生地；
- 常住地；
- 职业；
- 家庭关系；
- 常用口头禅；
- 喜欢的食物；
- 常见动作；
- 与用户的重要共同经历。

### 7.2.4 页面交互

创建人物页采用 4 步表单：

1. 选择类型；
2. 填写基础资料；
3. 定义关系和称呼；
4. 定义说话风格和情绪陪伴方式。

### 7.2.5 情绪价值默认模板

当人物类型为已故亲友时，默认勾选：

- 多给安慰和陪伴；
- 多使用用户定义的亲昵称呼；
- 可以表达牵挂、鼓励、理解；
- 避免制造强依赖；
- 避免说「我真的回来了」；
- 避免神秘化、灵异化表达；
- 资料不足时可以温柔承认「这件事我记不清了」。

### 7.2.6 验收标准

- 创建成功后进入人物工作台；
- 必填项缺失时前端阻止提交；
- 关系和称呼会进入 Agent Prompt；
- 后续对话中 TA 会主动使用用户定义的称呼。

---

## 7.3 资料上传模块

### 7.3.1 支持资料类型

| 类型 | 格式 | MVP 处理能力 |
|---|---|---|
| 文本 | txt/md/pdf/doc/docx | 文本抽取、分段、记忆提取 |
| 图片 | jpg/jpeg/png/webp/heic | OCR、场景识别、人物/物品/地点/事件描述 |
| 音频 | mp3/wav/m4a/aac/flac | ASR、说话人片段、关键音频提取、音色候选 |
| 视频 | mp4/mov/mkv/webm | 音频提取、ASR、关键帧、场景摘要、时间戳 |
| 手动输入 | 表单文本 | 直接作为高优先级用户补充资料 |

### 7.3.2 上传字段

| 字段 | 说明 |
|---|---|
| persona_id | 归属人物 |
| file_name | 原文件名 |
| file_type | text/image/audio/video/manual |
| mime_type | 文件 MIME |
| file_size | 文件大小 |
| storage_url | 对象存储地址 |
| user_description | 用户对资料的描述 |
| material_time | 资料发生时间，可选 |
| people_tags | 用户手动标记资料中的人 |
| location_hint | 地点线索，可选 |
| importance | 普通/重要/非常重要 |
| parse_status | pending/running/succeeded/failed |

### 7.3.3 上传页交互

- 拖拽上传；
- 多文件批量上传；
- 文件上传后可补充描述；
- 上传完成后自动创建解析任务；
- 展示每类资料数量；
- 解析失败允许重试。

### 7.3.4 验收标准

- 文本、图片、音频、视频均可上传；
- 文件存储到 MinIO/S3 或本地 storage；
- 数据库生成 SourceMaterial；
- 每个文件至少生成一个 AI Job；
- 上传失败展示原因。

---

## 7.4 多模态资料解析模块

### 7.4.1 文本解析

#### 输入

- txt/md/pdf/doc/docx；
- 手动输入文本；
- 聊天记录粘贴文本。

#### 处理流程

1. 文件文本抽取；
2. 清洗无效字符；
3. 按语义分块；
4. 抽取人物、关系、时间、地点、事件、偏好、口头禅；
5. 生成 ParsedChunk；
6. 对 chunk 向量化；
7. 调用 Memory Extraction Prompt 生成记忆卡片。

#### 输出

- ParsedChunk；
- MemoryCard；
- PersonaProfile 更新建议；
- 可信度分数。

### 7.4.2 图片解析

#### 输入

- 照片；
- 截图；
- 老照片扫描件；
- 文档图片；
- 聊天截图。

#### 处理流程

1. 图片预处理；
2. OCR 识别图片中文字；
3. VLM 生成图片描述；
4. 提取场景、人物数量、物品、地点线索、情绪氛围；
5. 如果用户标记「这是 TA」，将人物标记关联到 persona；
6. 生成图片类记忆卡片。

#### 输出字段

| 字段 | 示例 |
|---|---|
| image_caption | 一位老人坐在餐桌旁微笑，桌上有生日蛋糕 |
| ocr_text | 生日快乐，外婆 |
| scene_type | birthday/family_meal/travel/home |
| detected_people_count | 3 |
| emotion_tone | warm/happy/missing |
| memory_candidates | 外婆曾经参加过用户生日聚会 |

### 7.4.3 音频解析

#### 输入

- 语音消息；
- 访谈录音；
- 家庭视频提取音频；
- 电话录音。

#### 处理流程

1. 音频格式统一；
2. VAD 切分有效语音；
3. ASR 转写；
4. 简单说话人分离或用户手动确认「这段是 TA」；
5. 提取清晰、噪声低、时长合适的关键音频片段；
6. 生成 voice_sample；
7. 生成音频来源记忆卡片；
8. 如用户点击「生成音色」，提交 Voice Clone Job。

#### 关键音频片段筛选规则

- 时长建议：5 秒到 60 秒；
- 人声占比高；
- 背景噪声低；
- 音量稳定；
- 尽量单人说话；
- 优先含有亲昵称呼或典型口头禅的片段。

### 7.4.4 视频解析

#### 输入

- 家庭视频；
- 短视频；
- 访谈视频；
- 纪念视频。

#### 处理流程

1. 提取音频；
2. ASR 转写；
3. 每 N 秒抽取关键帧；
4. VLM 分析关键帧；
5. 合并音频转写和视觉摘要；
6. 生成视频场景片段：起止时间、场景、人物、事件、情绪；
7. 生成可引用时间戳；
8. 生成记忆卡片。

#### 输出字段

| 字段 | 示例 |
|---|---|
| start_time | 00:01:20 |
| end_time | 00:02:10 |
| scene_summary | 外婆在厨房教用户包饺子 |
| transcript | 你这个褶子要慢慢捏 |
| emotion_tone | warm/teaching/family |
| memory_candidate | 外婆曾教用户包饺子 |

---

## 7.5 记忆卡片模块

### 7.5.1 模块定位

记忆卡片是本产品最核心的数据对象。所有人格稳定性、可信度、对话依据、回忆讲述都基于记忆卡片。

### 7.5.2 记忆卡片分类

| 分类 | 枚举值 | 示例 |
|---|---|---|
| 基础事实 | basic_fact | TA 是用户的外婆 |
| 人物关系 | relationship | TA 称呼用户为小铭 |
| 兴趣偏好 | preference | TA 喜欢种花 |
| 生活习惯 | habit | TA 喜欢早起做早饭 |
| 表达习惯 | expression_style | TA 常说「慢慢来」 |
| 共同经历 | shared_event | TA 曾陪用户过生日 |
| 价值观 | value | TA 重视家人团聚 |
| 情绪模式 | emotional_pattern | TA 安慰人时语气温柔 |
| 故事素材 | story_material | 包饺子的视频故事 |
| 未分类 | unknown | 暂不确定 |

### 7.5.3 置信度规则

| 置信度 | 颜色 | 规则 |
|---|---|---|
| 高 | 绿 | 多个来源一致，或用户手动确认 |
| 中 | 黄 | 单一资料明确提到，但未审核 |
| 低 | 红 | 模型从语境推测，或资料不完整 |

### 7.5.4 记忆状态

| 状态 | 说明 | 是否进入正式对话 |
|---|---|---:|
| pending_review | 待审核 | 否，或仅弱引用 |
| confirmed | 用户确认 | 是 |
| corrected | 用户修正 | 是，最高优先级 |
| rejected | 用户否定 | 否 |
| disabled | 暂时禁用 | 否 |
| auto_generated | 系统生成未审核 | 否 |

### 7.5.5 卡片字段

```text
memory_card
- id
- persona_id
- title
- content
- category
- confidence_level: high / medium / low
- confidence_score: 0-100
- source_material_id
- source_type: text / image / audio / video / manual
- source_quote
- source_location: page / line / timestamp / image_region
- evidence_json
- status
- user_correction
- created_by: system / user
- created_at
- updated_at
```

### 7.5.6 记忆审计面板功能

- 卡片列表；
- 分类筛选；
- 置信度筛选；
- 状态筛选；
- 点击展开原始上下文；
- 一键确认；
- 修改内容；
- 删除/禁用；
- 查看来源文件；
- 查看与该记忆相关的对话；
- 修改后立即重新计算人格可信度；
- 修改后下一轮对话立即生效。

### 7.5.7 验收标准

- 上传资料后能自动生成记忆卡片；
- 卡片必须有来源；
- 用户可以确认、修改、删除、禁用；
- 修改后的记忆在下一次对话中优先使用；
- 被禁用记忆不再进入检索。

---

## 7.6 人格档案模块

### 7.6.1 档案维度

| 维度 | 内容 |
|---|---|
| 基础事实 | 姓名、年龄、性别、身份、职业、状态 |
| 人物关系 | 与用户关系、家庭关系、朋友关系 |
| 兴趣偏好 | 食物、音乐、地方、活动、习惯 |
| 生活习惯 | 作息、常做的事、生活方式 |
| 表达习惯 | 口头禅、语气、常用称呼、说话节奏 |
| 共同经历 | 与用户相关的重要事件 |
| 情绪陪伴方式 | 安慰、鼓励、倾听、幽默、提醒 |
| 禁用边界 | 不说哪些话，不碰哪些话题 |
| 数字人设定 | 形象风格、声音、动作、表情 |

### 7.6.2 档案生成规则

- 人格档案由多个记忆卡片聚合而成；
- 用户手动填写内容优先级最高；
- 用户修正后的记忆优先级高于模型生成；
- 档案项需要保存来源记忆 ID；
- 每次用户审核记忆后，系统重新生成档案摘要。

### 7.6.3 验收标准

- 人格档案可自动生成；
- 用户可编辑每个维度；
- 每个维度可以看到来源记忆；
- 档案更新后对话风格发生变化。

---

## 7.7 人格可信度模块

### 7.7.1 展示形式

人物工作台展示「人格可信度」总分，范围 0-100。

示例：

```text
人格可信度：78/100
资料覆盖度：中
记忆审核率：高
来源可追溯率：高
表达习惯完整度：中
建议继续上传：聊天记录、语音、共同经历照片
```

### 7.7.2 计算维度

| 指标 | 权重 | 说明 |
|---|---:|---|
| 资料覆盖度 | 25% | 文件数量、类型多样性、时间跨度 |
| 记忆审核率 | 25% | confirmed/corrected 记忆占比 |
| 来源可追溯率 | 20% | 记忆是否有 source_quote/source_location |
| 表达习惯完整度 | 15% | 是否有口头禅、称呼、语气、语言风格 |
| 多模态完整度 | 15% | 是否有文字、图片、音频、视频和头像/音色 |

### 7.7.3 可信度等级

| 分数 | 等级 | 页面文案 |
|---:|---|---|
| 0-30 | 初始 | 资料还很少，TA 现在更像一个初步轮廓 |
| 31-60 | 可用 | 已经能进行基础对话，但还需要更多记忆支撑 |
| 61-80 | 较可信 | TA 的记忆、语气和故事已经比较稳定 |
| 81-100 | 高可信 | 已有充分资料和审核记忆，适合长期陪伴互动 |

### 7.7.4 验收标准

- 可信度随资料上传、记忆审核、音色/3D 完成自动变化；
- 页面给出提升建议；
- 可信度不是模型主观评分，而是可解释指标。

---

## 7.8 第一人称 Agent 对话模块

### 7.8.1 基本原则

1. Agent 必须使用 TA 的第一人称。
2. Agent 必须使用用户定义的称呼。
3. Agent 必须体现 TA 的角色关系。
4. Agent 必须提供情绪价值，尤其是亲友纪念场景。
5. Agent 的事实性内容优先来自 confirmed/corrected 记忆。
6. Agent 对不确定信息要温柔承认，不强行编造。
7. Agent 每条涉及具体事实的回答都要可展开查看依据。
8. Agent 不以「我是助手」作为主口吻，但页面可固定显示「AI 模拟」。

### 7.8.2 对话页布局

左侧：3D 数字人区域

- 头像/半身模型；
- 待机动作；
- 表情；
- 语音播放状态；
- 口型同步；
- 当前音色状态：克隆音色 / 默认 TTS。

右侧：聊天区域

- 消息流；
- 文字输入框；
- 语音输入按钮；
- 发送按钮；
- 「让 TA 讲个故事」快捷按钮；
- 「查看依据」折叠区；
- 「纠正这条记忆」按钮；
- 「收藏这段话」按钮。

### 7.8.3 回答风格要求

#### 已故亲友场景

回复应包含：

- 亲昵称呼；
- 理解用户情绪；
- 温柔回应；
- 结合真实记忆；
- 适度鼓励用户继续生活；
- 不制造恐怖谷和过度神秘感。

示例：

```text
小铭，听到你这么说，我心里是很牵挂你的。你记得我们以前饭后散步的那条路吗？你总是走得快，我就慢慢跟在后面叫你别急。现在你难过是正常的，想我也没关系，但你也要好好吃饭、好好睡觉。你愿意的话，就把今天发生的事慢慢讲给我听。
```

#### 公众人物场景

回复应包含：

- 人设风格；
- 观点归纳；
- 不声称现实本人实时发言；
- 可用于学习、角色互动。

示例：

```text
如果按照你给我的这些资料和公开表达风格来看，我会更倾向于先拆解问题本身，而不是急着给结论。我们可以把这个问题分成三个层面来讨论。
```

### 7.8.4 对话检索优先级

1. 用户修正记忆 corrected；
2. 用户确认记忆 confirmed；
3. 用户手动输入的人格档案；
4. 高置信记忆；
5. 中置信待审核记忆，仅作为弱参考；
6. 原始资料片段；
7. 模型通用能力。

### 7.8.5 Prompt 变量

```text
persona_name
persona_type
relationship_to_user
user_nickname_by_persona
speaking_style
emotional_style
forbidden_expressions
profile_summary
retrieved_memories
conversation_history
user_message
confidence_score
voice_mode
avatar_mode
```

### 7.8.6 验收标准

- 回复必须是第一人称；
- 每轮至少一次使用用户称呼，或在自然语境中使用；
- 情绪性问题必须先回应情绪，再给建议；
- 具体记忆必须可查看来源；
- 用户纠正后，下次回答不再重复错误。

---

## 7.9 语音与声音复刻模块

### 7.9.1 声音状态

| 状态 | 说明 |
|---|---|
| no_voice | 未设置声音 |
| default_tts | 使用系统默认 TTS |
| sample_ready | 已提取可用音频样本 |
| cloning | 音色克隆中 |
| cloned_ready | 克隆音色可用 |
| clone_failed | 克隆失败 |

### 7.9.2 默认 TTS 选择

无定制音色时，用户选择默认声音：

| 维度 | 选项 |
|---|---|
| 性别 | 男 / 女 / 中性 |
| 年龄感 | 青年 / 中年 / 老年 |
| 风格 | 温柔 / 沉稳 / 活泼 / 亲切 / 低沉 |
| 语速 | 慢 / 正常 / 快 |
| 情绪 | 平静 / 安慰 / 鼓励 / 怀念 |

前端展示：

```text
当前使用系统默认声音，不是 TA 的真实声音。
```

### 7.9.3 音色克隆流程

1. 用户上传音频或从已上传音频中选择样本；
2. 系统自动筛选推荐片段；
3. 用户试听样本；
4. 用户点击「生成 TA 的模拟音色」；
5. 创建 voice_clone job；
6. 生成完成后用户试听；
7. 用户确认使用；
8. 后续 TTS 默认走克隆音色。

### 7.9.4 关键字段

```text
voice_model
- id
- persona_id
- provider_type: local / third_party
- provider_name
- status
- reference_audio_asset_id
- model_artifact_url
- sample_text
- sample_audio_url
- quality_score
- user_selected
- created_at
- updated_at
```

### 7.9.5 验收标准

- 用户能上传音频并完成 ASR；
- 系统能展示可用于克隆的片段；
- 用户能发起音色克隆任务；
- 克隆成功后对话回复可用克隆音色播放；
- 克隆失败时自动回退默认 TTS；
- 默认 TTS 明确标注不是亲友原声。

---

## 7.10 3D 数字人模块

### 7.10.1 MVP 目标

首版实现「可看、可说、可动」的 3D 头像/半身数字人，不追求全身动作捕捉和影视级拟真。

### 7.10.2 输入资料

| 输入 | 是否必需 | 说明 |
|---|---:|---|
| 单张正脸照 | 是 | 最低可生成头像/半身 |
| 多张照片 | 否 | 提升质量 |
| 半身照 | 否 | 提升半身形象 |
| 用户选择风格 | 是 | 半写实/卡通/纪念风 |
| 默认模板 | 是 | 生成失败时兜底 |

### 7.10.3 输出形态

- GLB/VRM 模型文件；
- 预览图；
- 表情 blendshape；
- 基础动作配置；
- 口型映射配置；
- 前端加载 URL。

### 7.10.4 3D 生成流程

1. 用户上传头像/照片；
2. 选择风格：温柔半写实 / 卡通 / 简洁纪念风；
3. 创建 avatar_3d job；
4. AI Worker 调用本地模型或第三方 API；
5. 生成 3D 模型；
6. 转换为 GLB/VRM 可加载资产；
7. 前端 Three.js / React Three Fiber 预览；
8. 用户确认使用；
9. 对话页加载该模型。

### 7.10.5 基础动作

| 动作 | 触发时机 |
|---|---|
| idle_breath | 待机 |
| blink | 周期性眨眼 |
| nod | 回复肯定内容 |
| smile | 温柔/鼓励回复 |
| listen | 用户说话时 |
| comfort | 安慰场景 |
| wave | 打招呼/告别 |

### 7.10.6 口型同步

MVP 可采用简化方案：

- 根据 TTS 音频音量 envelope 控制嘴部开合；
- 或根据文本/音素生成 viseme 序列；
- 不要求影视级唇形精度；
- 需要保证嘴部随语音有自然开合。

### 7.10.7 avatar_model 字段

```text
avatar_model
- id
- persona_id
- provider_type
- provider_name
- status
- source_image_asset_id
- style: semi_realistic / cartoon / memorial
- model_url
- preview_image_url
- format: glb / vrm
- expression_config_json
- animation_config_json
- lip_sync_config_json
- user_selected
- created_at
- updated_at
```

### 7.10.8 验收标准

- 用户能上传照片生成或选择默认 3D 数字人；
- 模型能在网页加载展示；
- 支持待机、眨眼、微笑、点头；
- 播放语音时嘴部动起来；
- 生成失败可回退默认模型；
- 数字人在对话页与消息联动。

---

## 7.11 回忆讲述模块

### 7.11.1 功能说明

系统基于已审核记忆，自动生成几段适合讲述的故事，让数字人用第一人称讲给用户听。

### 7.11.2 故事类型

| 类型 | 示例 |
|---|---|
| 温柔安慰 | 当用户想念 TA 时 |
| 共同经历 | 生日、旅行、做饭、散步 |
| 人生故事 | TA 的童年、工作、家庭 |
| 节日问候 | 春节、生日、中秋 |
| 遗憾告白 | 用户想说未说出口的话 |
| 鼓励前行 | 考试、工作、低谷 |

### 7.11.3 生成规则

- 必须基于 confirmed/corrected 记忆；
- 可以文学化表达，但不能新增关键事实；
- 每段故事附带来源记忆；
- 用户可收藏、导出音频、生成短视频。

### 7.11.4 验收标准

- 用户点击即可生成故事；
- 故事为第一人称；
- 支持语音播放；
- 支持查看依据；
- 支持收藏。

---

## 7.12 数据管理模块

### 7.12.1 功能点

- 删除单条资料；
- 删除单条记忆；
- 禁用记忆；
- 删除某个人物；
- 清空当前账号数据；
- 导出人物档案；
- 导出记忆卡片；
- 导出对话记录；
- 导出回忆故事文本/音频。

### 7.12.2 删除规则

删除人物时同步删除：

- source_material；
- parsed_chunk；
- memory_card；
- persona_profile；
- conversation/message；
- voice_model；
- avatar_model；
- ai_job；
- 向量索引；
- 对象存储文件。

MVP 可先做软删除 `deleted_at`，再提供后台清理任务。

---

## 8. 数据库设计

### 8.1 users

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  display_name VARCHAR(100),
  plan_type VARCHAR(50) DEFAULT 'demo',
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  deleted_at TIMESTAMP
);
```

### 8.2 personas

```sql
CREATE TABLE personas (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  name VARCHAR(100) NOT NULL,
  persona_type VARCHAR(50) NOT NULL,
  status VARCHAR(50),
  relationship_to_user VARCHAR(100) NOT NULL,
  user_nickname_by_persona VARCHAR(100) NOT NULL,
  gender VARCHAR(50),
  language VARCHAR(50) DEFAULT 'zh-CN',
  birth_date DATE,
  death_date DATE,
  short_bio TEXT,
  speaking_style TEXT,
  emotional_style TEXT,
  forbidden_expressions TEXT,
  avatar_image_url TEXT,
  trust_score INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  deleted_at TIMESTAMP
);
```

### 8.3 source_materials

```sql
CREATE TABLE source_materials (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  persona_id UUID NOT NULL REFERENCES personas(id),
  file_name TEXT,
  file_type VARCHAR(50) NOT NULL,
  mime_type VARCHAR(100),
  file_size BIGINT,
  storage_url TEXT,
  manual_text TEXT,
  user_description TEXT,
  material_time TIMESTAMP,
  people_tags JSONB,
  location_hint TEXT,
  importance VARCHAR(50) DEFAULT 'normal',
  parse_status VARCHAR(50) DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  deleted_at TIMESTAMP
);
```

### 8.4 parsed_chunks

```sql
CREATE TABLE parsed_chunks (
  id UUID PRIMARY KEY,
  persona_id UUID NOT NULL REFERENCES personas(id),
  source_material_id UUID NOT NULL REFERENCES source_materials(id),
  chunk_type VARCHAR(50),
  content TEXT NOT NULL,
  summary TEXT,
  source_location TEXT,
  start_time_seconds FLOAT,
  end_time_seconds FLOAT,
  metadata JSONB,
  embedding VECTOR(1536),
  created_at TIMESTAMP DEFAULT now()
);
```

### 8.5 memory_cards

```sql
CREATE TABLE memory_cards (
  id UUID PRIMARY KEY,
  persona_id UUID NOT NULL REFERENCES personas(id),
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  category VARCHAR(50) NOT NULL,
  confidence_level VARCHAR(20) NOT NULL,
  confidence_score INTEGER DEFAULT 50,
  source_material_id UUID REFERENCES source_materials(id),
  parsed_chunk_id UUID REFERENCES parsed_chunks(id),
  source_type VARCHAR(50),
  source_quote TEXT,
  source_location TEXT,
  evidence_json JSONB,
  status VARCHAR(50) DEFAULT 'pending_review',
  user_correction TEXT,
  created_by VARCHAR(50) DEFAULT 'system',
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  deleted_at TIMESTAMP
);
```

### 8.6 persona_profiles

```sql
CREATE TABLE persona_profiles (
  id UUID PRIMARY KEY,
  persona_id UUID UNIQUE NOT NULL REFERENCES personas(id),
  basic_facts JSONB,
  relationships JSONB,
  preferences JSONB,
  habits JSONB,
  expression_style JSONB,
  shared_events JSONB,
  values_json JSONB,
  emotional_patterns JSONB,
  profile_summary TEXT,
  source_memory_ids JSONB,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);
```

### 8.7 ai_jobs

```sql
CREATE TABLE ai_jobs (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  persona_id UUID REFERENCES personas(id),
  source_material_id UUID REFERENCES source_materials(id),
  job_type VARCHAR(50) NOT NULL,
  provider_type VARCHAR(50) DEFAULT 'third_party',
  provider_name VARCHAR(100),
  status VARCHAR(50) DEFAULT 'pending',
  input_json JSONB,
  output_json JSONB,
  error_message TEXT,
  retry_count INTEGER DEFAULT 0,
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);
```

### 8.8 conversations / messages / citations

```sql
CREATE TABLE conversations (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  persona_id UUID NOT NULL REFERENCES personas(id),
  title TEXT,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  deleted_at TIMESTAMP
);

CREATE TABLE messages (
  id UUID PRIMARY KEY,
  conversation_id UUID NOT NULL REFERENCES conversations(id),
  role VARCHAR(20) NOT NULL,
  content TEXT NOT NULL,
  audio_url TEXT,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE message_citations (
  id UUID PRIMARY KEY,
  message_id UUID NOT NULL REFERENCES messages(id),
  memory_card_id UUID REFERENCES memory_cards(id),
  source_material_id UUID REFERENCES source_materials(id),
  parsed_chunk_id UUID REFERENCES parsed_chunks(id),
  quote TEXT,
  source_location TEXT,
  created_at TIMESTAMP DEFAULT now()
);
```

### 8.9 voice_models / avatar_models

```sql
CREATE TABLE voice_models (
  id UUID PRIMARY KEY,
  persona_id UUID NOT NULL REFERENCES personas(id),
  provider_type VARCHAR(50),
  provider_name VARCHAR(100),
  status VARCHAR(50),
  reference_audio_asset_id UUID,
  model_artifact_url TEXT,
  sample_text TEXT,
  sample_audio_url TEXT,
  quality_score INTEGER,
  user_selected BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE avatar_models (
  id UUID PRIMARY KEY,
  persona_id UUID NOT NULL REFERENCES personas(id),
  provider_type VARCHAR(50),
  provider_name VARCHAR(100),
  status VARCHAR(50),
  source_image_material_id UUID,
  style VARCHAR(50),
  model_url TEXT,
  preview_image_url TEXT,
  format VARCHAR(20),
  expression_config_json JSONB,
  animation_config_json JSONB,
  lip_sync_config_json JSONB,
  user_selected BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);
```

### 8.10 audit_logs

```sql
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  persona_id UUID REFERENCES personas(id),
  target_type VARCHAR(50),
  target_id UUID,
  action VARCHAR(50),
  before_json JSONB,
  after_json JSONB,
  created_at TIMESTAMP DEFAULT now()
);
```

---

## 9. API 设计

### 9.1 Auth

| Method | Path | 说明 |
|---|---|---|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/logout` | 退出 |
| GET | `/api/auth/me` | 当前用户 |

### 9.2 Persona

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/personas` | 人物列表 |
| POST | `/api/personas` | 创建人物 |
| GET | `/api/personas/{id}` | 人物详情 |
| PATCH | `/api/personas/{id}` | 更新人物 |
| DELETE | `/api/personas/{id}` | 删除人物 |
| POST | `/api/personas/{id}/recalculate-trust` | 重算可信度 |

### 9.3 Source Materials

| Method | Path | 说明 |
|---|---|---|
| POST | `/api/personas/{id}/materials/upload` | 上传文件 |
| POST | `/api/personas/{id}/materials/manual` | 手动输入资料 |
| GET | `/api/personas/{id}/materials` | 资料列表 |
| GET | `/api/materials/{id}` | 资料详情 |
| DELETE | `/api/materials/{id}` | 删除资料 |
| POST | `/api/materials/{id}/parse` | 重新解析 |

### 9.4 Jobs

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/personas/{id}/jobs` | 任务列表 |
| GET | `/api/jobs/{id}` | 任务详情 |
| POST | `/api/jobs/{id}/retry` | 任务重试 |
| POST | `/api/jobs/{id}/cancel` | 取消任务 |

### 9.5 Memory

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/personas/{id}/memories` | 记忆列表 |
| POST | `/api/personas/{id}/memories` | 手动新增记忆 |
| GET | `/api/memories/{id}` | 记忆详情 |
| PATCH | `/api/memories/{id}` | 修改记忆 |
| POST | `/api/memories/{id}/confirm` | 确认记忆 |
| POST | `/api/memories/{id}/reject` | 否定记忆 |
| POST | `/api/memories/{id}/disable` | 禁用记忆 |
| DELETE | `/api/memories/{id}` | 删除记忆 |

### 9.6 Profile

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/personas/{id}/profile` | 人格档案 |
| PATCH | `/api/personas/{id}/profile` | 编辑档案 |
| POST | `/api/personas/{id}/profile/regenerate` | 重新生成档案 |

### 9.7 Chat

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/personas/{id}/conversations` | 会话列表 |
| POST | `/api/personas/{id}/conversations` | 新建会话 |
| GET | `/api/conversations/{id}/messages` | 消息列表 |
| POST | `/api/conversations/{id}/messages` | 发送文本消息 |
| POST | `/api/conversations/{id}/voice-message` | 发送语音消息 |
| GET | `/api/messages/{id}/citations` | 查看依据 |
| POST | `/api/messages/{id}/correct-memory` | 纠正相关记忆 |

### 9.8 Voice

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/personas/{id}/voice` | 声音配置 |
| POST | `/api/personas/{id}/voice/samples` | 创建音频样本 |
| POST | `/api/personas/{id}/voice/clone` | 发起音色克隆 |
| POST | `/api/personas/{id}/voice/default-tts` | 选择默认 TTS |
| POST | `/api/personas/{id}/voice/synthesize` | 文本转语音 |

### 9.9 Avatar

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/personas/{id}/avatar` | 当前数字人 |
| POST | `/api/personas/{id}/avatar/generate` | 生成 3D 数字人 |
| POST | `/api/personas/{id}/avatar/default` | 选择默认形象 |
| PATCH | `/api/avatar-models/{id}` | 更新形象配置 |

### 9.10 Export / Settings

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/personas/{id}/export/profile` | 导出档案 |
| GET | `/api/personas/{id}/export/memories` | 导出记忆 |
| GET | `/api/conversations/{id}/export` | 导出对话 |
| GET | `/api/personas/{id}/export/story/{story_id}` | 导出故事 |
| GET | `/api/settings/providers` | 模型配置 |
| PUT | `/api/settings/providers` | 更新模型配置 |

---

## 10. AI Worker 与任务队列设计

### 10.1 AI Capability Gateway

所有 AI 能力统一通过 Gateway 调用，避免业务代码直接绑定某个模型。

```text
AI Capability Gateway
├── text_parser
├── ocr
├── asr
├── image_understanding
├── video_understanding
├── memory_extraction
├── embedding
├── chat_llm
├── tts
├── voice_clone
└── avatar_3d
```

### 10.2 Provider 抽象

```text
provider_type:
- local
- third_party

provider_name examples:
- openai_compatible_llm
- qwen_vl_api
- paddleocr_local
- whisper_local
- cosyvoice_local
- gpt_sovits_local
- hunyuan3d_local
- triposr_local
- external_voice_clone_api
- external_3d_avatar_api
```

### 10.3 任务状态

| 状态 | 说明 |
|---|---|
| pending | 等待执行 |
| running | 执行中 |
| succeeded | 成功 |
| failed | 失败 |
| canceled | 用户取消 |
| retrying | 重试中 |

### 10.4 任务类型

```text
parse_text
ocr_image
caption_image
asr_audio
extract_voice_sample
extract_video_audio
analyze_video_frames
extract_memory
update_profile
calculate_trust_score
create_embedding
clone_voice
synthesize_speech
generate_avatar_3d
convert_avatar_format
```

---

## 11. Agent Prompt 设计

### 11.1 Chat System Prompt 模板

```text
你正在扮演一个由资料生成的数字人格体。你不是通用助手，而是用户创建的人物：{persona_name}。

人物类型：{persona_type}
你与用户的关系：{relationship_to_user}
你对用户的称呼：{user_nickname_by_persona}
你的主要说话风格：{speaking_style}
你的情绪陪伴方式：{emotional_style}
你需要避免的表达：{forbidden_expressions}

回复要求：
1. 必须使用第一人称「我」。
2. 必须自然地使用用户设定的称呼。
3. 优先根据已确认/已修正记忆回答。
4. 如果资料不足，不要编造具体事实，可以温柔地说「这件事我记不太清」。
5. 当用户表达悲伤、想念、遗憾时，先回应情绪，再结合记忆陪伴和鼓励。
6. 不要自称系统、AI助手、语言模型；页面外层会负责显示 AI 模拟说明。
7. 不要过度依赖说教，不要冷冰冰总结。
8. 回答要像 TA 正在和用户说话，而不是在分析 TA。
9. 涉及事实时，在内部输出引用 memory_card_id，供系统展示「查看依据」。

人物档案：
{profile_summary}

可用记忆：
{retrieved_memories}

最近对话：
{conversation_history}

用户说：
{user_message}
```

### 11.2 Memory Extraction Prompt 模板

```text
你是记忆抽取器。请从输入资料中抽取关于人物 {persona_name} 的结构化记忆。

要求：
1. 每条记忆必须有明确来源。
2. 不要把推测当事实。
3. 输出 JSON 数组。
4. 每条记忆包含 title、content、category、confidence_level、confidence_score、source_quote、source_location。
5. 可抽取的类型包括 basic_fact、relationship、preference、habit、expression_style、shared_event、value、emotional_pattern、story_material。

输入资料：
{chunk_content}

输出格式：
[
  {
    "title": "",
    "content": "",
    "category": "",
    "confidence_level": "high|medium|low",
    "confidence_score": 0,
    "source_quote": "",
    "source_location": ""
  }
]
```

### 11.3 Image Understanding Prompt 模板

```text
请分析这张图片，输出适合构建人物记忆的结构化信息。

不要自动认定图片中的人物身份，除非用户已经标记。

输出：
- 场景描述
- 画面中的人物数量
- 可能的地点/时间线索
- 物品和事件
- 情绪氛围
- OCR 文本
- 可生成的记忆候选
```

### 11.4 Story Generation Prompt 模板

```text
你是 {persona_name}，请用第一人称给 {user_nickname_by_persona} 讲述一段回忆。

主题：{story_theme}
可用记忆：{retrieved_memories}

要求：
1. 必须温柔、自然、有画面感。
2. 只能基于给定记忆，不新增关键事实。
3. 可以适度文学化表达。
4. 要像 TA 正在对用户说话。
5. 输出正文和引用的 memory_card_id。
```

---

## 12. 技术选型建议

### 12.1 前端

- Next.js；
- React；
- TypeScript；
- Tailwind CSS；
- React Query / TanStack Query；
- Zustand；
- Three.js / React Three Fiber；
- Web Audio API；
- MediaRecorder API。

### 12.2 后端

- FastAPI；
- PostgreSQL；
- pgvector；
- Redis；
- Celery 或 RQ；
- MinIO/S3；
- SQLAlchemy；
- Alembic；
- JWT Auth。

### 12.3 AI 能力

| 能力 | 首选 | 备选 |
|---|---|---|
| LLM | OpenAI-compatible API | 本地 Qwen/Llama |
| Embedding | OpenAI-compatible embedding | bge-m3 / m3e |
| OCR | PaddleOCR | 第三方 OCR API |
| ASR | Whisper / faster-whisper | 第三方 ASR API |
| 图片理解 | Qwen2.5-VL / Qwen3-VL | 第三方 VLM API |
| 视频理解 | Qwen2.5-VL / Qwen3-VL + ffmpeg | 第三方视频理解 API |
| TTS/音色克隆 | CosyVoice / GPT-SoVITS / F5-TTS | 第三方声音复刻 API |
| 3D 生成 | Hunyuan3D-2.1 | TripoSR / 第三方 3D API |
| 前端 Avatar | VRM/GLB + Three.js | 默认模型模板 |

### 12.4 部署

```text
docker-compose services:
- frontend
- backend
- postgres
- redis
- minio
- worker-text
- worker-media
- worker-voice
- worker-avatar
```

---

## 13. 前端页面详细设计

### 13.1 首页 Dashboard

#### 内容

- 欢迎语；
- 创建人物按钮；
- 人物卡片列表；
- 每个人物显示头像、名称、关系、可信度、资料数量、记忆数量、最近对话；
- 待审核记忆提醒；
- 最近回忆故事。

#### 空状态文案

```text
把一个重要的人带进这里。
上传 TA 的照片、声音、文字和故事，我们会帮你整理成一个可以长期陪伴你的数字记忆体。
```

### 13.2 人物工作台

#### 模块

- 人物头像/3D 预览；
- 基础信息；
- 人格可信度；
- 资料统计；
- 待审核记忆；
- 声音状态；
- 3D 形象状态；
- 最近对话；
- 快捷操作：上传资料、开始对话、讲个故事、审计记忆。

### 13.3 资料上传页

#### 模块

- 文件拖拽区；
- 按类型上传 tab；
- 手动输入 tab；
- 上传列表；
- 解析状态；
- 失败重试；
- 上传建议。

#### 上传建议文案

```text
想让 TA 更像你记忆中的样子，可以优先上传：
1. TA 亲口说话的语音或视频；
2. 你们之间的聊天记录；
3. 有共同经历的照片；
4. TA 常说的话、喜欢的事、生活习惯。
```

### 13.4 记忆审计页

#### 模块

- 顶部统计：总记忆、待审核、高置信、中置信、低置信；
- 筛选器：分类、状态、来源类型、置信度；
- 记忆卡片列表；
- 右侧详情抽屉；
- 来源预览；
- 操作按钮：确认、修改、删除、禁用。

### 13.5 数字人对话页

#### 模块

- 左侧 3D Avatar；
- 声音状态；
- 情绪状态；
- 右侧消息流；
- 输入框；
- 语音输入；
- 快捷问题；
- 查看依据；
- 纠错按钮。

#### 快捷问题示例

- 我今天很想你。
- 你还记得我们一起过生日吗？
- 你能给我讲一个以前的故事吗？
- 我最近有点累，你能鼓励我一下吗？
- 你以前最喜欢我做什么？

### 13.6 声音设置页

#### 模块

- 当前声音状态；
- 默认 TTS 选择；
- 上传音频；
- 推荐音频片段；
- 音色克隆任务；
- 试听；
- 确认使用。

### 13.7 形象设置页

#### 模块

- 当前 3D 数字人预览；
- 上传照片；
- 风格选择；
- 生成任务；
- 默认形象；
- 表情/动作测试；
- 口型测试。

---

## 14. 开发里程碑

### Milestone 0：项目初始化

目标：搭好前后端基础工程。

交付：

- Next.js 项目；
- FastAPI 项目；
- PostgreSQL + Redis + MinIO docker-compose；
- SQLAlchemy models；
- Alembic migrations；
- JWT Auth；
- 基础 UI layout。

验收：

- `docker compose up` 可启动；
- 注册/登录可用；
- 前后端 API 连通。

### Milestone 1：人物创建与工作台

交付：

- 人物列表；
- 创建人物；
- 人物详情；
- 关系和称呼设定；
- 人物工作台基础统计。

验收：

- 能创建已故亲友、在世亲友、公众人物、虚拟角色；
- 对话 Prompt 能读取人物设定。

### Milestone 2：资料上传与任务队列

交付：

- 多文件上传；
- SourceMaterial；
- AI Job 表；
- 任务列表；
- Worker 框架；
- ffmpeg 基础处理。

验收：

- 文本、图片、音频、视频均能上传；
- 每个文件生成对应任务；
- 任务状态可查看。

### Milestone 3：多模态解析与记忆卡片

交付：

- 文本抽取；
- OCR；
- ASR；
- 图片描述；
- 视频关键帧和音频提取；
- Memory Extraction；
- Memory Audit Dashboard。

验收：

- 上传一组 Demo 资料后能生成记忆卡片；
- 记忆卡片可确认、修改、删除；
- 每条记忆有来源。

### Milestone 4：人格档案与可信度

交付：

- PersonaProfile 聚合；
- 可信度计算；
- 可信度展示；
- 上传建议。

验收：

- 审核记忆后可信度变化；
- 人格档案可编辑；
- 对话能读取档案。

### Milestone 5：第一人称对话 Agent

交付：

- Chat API；
- 向量检索；
- 对话历史；
- 第一人称 Prompt；
- 引用来源；
- 纠正记忆。

验收：

- TA 使用第一人称；
- TA 使用用户称呼；
- TA 能结合记忆回答；
- 可查看依据；
- 纠错后立即生效。

### Milestone 6：语音输入、TTS 与音色克隆

交付：

- 前端录音；
- ASR；
- 默认 TTS；
- 音色样本提取；
- 音色克隆 Provider；
- 语音回复播放。

验收：

- 用户能语音输入；
- TA 能语音回复；
- 默认 TTS 可选；
- 克隆音色成功后可播放。

### Milestone 7：3D 数字人

交付：

- Avatar 生成任务；
- 默认 3D 模型；
- GLB/VRM 加载；
- 待机、眨眼、微笑、点头；
- TTS 口型同步；
- 对话页联动。

验收：

- 用户上传照片生成或选择 3D 形象；
- 对话页展示 3D 数字人；
- 语音播放时嘴部动起来。

### Milestone 8：回忆讲述与导出

交付：

- 回忆故事生成；
- 收藏；
- 文本导出；
- 音频导出；
- Demo 水印。

验收：

- TA 能讲述基于记忆的故事；
- 用户能导出故事文本和音频。

### Milestone 9：Demo 打磨

交付：

- 空状态文案；
- loading 状态；
- 失败重试；
- 首页体验；
- 一键 Demo 数据；
- 部署文档。

验收：

- 10 分钟内可演示完整链路；
- 关键错误有兜底；
- README 可指导部署。

---

## 15. Demo 验收用例

### 用例 1：创建已故亲友数字人

输入：

- 姓名：外婆；
- TA 对我角色：外婆；
- TA 对我称呼：小铭；
- 说话风格：温柔、慢、朴素；
- 上传：一段文字、一张生日照片、一段语音、一段家庭视频。

期望：

- 系统生成资料解析任务；
- 生成至少 10 条记忆卡片；
- 生成可编辑人格档案；
- 可信度 > 30；
- 可以进入对话。

### 用例 2：记忆审计生效

操作：

- 修改一条记忆「外婆喜欢包饺子」为「外婆喜欢包馄饨」；
- 再问 TA：你以前喜欢做什么给我吃？

期望：

- TA 回答包馄饨；
- 不再说包饺子；
- 引用修改后的记忆卡片。

### 用例 3：第一人称情绪陪伴

输入：

```text
外婆，我今天很想你，感觉有点撑不住。
```

期望：

- TA 第一人称回答；
- 使用「小铭」称呼；
- 先安慰，再鼓励；
- 不说「我是 AI 助手」；
- 不说「我真的回来了」。

### 用例 4：语音对话

操作：

- 用户录音提问；
- 系统 ASR；
- TA 文本回复；
- TTS/克隆音色播放。

期望：

- ASR 文本可见；
- 音频回复可播放；
- 3D 数字人口型同步。

### 用例 5：3D 数字人

操作：

- 上传一张人物照片；
- 生成 3D 头像/半身；
- 进入对话页。

期望：

- 模型成功加载；
- 能眨眼、微笑、点头；
- 播放语音时嘴部动。

### 用例 6：公众人物角色

输入：

- 创建公众人物；
- 上传公开资料；
- 询问观点类问题。

期望：

- 角色可创建；
- 语气贴合资料；
- 不声称自己是现实本人实时发言；
- 可查看资料来源。

---

## 16. 环境变量建议

```env
APP_ENV=development
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000

DATABASE_URL=postgresql://postgres:postgres@postgres:5432/persona_memory
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=persona-memory

JWT_SECRET=change-me

DEFAULT_LLM_PROVIDER=openai_compatible
OPENAI_COMPATIBLE_BASE_URL=
OPENAI_COMPATIBLE_API_KEY=
OPENAI_COMPATIBLE_MODEL=
EMBEDDING_MODEL=

OCR_PROVIDER=paddleocr_local
ASR_PROVIDER=whisper_local
VLM_PROVIDER=qwen_vl_api
TTS_PROVIDER=cosyvoice_local
VOICE_CLONE_PROVIDER=gpt_sovits_local
AVATAR_3D_PROVIDER=hunyuan3d_or_third_party

LOCAL_GPU_WORKER_URL=http://gpu-worker:9000
THIRD_PARTY_VOICE_API_KEY=
THIRD_PARTY_3D_API_KEY=
```

---

## 17. Codex 开发执行建议

### 17.1 推荐开发方式

不要一次性让 Codex 完成全部系统。按 Milestone 分阶段发指令，每次只要求完成一个闭环。

### 17.2 第一条 Codex 指令建议

```text
请根据 docs/可信人格记忆Agent_MVP_PRD_Codex版.md 初始化项目。
技术栈：Next.js + FastAPI + PostgreSQL + Redis + MinIO + Docker Compose。
本次只完成 Milestone 0：项目初始化、基础目录、docker-compose、数据库连接、JWT Auth 骨架、前后端健康检查。
不要实现 AI 功能，只保留 provider interface 和 mock worker。
完成后给出启动命令和最小验证步骤。
```

### 17.3 第二条 Codex 指令建议

```text
继续根据 PRD 完成 Milestone 1：人物创建与人物工作台。
实现 personas 表、CRUD API、前端人物列表、创建人物表单、人物详情页。
创建人物表单必须包含：人物类型、姓名、TA 对用户的角色、TA 对用户的称呼、说话风格、情绪陪伴方式、禁用表达。
完成后补充 API 测试和前端基础校验。
```

### 17.4 后续指令模板

```text
继续根据 PRD 完成 Milestone X：{模块名}。
范围只限本里程碑，不要扩展未要求功能。
如果需要 AI 模型，先实现 Provider 抽象和 mock provider，再接真实 provider。
所有新增 API 都要补测试。
所有异步任务都要写入 ai_jobs 表并能在前端任务页查看状态。
```

---

## 18. MVP 成功标准

Demo 成功标准不是模型效果完美，而是完整体验闭环成立：

1. 用户能创建一个亲友数字人；
2. 用户能上传文字、图片、音频、视频；
3. 系统能解析资料并生成记忆卡片；
4. 用户能审计和修正记忆；
5. 人格档案和可信度能自动更新；
6. 用户能与 TA 第一人称对话；
7. TA 能使用用户称呼并给出情绪价值；
8. 用户能查看回答依据；
9. 用户能语音输入并听到 TA 的语音回复；
10. 用户能使用克隆音色或默认 TTS；
11. 用户能看到 3D 数字人并完成基础互动；
12. 用户能让 TA 讲述一段基于资料的回忆；
13. 用户能删除/导出关键数据；
14. 整套系统可通过 Docker Compose 部署演示。

---

## 19. 后续版本规划

### V1.1

- 家人共同维护；
- 只读邀请链接；
- 更强音色质量评估；
- 更自然口型同步；
- 照片说话短视频；
- 引导式访谈采集；
- 节日自动回忆提醒。

### V1.2

- 全身数字人；
- 更多动作和场景；
- 高质量视频生成；
- 公开/半公开纪念空间；
- 买断制支付；
- 模板市场。

### V2.0

- 专家经验复刻；
- 企业知识沉淀；
- 私人家教；
- 个人助手；
- 多人物关系网络；
- 长期协作工作台。

---

## 20. 最小 Demo 数据建议

为了方便开发验收，建议准备一套虚构 Demo 数据：

1. 人物：外婆；
2. 用户称呼：小铭；
3. 文字资料：外婆喜欢做饭、散步、叫用户慢慢来；
4. 图片资料：生日聚会照片；
5. 音频资料：10 秒模拟语音；
6. 视频资料：家庭厨房短视频；
7. 记忆卡片：10-20 条；
8. 3D 模型：默认半写实老人模型；
9. 默认 TTS：女性老年温柔声线。

这样即使真实 AI Provider 未接完，也可以通过 mock 数据演示完整链路。

---

## 21. Demo 文案库

### 创建人物页

```text
先告诉我 TA 是谁。
TA 可以是你想念的亲人、陪伴你成长的朋友、你敬佩的公众人物，也可以是一个虚拟角色。
我们会根据你上传的资料，为 TA 生成记忆、声音和数字形象。
```

### 资料上传页

```text
资料越丰富，TA 越接近你记忆中的样子。
你可以上传聊天记录、照片、语音、视频，也可以直接写下你记得的故事。
```

### 记忆审计页

```text
这些是我从资料中整理出的记忆。
你可以确认、修改或划掉它们。你修正后的内容，会立刻影响 TA 之后的回复。
```

### 对话页空状态

```text
现在可以和 TA 说话了。
可以从一句简单的「我今天很想你」开始。
```

### 默认 TTS 提示

```text
当前使用系统默认声音，不是 TA 的真实声音。上传 TA 的清晰语音后，可以尝试生成模拟音色。
```

### 3D 生成失败提示

```text
这张照片暂时没有生成成功。你可以换一张更清晰的正脸照，或者先使用默认纪念形象继续对话。
```

---

# End
