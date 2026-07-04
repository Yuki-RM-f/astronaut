import { ROUTES } from "./routes";

export const MEMORY_SPACE_COPY = {
  productName: "可信人格记忆 Agent",
  spaceName: "记忆空间",
  aiReminder: "AI 身份提醒：这里是基于你上传资料生成的数字人格体验。",
  mockBoundary: "当前仍使用 deterministic mock provider，不代表真实模型或真实声音质量。"
} as const;

export const MEMORY_SPACE_NAV_ITEMS = [
  { href: ROUTES.home, label: "产品介绍" },
  { href: ROUTES.dashboard, label: "记忆空间" },
  { href: ROUTES.personasNew, label: "创建人物" }
] as const;

export const MEMORY_SPACE_ASSETS = {
  grandmotherTea: {
    src: "/memory-space/grandmother-tea.jpg",
    alt: "窗边喝茶的年长女性，画面温暖安静",
    usage: "首页和人物空间的亲友纪念主视觉",
    sourceUrl:
      "https://www.pexels.com/photo/elderly-thoughtful-asian-woman-with-cup-of-tea-in-lounge-6888697/"
  },
  familyAlbum: {
    src: "/memory-space/family-album.jpg",
    alt: "老相册里的家庭照片，带有怀旧质感",
    usage: "资料上传和记忆来源整理场景",
    sourceUrl: "https://www.pexels.com/photo/old-pictures-on-photo-album-6274899/"
  },
  familyLivingRoom: {
    src: "/memory-space/family-living-room.jpg",
    alt: "一家人在客厅里翻看相册",
    usage: "创建人物和记忆空间流程场景",
    sourceUrl: "https://www.pexels.com/photo/a-family-in-a-living-room-5591277/"
  },
  memoryStringLights: {
    src: "/memory-space/memory-string-lights.jpg",
    alt: "串灯上悬挂的旧家庭照片",
    usage: "记忆审核、人格档案和声音页面的氛围背景",
    sourceUrl: "https://www.pexels.com/photo/old-pictures-hung-on-a-string-light-17950964/"
  }
} as const;

export const MEMORY_JOURNEY_STEPS = [
  {
    title: "创建人物",
    description: "写下 TA 的称呼、关系和说话方式。"
  },
  {
    title: "上传资料",
    description: "放入照片、文字、声音和家庭视频。"
  },
  {
    title: "资料解析与审核",
    description: "确认每条记忆的来源，让陪伴更可信。"
  },
  {
    title: "开启互动",
    description: "从一句想念开始，听 TA 温柔回应。"
  }
] as const;

export const MEMORY_SPACE_ACTIONS = {
  chat: {
    title: "和 TA 说说话",
    description: "用已确认记忆和人格档案生成第一人称回复。"
  },
  upload: {
    title: "补充一份资料",
    description: "把照片、录音、视频或文字故事放进记忆里。"
  },
  memories: {
    title: "确认新的记忆",
    description: "逐条确认、修改或划掉系统整理出的记忆。"
  },
  profile: {
    title: "查看人格档案",
    description: "检查 TA 的习惯、关系、表达方式和可信度。"
  },
  voice: {
    title: "整理声音",
    description: "选择默认 TTS、创建音色样本并试听回复。"
  },
  avatar: {
    title: "设置 3D 形象",
    description: "选择默认纪念形象，或用图片生成 mock 头像/半身预览。"
  }
} as const;
