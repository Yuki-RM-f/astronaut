import { ROUTES } from "./routes";

export const MEMORY_SPACE_COPY = {
  productName: "可信人格记忆 Agent",
  spaceName: "记忆空间",
  aiReminder: "AI 身份提醒：这里是基于你上传资料生成的数字人格体验。",
  mockBoundary: "当前仍使用 deterministic mock provider，不代表真实模型或真实声音质量。"
} as const;

export const MEMORY_SPACE_NAV_ITEMS = [
  { href: ROUTES.home, label: "首页" },
  { href: ROUTES.productIntro, label: "产品介绍" },
  { href: ROUTES.personasNew, label: "创建档案" },
  { href: ROUTES.dashboard, label: "我的星空" }
] as const;

export type PersonaWorkspaceNavKey =
  | "overview"
  | "uploads"
  | "jobs"
  | "memories"
  | "chat"
  | "regrets"
  | "wishes"
  | "voice"
  | "avatar";

export type PersonaWorkspaceNavItem = {
  key: PersonaWorkspaceNavKey;
  label: string;
  href: string;
  description: string;
};

export type PersonaWorkspaceNavGroup = {
  label: string;
  items: PersonaWorkspaceNavItem[];
};

export function getPersonaWorkspaceNavGroups(personaId: string): PersonaWorkspaceNavGroup[] {
  return [
    {
      label: "总览",
      items: [
        {
          key: "overview",
          label: "人物总览",
          href: ROUTES.personaDetail(personaId),
          description: "查看资料建议、互动入口和人格设定。"
        }
      ]
    },
    {
      label: "资料",
      items: [
        {
          key: "uploads",
          label: "资料上传",
          href: ROUTES.personaUploads(personaId),
          description: "补充资料，审核资料解析结果。"
        },
        {
          key: "jobs",
          label: "资料任务",
          href: ROUTES.personaJobs(personaId),
          description: "查看解析、抽取和语音合成进度。"
        }
      ]
    },
    {
      label: "记忆",
      items: [
        {
          key: "memories",
          label: "记忆档案馆",
          href: ROUTES.personaMemories(personaId),
          description: "让 TA 讲述几段回忆，搜索已整理记忆。"
        }
      ]
    },
    {
      label: "互动",
      items: [
        {
          key: "chat",
          label: "星星对话",
          href: ROUTES.personaChat(personaId),
          description: "进入文字、手势和语音对话。"
        },
        {
          key: "regrets",
          label: "遗憾对话室",
          href: ROUTES.personaRegrets(personaId),
          description: "说出以前没来得及说的话。"
        },
        {
          key: "wishes",
          label: "心愿延续系统",
          href: ROUTES.personaWishes(personaId),
          description: "写下想继续完成的心愿和下一步行动。"
        },
        {
          key: "voice",
          label: "声音",
          href: ROUTES.personaVoice(personaId),
          description: "设置默认 TTS、音色样本和语音预览。"
        },
        {
          key: "avatar",
          label: "3D 形象",
          href: ROUTES.personaAvatar(personaId),
          description: "上传 GLB 模型并查看数字人预览。"
        }
      ]
    }
  ];
}

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
    usage: "资料审核和声音页面的氛围背景",
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
    description: "用已确认记忆和档案摘要生成第一人称回复。"
  },
  upload: {
    title: "补充一份资料",
    description: "把照片、录音、视频或文字故事放进记忆里。"
  },
  memories: {
    title: "进入记忆档案馆",
    description: "让 TA 讲几段回忆，并搜索已整理记忆。"
  },
  regrets: {
    title: "进入遗憾对话室",
    description: "把以前没来得及说的话慢慢说完。"
  },
  wishes: {
    title: "记录一个心愿",
    description: "把想继续完成的事拆成下一步行动。"
  },
  voice: {
    title: "整理声音",
    description: "选择默认 TTS、创建音色样本并试听回复。"
  },
  avatar: {
    title: "设置 3D 形象",
    description: "上传自包含 GLB 模型，并在对话侧展示同一数字人。"
  }
} as const;
