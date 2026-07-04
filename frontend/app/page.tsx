"use client";

import Link from "next/link";
import {
  Archive,
  MessageCircle,
  ScrollText,
  Sparkles,
  UploadCloud,
  UserRound
} from "lucide-react";
import { FeatureTile, StarNav, StarPanel, StarShell } from "@/src/components/StarSite";
import { StarPlanetScene } from "@/src/components/StarPlanetScene";
import { ROUTES } from "@/src/lib/routes";

export default function HomePage() {
  return (
    <StarShell hero className="star-home-shell">
      <StarPlanetScene />
      <StarNav floating />
      <main className="relative z-10">
        <section className="flex min-h-screen w-full items-center justify-center px-6 pb-14 pt-32 sm:px-10 md:pb-16 md:pt-28">
          <div className="star-hero-copy mx-auto flex w-full max-w-md flex-col items-center text-center">
            <h1 className="font-serif text-[clamp(1.5rem,3.6vw,2.65rem)] font-bold leading-[1.24] text-starCream drop-shadow-[0_4px_22px_rgba(0,0,0,0.42)]">
              每一颗星，
              <br />
              都是爱与记忆的光。
            </h1>

            <div className="home-hero-actions">
              <Link
                href={ROUTES.personasNew}
                className="star-button star-cta home-hero-action"
              >
                创建属于TA的星星
                <Sparkles className="h-5 w-5" aria-hidden="true" />
              </Link>
              <Link
                href={ROUTES.dashboard}
                className="star-button star-cta home-hero-action"
              >
                进入我的星空
                <ScrollText className="h-5 w-5" aria-hidden="true" />
              </Link>
            </div>
          </div>
        </section>

        <section
          id="product-intro"
          className="mx-auto grid w-full max-w-7xl scroll-mt-28 gap-5 px-6 py-12 sm:px-10 lg:grid-cols-[1fr_0.85fr] lg:items-stretch"
        >
          <StarPanel className="p-6 sm:p-8">
            <p className="text-sm font-bold text-starGold">产品介绍</p>
            <h2 className="mt-3 font-serif text-3xl font-bold leading-tight text-starCream sm:text-4xl">
              把重要的人，整理成可信的星光档案。
            </h2>
            <p className="mt-5 text-sm font-semibold leading-7 text-starMist/72">
              星记围绕人物档案、资料解析与审核、回忆讲述和第一人称互动建立闭环。每一段对话和故事都尽量回到已确认的资料来源。
            </p>
          </StarPanel>

          <div className="grid gap-4">
            <FeatureTile
              icon={UserRound}
              title="创建档案"
              text="写下 TA 的身份、关系、称呼和基础资料，形成后续对话的人格边界。"
            />
            <FeatureTile
              icon={UploadCloud}
              title="补充资料"
              text="上传文字、照片、声音和视频，让分散的记忆进入同一片星空。"
              accent="bg-starGold/16 text-starGold"
            />
            <FeatureTile
              icon={MessageCircle}
              title="开启陪伴"
              text="在审核后的记忆和档案摘要基础上，进行文字、语音和 3D 数字人互动。"
              accent="bg-indigo-300/16 text-indigo-100"
            />
          </div>
        </section>

        <section
          id="memory-review"
          className="mx-auto grid w-full max-w-7xl scroll-mt-28 gap-5 px-6 py-12 sm:px-10 lg:grid-cols-[1fr_0.85fr] lg:items-stretch"
        >
          <StarPanel className="p-6 sm:p-8">
            <p className="text-sm font-bold text-starGold">资料解析与审核</p>
            <h2 className="mt-3 font-serif text-3xl font-bold leading-tight text-starCream sm:text-4xl">
              先确认，再让 TA 记住。
            </h2>
            <p className="mt-5 text-sm font-semibold leading-7 text-starMist/72">
              上传资料后，在资料页面审查解析出的记忆卡片，确认、修正或删除后再进入后续互动。
            </p>
          </StarPanel>

          <div className="grid gap-4">
            <FeatureTile
              icon={ScrollText}
              title="来源可追溯"
              text="每条记忆保留资料来源、摘录和置信度，方便用户判断是否可信。"
            />
            <FeatureTile
              icon={Archive}
              title="档案会更新"
              text="审核结果会影响档案摘要和后续对话使用的长期记忆；回忆讲述与搜索保留在记忆档案馆。"
              accent="bg-starGold/16 text-starGold"
            />
          </div>
        </section>
      </main>
    </StarShell>
  );
}
