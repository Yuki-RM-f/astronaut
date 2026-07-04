"use client";

import Link from "next/link";
import {
  Archive,
  FileCheck2,
  HeartHandshake,
  MessageCircle,
  Microscope,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  UserRound
} from "lucide-react";
import {
  FeatureTile,
  PageTitle,
  StarNav,
  StarPanel,
  StarShell,
  TwinkleLabel
} from "@/src/components/StarSite";
import { ROUTES } from "@/src/lib/routes";

const ROADSHOW_FLOW = ["创建星星", "上传回忆", "审核记忆", "开启互动"] as const;

const VALUE_POINTS = [
  {
    title: "分散的材料需要被整理",
    text: "聊天片段、照片、声音和视频先进入同一份人物档案，再被整理成可审核的记忆。"
  },
  {
    title: "情感陪伴需要有依据",
    text: "对话和回忆讲述尽量回到已确认资料，减少没有来源的想象式回应。"
  },
  {
    title: "长期维护需要可修正",
    text: "用户可以确认、编辑或删除记忆，让这颗星星随着新的资料持续变得清楚。"
  }
] as const;

const TRUST_MECHANISMS = [
  {
    title: "Memory Engine",
    text: "把单份资料识别文本整理为结构化记忆，再汇总成长期记忆 Markdown 和资料来源。"
  },
  {
    title: "Persona Engine",
    text: "把关系、称呼、表达习惯和已确认记忆沉淀为人格档案，约束第一人称回应。"
  },
  {
    title: "Memory Audit",
    text: "记录记忆确认、修正、删除、对话引用和搜索事件，让记忆变化可以追溯。"
  },
  {
    title: "Prompt 与检索策略",
    text: "对话优先使用已确认或已修正记忆；资料不足时温柔承认不确定。"
  }
] as const;

export default function ProductIntroPage() {
  return (
    <StarShell>
      <StarNav />
      <main className="mx-auto w-full max-w-7xl px-5 pb-14 sm:px-8 lg:px-10">
        <section className="grid gap-6 py-10 lg:grid-cols-[0.95fr_1.05fr] lg:items-stretch">
          <StarPanel className="flex flex-col justify-between p-6 sm:p-8">
            <div>
              <p className="text-sm font-bold text-starGold">产品介绍 · 展览路演材料</p>
              <h1 className="mt-3 font-serif text-4xl font-bold leading-tight text-starCream sm:text-5xl">
                让记忆不止于回忆。
              </h1>
              <p className="mt-5 max-w-2xl text-sm font-semibold leading-7 text-starMist/72">
                星记把重要的人整理成可看见、可听见、可对话、可追溯的星光档案。它不是把原始资料堆成聊天窗口，而是先建立来源、审核和边界，再开启互动。
              </p>
            </div>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href={ROUTES.personasNew} className="star-button gap-2">
                创建档案
                <Sparkles className="h-5 w-5" aria-hidden="true" />
              </Link>
              <Link href={ROUTES.dashboard} className="star-button gap-2">
                我的星空
                <Archive className="h-5 w-5" aria-hidden="true" />
              </Link>
            </div>
          </StarPanel>

          <StarPanel className="p-6 sm:p-8">
            <p className="text-sm font-bold text-starGold">演示闭环</p>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              {ROADSHOW_FLOW.map((step, index) => (
                <div
                  key={step}
                  className="rounded-2xl border border-starGold/14 bg-indigo-950/28 p-4 shadow-[0_12px_34px_rgba(0,0,0,0.18)]"
                >
                  <span className="text-xs font-black text-starGold/78">STEP {index + 1}</span>
                  <p className="mt-2 text-base font-bold text-starCream">{step}</p>
                </div>
              ))}
            </div>
            <p className="mt-5 text-sm font-semibold leading-7 text-starMist/66">
              当前 demo 已覆盖资料上传、记忆审核、文本/语音互动和 GLB 数字人展示；真实声音质量仍取决于本地 provider 配置与样本质量。
            </p>
          </StarPanel>
        </section>

        <section className="py-10">
          <PageTitle
            title="为什么需要这个产品"
            subtitle="路演材料中的核心问题被收束为三件事：资料分散、AI 回答需要可信依据、亲密记忆需要长期维护。"
          />
          <div className="mt-7 grid gap-4 md:grid-cols-3">
            {VALUE_POINTS.map((item) => (
              <StarPanel key={item.title} className="p-5">
                <h2 className="text-lg font-bold text-starCream">{item.title}</h2>
                <p className="mt-3 text-sm font-semibold leading-7 text-starMist/66">{item.text}</p>
              </StarPanel>
            ))}
          </div>
        </section>

        <section className="grid gap-5 py-10 lg:grid-cols-[0.82fr_1.18fr] lg:items-stretch">
          <StarPanel className="p-6 sm:p-8">
            <p className="text-sm font-bold text-starGold">我们提供什么</p>
            <h2 className="mt-3 font-serif text-3xl font-bold leading-tight text-starCream sm:text-4xl">
              一颗有边界、可追溯、能陪你慢慢说话的星星。
            </h2>
            <p className="mt-5 text-sm font-semibold leading-7 text-starMist/72">
              它可以承接想念、遗憾和共同回忆，也会清楚标注 AI 模拟边界。记忆属于用户，互动建立在用户确认过的资料之上。
            </p>
            <p className="mt-5 text-sm font-bold text-starGold">
              <TwinkleLabel>记忆属于你</TwinkleLabel>
            </p>
          </StarPanel>

          <div className="grid gap-4">
            <FeatureTile
              icon={UploadCloud}
              title="多模态资料"
              text="文字、照片、声音和视频进入同一份人物档案，先沉淀资料，再生成可审核记忆。"
              accent="bg-starGold/16 text-starGold"
            />
            <FeatureTile
              icon={UserRound}
              title="人格复刻/档案"
              text="关系、称呼、表达习惯和已确认资料一起进入人格档案，形成后续回应边界。"
            />
            <FeatureTile
              icon={ShieldCheck}
              title="可信追溯"
              text="每条记忆保留来源摘录和状态；用户确认、修正或删除后，再进入对话和回忆讲述。"
              accent="bg-starGold/16 text-starGold"
            />
            <FeatureTile
              icon={MessageCircle}
              title="有边界的对话"
              text="TA 使用第一人称和用户称呼，也会在资料不足时温柔承认不确定，不暗示本人复生。"
            />
            <FeatureTile
              icon={HeartHandshake}
              title="声音/3D demo 互动"
              text="当前页面链路支持语音播放、声音设置和 GLB 数字人展示，用于承接对话侧预览。"
              accent="bg-indigo-300/16 text-indigo-100"
            />
          </div>
        </section>

        <section className="py-10">
          <PageTitle
            title="核心能力"
            subtitle="从资料到人格、从人格到互动，每一步都围绕来源、审核和边界设计。"
          />
          <div className="mt-7 grid gap-4 md:grid-cols-2">
            <FeatureTile
              icon={FileCheck2}
              title="资料进入审核流"
              text="资料解析后生成结构化记忆，用户确认或修正后才进入长期记忆上下文。"
              accent="bg-starGold/16 text-starGold"
            />
            <FeatureTile
              icon={Microscope}
              title="来源进入回答依据"
              text="对话和故事优先引用已确认记忆，用户可以回看来源并纠正错误。"
            />
          </div>
        </section>

        <section className="py-10">
          <PageTitle
            title="技术与可信机制"
            subtitle="路演中的技术亮点被整理成当前项目已有或 mock 可演示的机制，不扩大为未验证承诺。"
          />
          <div className="mt-7 grid gap-4 md:grid-cols-2">
            {TRUST_MECHANISMS.map((item) => (
              <StarPanel key={item.title} className="p-5">
                <h2 className="text-lg font-bold text-starCream">{item.title}</h2>
                <p className="mt-3 text-sm font-semibold leading-7 text-starMist/66">{item.text}</p>
              </StarPanel>
            ))}
          </div>
        </section>
      </main>
    </StarShell>
  );
}
