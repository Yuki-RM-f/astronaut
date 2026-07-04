"use client";

import Link from "next/link";
import { BookOpenText, Heart, MessageCircle, ShieldCheck, UploadCloud } from "lucide-react";
import { DemoEntry } from "@/src/components/DemoEntry";
import {
  AiReminder,
  GlassPanel,
  MemoryActionCard,
  MemoryContainer,
  MemoryShell,
  MemoryTitle,
  PhotoStack,
  SecondaryMemoryLink,
  StatPill,
  StepRibbon,
  VoiceWave
} from "@/src/components/MemorySpace";
import { MEMORY_SPACE_ACTIONS } from "@/src/lib/memory-space";
import { ROUTES } from "@/src/lib/routes";

export default function HomePage() {
  return (
    <MemoryShell background="grandmotherTea">
      <MemoryContainer className="grid min-h-[calc(100vh-4.75rem)] content-between gap-8 py-8 lg:py-10">
        <section className="grid gap-8 lg:grid-cols-[0.92fr_1.08fr] lg:items-center">
          <div className="max-w-2xl">
            <MemoryTitle
              title="把珍贵回忆，变成可对话的陪伴"
              subtitle="那些没来得及说的话，现在可以继续说给 TA 听。上传文字、照片、声音和视频，基于珍贵回忆与真实情感，为你创建一个值得信赖、独一无二的数字陪伴者。"
            >
              <div className="mt-6">
                <AiReminder />
              </div>
            </MemoryTitle>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <DemoEntry label="立即体验示例" />
              <SecondaryMemoryLink href={ROUTES.login}>登录已有账号</SecondaryMemoryLink>
            </div>
            <p className="mt-4 max-w-xl text-sm leading-7 text-memoryText/64">
              演示会自动创建本地临时用户和虚构人物「外婆」，不需要邮箱或密码。
            </p>
          </div>

          <div className="relative min-h-[28rem]">
            <div className="absolute left-3 top-3 z-10 rotate-[-6deg]">
              <VoiceWave label="外婆的声音" />
            </div>
            <PhotoStack
              primary="grandmotherTea"
              secondary="familyLivingRoom"
              className="mx-auto max-w-xl"
            />
            <GlassPanel className="absolute bottom-4 right-0 max-w-xs p-4">
              <p className="text-sm leading-6 text-memoryText/78">
                宝贝，今天过得好吗？记得按时吃饭，照顾好自己哦。
              </p>
              <div className="mt-3 flex gap-1.5">
                <span className="h-2 w-2 rounded-full bg-white" />
                <span className="h-2 w-2 rounded-full bg-memoryAccent" />
                <span className="h-2 w-2 rounded-full bg-white" />
              </div>
            </GlassPanel>
          </div>
        </section>

        <StepRibbon activeIndex={0} />

        <section className="grid gap-4 md:grid-cols-3">
          <StatPill label="资料来源" value="可追溯" />
          <StatPill label="记忆状态" value="可审核" />
          <StatPill label="当前能力" value="Mock" />
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <MemoryActionCard
            href={ROUTES.personasNew}
            title="创建人物"
            text="先写下关系、称呼、说话风格和边界。"
            icon={Heart}
          />
          <MemoryActionCard
            href={ROUTES.dashboard}
            title={MEMORY_SPACE_ACTIONS.upload.title}
            text="把故事、照片和声音放进一个可整理的空间。"
            icon={UploadCloud}
          />
          <MemoryActionCard
            href={ROUTES.login}
            title="可信记忆"
            text="确认来源后，才让记忆进入后续对话。"
            icon={ShieldCheck}
          />
        </section>

        <section className="grid gap-4 pb-3 md:grid-cols-2">
          <GlassPanel>
            <div className="flex items-start gap-4">
              <BookOpenText className="mt-1 h-6 w-6 shrink-0 text-memoryAccent" />
              <div>
                <h2 className="text-lg font-semibold text-memoryText">来源可见</h2>
                <p className="mt-2 text-sm leading-7 text-memoryText/68">
                  每条回复都尽量回到资料、记忆和人格档案，避免无依据地自由发挥。
                </p>
              </div>
            </div>
          </GlassPanel>
          <GlassPanel>
            <div className="flex items-start gap-4">
              <MessageCircle className="mt-1 h-6 w-6 shrink-0 text-memoryAccent" />
              <div>
                <h2 className="text-lg font-semibold text-memoryText">边界清楚</h2>
                <p className="mt-2 text-sm leading-7 text-memoryText/68">
                  当前仍是 deterministic mock provider，不伪装真实 OCR、ASR、LLM、音色或 3D 能力。
                </p>
              </div>
            </div>
          </GlassPanel>
        </section>
      </MemoryContainer>
    </MemoryShell>
  );
}
