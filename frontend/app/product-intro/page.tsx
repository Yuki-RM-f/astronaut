"use client";

import { useCallback, useEffect, useState } from "react";
import { StarNav, StarShell } from "@/src/components/StarSite";

type RoadshowCard = {
  title: string;
  text?: string;
  items?: string[];
  pills?: string[];
  gold?: boolean;
};

type RoadshowStep = {
  number: string;
  title: string;
  text: string;
};

type RoadshowSlide = {
  eyebrow: string;
  title: string;
  lead?: string;
  pills?: string[];
  cards?: RoadshowCard[];
  steps?: RoadshowStep[];
  quote?: string;
  subtle?: string;
  cover?: boolean;
};

const COVER_IMAGE = "/product-intro/cover-starry-girl.png";

const ROADSHOW_SLIDES: RoadshowSlide[] = [
  {
    eyebrow: "Product Roadshow",
    title: "“复活”亲友，让思念有处安放",
    lead: "帮助用户与逝去亲友记忆对话的数字人格 Agent",
    pills: ["多模态记忆", "人格边界", "情感疗愈", "数字陪伴"],
    cover: true
  },
  {
    eyebrow: "Market Insight",
    title: "失亲哀伤，需要新的陪伴方式",
    cards: [
      {
        title: "安全出口",
        text: "失去亲友后的痛苦，常常缺少一个可持续、可表达、不会打扰他人的出口。",
        gold: true
      },
      {
        title: "传统方式断点明显",
        text: "心理咨询门槛高，纪念相册偏静态，亲友倾诉难以长期承接。"
      },
      {
        title: "需求已被验证",
        text: "AI 情感陪伴与 griefbot 已有大规模使用，说明用户存在继续连接、表达遗憾、保存记忆的需求。"
      }
    ]
  },
  {
    eyebrow: "Competition Gap",
    title: "现有产品，解决得还不够深",
    cards: [
      {
        title: "资料输入门槛高",
        text: "用户需要主动整理大量信息，创建成本高，越悲伤越难开始。"
      },
      {
        title: "交互方式单一",
        text: "大多停留在文字或语音对话，情感层次和陪伴感偏浅。"
      },
      {
        title: "缺乏“走出来”的心理治疗",
        text: "容易强化“TA 还在”的幻觉，而非帮助用户逐渐修复哀伤。"
      }
    ],
    quote: "机会不在“像不像”，而在能不能整理记忆、表达遗憾、修复哀伤。"
  },
  {
    eyebrow: "Positioning",
    title: "我们不是简单复刻一个 AI 亲友",
    lead: "我们构建的是一个有边界、有来源、有疗愈路径的数字人格体。",
    cards: [
      {
        title: "有来源",
        text: "用户确认后，记忆才进入人格档案。",
        gold: true
      },
      {
        title: "有边界",
        text: "不虚构关键事实，不替代真实亲友。",
        gold: true
      },
      {
        title: "有路径",
        text: "帮助用户表达遗憾、整理记忆、延续心愿。",
        gold: true
      }
    ]
  },
  {
    eyebrow: "Highlight 01",
    title: "低门槛创建数字人格",
    lead: "用户不需要懂 Prompt，也不需要先整理资料，只要上传碎片化回忆。",
    cards: [
      {
        title: "输入：自然散落的资料",
        pills: ["老照片", "语音片段", "家庭视频", "纪念文字", "亲友故事", "聊天记录"]
      },
      {
        title: "解析：结构化人格档案",
        items: ["基础事实、人物关系、兴趣偏好", "生活习惯、表达习惯、共同经历"],
        gold: true
      }
    ]
  },
  {
    eyebrow: "Highlight 02",
    title: "多模态互动，更接近真实陪伴",
    cards: [
      {
        title: "文字对话",
        text: "适合深度表达、长文本倾诉、回忆追问。",
        gold: true
      },
      {
        title: "语音对话",
        text: "让情绪有声音，也让回应更像陪伴。",
        gold: true
      },
      {
        title: "视频互动",
        text: "通过数字人形象、表情和手势建立情绪连接。",
        gold: true
      }
    ],
    subtle: "从“能说话”走向“能被看见、听见、陪伴”。"
  },
  {
    eyebrow: "Highlight 03",
    title: "明确的疗愈路径",
    lead: "目标不是让用户沉迷，而是帮助用户告别。",
    steps: [
      {
        number: "1",
        title: "记忆档案馆",
        text: "回忆疗法：让 TA 讲述共同经历过的故事，重新整理爱与记忆。"
      },
      {
        number: "2",
        title: "遗憾对话室",
        text: "空椅子疗法：说出没来得及说的话，完成情绪表达。"
      },
      {
        number: "3",
        title: "心愿延续系统",
        text: "纪念行动疗法：记录并完成 TA 的愿望，把悲伤转化为行动。"
      }
    ]
  },
  {
    eyebrow: "Demo Focus",
    title: "三个演示场景",
    cards: [
      {
        title: "场景一：记忆档案馆",
        text: "“让爷爷讲讲他下南洋的故事。”",
        gold: true
      },
      {
        title: "场景二：遗憾对话室",
        text: "“爷爷，你这一生真的很了不起。”",
        gold: true
      },
      {
        title: "场景三：心愿延续系统",
        text: "生成心愿：好好照顾阿嬷和家里人。",
        gold: true
      }
    ]
  },
  {
    eyebrow: "Business Model",
    title: "商业化设计：分层订阅制",
    cards: [
      {
        title: "免费体验",
        items: ["创建 1 位人物档案", "基础资料和互动"]
      },
      {
        title: "VIP订阅",
        items: ["创建多位人物档案", "长期记忆维护", "多模态互动"],
        gold: true
      },
      {
        title: "SVIP订阅",
        items: ["数字人形象精修", "更专业的心理帮助", "家庭成员共同维护"]
      }
    ],
    subtle: "订阅制匹配持续对话、资料存储和多模态生成的长期成本。"
  },
  {
    eyebrow: "Risk Control",
    title: "风险把控：授权、隐私、心理安全",
    cards: [
      {
        title: "肖像权与授权",
        items: ["上传者确认资料使用权", "声音与视频需授权确认", "明确标识 AI 生成"]
      },
      {
        title: "隐私与数据安全",
        items: ["用户资料加密存储", "敏感内容不用于公开训练"]
      },
      {
        title: "心理安全",
        items: ["避免诱导过度依赖", "严重哀伤触发风险提示", "引导现实支持与专业帮助"],
        gold: true
      }
    ]
  },
  {
    eyebrow: "Roadmap",
    title: "后续迭代方向",
    cards: [
      {
        title: "复活宠物",
        text: "宠物陪伴同样具有强情感价值，适合拓展为独立场景。",
        gold: true
      },
      {
        title: "更仿真的数字人",
        text: "提升面部表情、声音、手势、语气一致性。",
        gold: true
      },
      {
        title: "更明确的疗愈路径",
        text: "从“回忆、表达、告别、延续”设计阶段化任务。",
        gold: true
      }
    ]
  },
  {
    eyebrow: "Closing",
    title: "真正的告别，不是忘记",
    lead: "而是终于可以带着爱，继续往前走。",
    quote: "我们想做的，不是复活逝去的人，而是复活那些还没来得及好好说出口的爱。"
  }
];

function normalizeSlideIndex(index: number) {
  return (index + ROADSHOW_SLIDES.length) % ROADSHOW_SLIDES.length;
}

function readHashSlideIndex() {
  const hashSlide = Number.parseInt(window.location.hash.replace("#", ""), 10);
  return Number.isFinite(hashSlide) ? normalizeSlideIndex(hashSlide - 1) : 0;
}

export default function ProductIntroPage() {
  const [currentSlide, setCurrentSlide] = useState(0);

  const showSlide = useCallback((index: number) => {
    const nextSlide = normalizeSlideIndex(index);
    setCurrentSlide(nextSlide);
    window.history.replaceState(null, "", `#${nextSlide + 1}`);
  }, []);

  const goToSlide = useCallback(
    (offset: number) => {
      showSlide(currentSlide + offset);
    },
    [currentSlide, showSlide]
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === "ArrowRight" || event.key === " " || event.key === "PageDown") {
        event.preventDefault();
        goToSlide(1);
      }

      if (event.key === "ArrowLeft" || event.key === "PageUp") {
        event.preventDefault();
        goToSlide(-1);
      }

      if (event.key === "Home") {
        event.preventDefault();
        showSlide(0);
      }

      if (event.key === "End") {
        event.preventDefault();
        showSlide(ROADSHOW_SLIDES.length - 1);
      }
    },
    [goToSlide, showSlide]
  );

  useEffect(() => {
    const syncSlideFromHash = () => setCurrentSlide(readHashSlideIndex());

    syncSlideFromHash();
    window.addEventListener("hashchange", syncSlideFromHash);
    return () => window.removeEventListener("hashchange", syncSlideFromHash);
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const activeSlide = ROADSHOW_SLIDES[currentSlide];
  const progress = ((currentSlide + 1) / ROADSHOW_SLIDES.length) * 100;

  return (
    <StarShell className="h-screen overflow-hidden">
      <StarNav />
      <main
        className="relative mx-auto flex h-[calc(100vh-5rem)] w-full max-w-[1500px] items-center justify-center px-3 pb-20 sm:px-5 md:pb-20"
        aria-live="polite"
      >
        <section
          className={`relative w-[min(92vw,1420px)] overflow-hidden rounded-[30px] border border-starGold/15 bg-[linear-gradient(145deg,rgba(61,46,112,0.78),rgba(27,28,79,0.68))] shadow-[inset_0_1px_0_rgba(255,255,255,.08),0_28px_90px_rgba(0,0,0,.34)] backdrop-blur-xl md:aspect-[16/9] md:max-h-[84vh] ${
            activeSlide.cover ? "min-h-[68vh] md:min-h-0" : "min-h-[68vh] md:min-h-0"
          }`}
          style={
            activeSlide.cover
              ? {
                  backgroundImage: `linear-gradient(90deg, rgba(5, 8, 28, 0.82) 0%, rgba(8, 13, 42, 0.58) 42%, rgba(8, 13, 42, 0.1) 78%), linear-gradient(180deg, rgba(8, 13, 42, 0.1), rgba(8, 13, 42, 0.42)), url("${COVER_IMAGE}")`,
                  backgroundPosition: "center",
                  backgroundSize: "cover"
                }
              : undefined
          }
        >
          <div
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_82%_15%,rgba(255,210,138,0.16),transparent_18%),radial-gradient(circle_at_18%_88%,rgba(181,128,255,0.16),transparent_24%),linear-gradient(120deg,rgba(255,240,210,0.04),transparent_42%)]"
            aria-hidden="true"
          />
          <div
            className={`relative z-10 flex h-full flex-col justify-center gap-5 overflow-y-auto p-7 sm:p-9 lg:p-12 ${
              activeSlide.cover ? "max-w-full md:max-w-[58%] md:text-shadow-lg" : ""
            }`}
          >
            <div className="inline-flex items-center gap-2 text-[clamp(0.7rem,1vw,0.9rem)] font-black uppercase text-starGold">
              <span className="h-3 w-3 rounded-full bg-starGold shadow-[0_0_20px_rgba(255,210,138,.82)]" />
              {activeSlide.eyebrow}
            </div>
            <h1 className="max-w-[980px] font-serif text-[clamp(2rem,5.2vw,4.75rem)] font-bold leading-[1.08] text-starGold shadow-starGold/10 [text-shadow:0_0_26px_rgba(255,210,138,.12)]">
              {activeSlide.title}
            </h1>
            {activeSlide.lead ? (
              <p className="max-w-[940px] text-[clamp(0.95rem,1.45vw,1.45rem)] font-bold leading-[1.42] text-starCream/88">
                {activeSlide.lead}
              </p>
            ) : null}
            {activeSlide.pills ? <PillRow pills={activeSlide.pills} /> : null}
            {activeSlide.cards ? <CardGrid cards={activeSlide.cards} /> : null}
            {activeSlide.steps ? <Timeline steps={activeSlide.steps} /> : null}
            {activeSlide.quote ? (
              <blockquote className="max-w-[900px] rounded-[20px] border-l-4 border-starGold bg-[#403474]/50 px-6 py-5 font-serif text-[clamp(1.25rem,2.05vw,2rem)] font-extrabold leading-[1.34] text-starCream">
                {activeSlide.quote}
              </blockquote>
            ) : null}
            {activeSlide.subtle ? (
              <p className="text-[clamp(0.75rem,0.95vw,0.95rem)] font-bold text-starMist/55">
                {activeSlide.subtle}
              </p>
            ) : null}
          </div>
        </section>

        <div className="absolute bottom-6 left-1/2 z-20 flex -translate-x-1/2 items-center gap-3">
          <button
            type="button"
            className="grid h-11 w-11 place-items-center rounded-full border border-starGold/25 bg-[#403474]/75 text-lg font-black text-starCream transition hover:bg-[#f5b06f]"
            aria-label="上一页"
            onClick={() => goToSlide(-1)}
          >
            ‹
          </button>
          <div className="h-2 w-[min(36vw,420px)] overflow-hidden rounded-full bg-starMist/15">
            <div
              className="h-full rounded-full bg-[linear-gradient(90deg,#f0a875,#ffd28a)] shadow-[0_0_18px_rgba(255,210,138,.52)] transition-[width] duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <button
            type="button"
            className="grid h-11 w-11 place-items-center rounded-full border border-starGold/25 bg-[#403474]/75 text-lg font-black text-starCream transition hover:bg-[#f5b06f]"
            aria-label="下一页"
            onClick={() => goToSlide(1)}
          >
            ›
          </button>
          <div className="min-w-[58px] text-center text-xs font-black text-starCream/80">
            {currentSlide + 1} / {ROADSHOW_SLIDES.length}
          </div>
        </div>
        <p className="absolute bottom-7 right-6 hidden text-xs font-bold text-starMist/45 md:block">
          使用 ← → 或空格翻页
        </p>
      </main>
    </StarShell>
  );
}

function CardGrid({ cards }: { cards: RoadshowCard[] }) {
  const columnClass =
    cards.length === 2 ? "md:grid-cols-2" : cards.length === 3 ? "md:grid-cols-3" : "";

  return (
    <div className={`grid w-full gap-3 ${columnClass}`}>
      {cards.map((card) => (
        <div
          key={card.title}
          className={`min-h-[118px] min-w-0 overflow-hidden rounded-[20px] border border-starGold/15 p-5 shadow-[0_18px_52px_rgba(0,0,0,.22)] ${
            card.gold
              ? "bg-[radial-gradient(circle_at_20%_0%,rgba(255,210,138,.22),transparent_38%),linear-gradient(145deg,rgba(62,48,112,.78),rgba(24,28,78,.68))]"
              : "bg-[linear-gradient(145deg,rgba(62,48,112,.74),rgba(24,28,78,.66))]"
          }`}
        >
          <h2 className="text-[clamp(0.95rem,1.12vw,1.125rem)] font-bold leading-snug text-starCream">
            {card.title}
          </h2>
          {card.text ? (
            <p className="mt-2 text-[clamp(0.82rem,1.05vw,1.05rem)] font-semibold leading-[1.55] text-starMist/72">
              {card.text}
            </p>
          ) : null}
          {card.items ? (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-[clamp(0.82rem,1.05vw,1.05rem)] font-semibold leading-[1.55] text-starMist/72">
              {card.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
          {card.pills ? <PillRow pills={card.pills} className="mt-4" /> : null}
        </div>
      ))}
    </div>
  );
}

function Timeline({ steps }: { steps: RoadshowStep[] }) {
  return (
    <div className="grid w-full gap-3 md:grid-cols-3">
      {steps.map((step) => (
        <div
          key={step.number}
          className="min-h-[226px] min-w-0 rounded-[22px] border border-starGold/15 bg-[#403474]/60 p-5"
        >
          <div className="mb-5 grid h-12 w-12 place-items-center rounded-full bg-[#f0a875] text-lg font-black text-[#fff7ea] shadow-[0_14px_42px_rgba(240,168,117,.36)]">
            {step.number}
          </div>
          <h2 className="text-[clamp(1rem,1.4vw,1.375rem)] font-bold leading-snug text-starCream">
            {step.title}
          </h2>
          <p className="mt-2 text-[clamp(0.82rem,1.05vw,1.05rem)] font-semibold leading-[1.55] text-starMist/72">
            {step.text}
          </p>
        </div>
      ))}
    </div>
  );
}

function PillRow({ pills, className = "" }: { pills: string[]; className?: string }) {
  return (
    <div className={`flex max-w-[980px] flex-wrap gap-3 ${className}`}>
      {pills.map((pill) => (
        <span
          key={pill}
          className="inline-flex min-h-[38px] items-center rounded-full border border-starGold/20 bg-[#0d123a]/55 px-4 text-[clamp(0.7rem,0.9vw,0.9rem)] font-black text-starCream/90 backdrop-blur"
        >
          {pill}
        </span>
      ))}
    </div>
  );
}
