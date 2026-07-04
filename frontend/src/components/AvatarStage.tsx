"use client";

import { Sparkles, Star } from "lucide-react";
import { AvatarPreview } from "@/src/components/AvatarPreview";
import type { AvatarDisplaySource } from "@/src/lib/avatar";

function joinClassNames(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

function safeBackgroundUrl(value: string): string {
  return `url("${value.replaceAll('"', "%22")}")`;
}

export function AvatarStage({
  personaName,
  source,
  mouthActive = false,
  subtitle,
  className = ""
}: {
  personaName: string;
  source: AvatarDisplaySource;
  mouthActive?: boolean;
  subtitle?: string;
  className?: string;
}) {
  return (
    <aside
      className={joinClassNames(
        "relative min-h-[32rem] overflow-hidden rounded-[2rem] border border-starGold/16 bg-indigo-950/24 shadow-[0_24px_72px_rgba(0,0,0,0.34)] backdrop-blur",
        className
      )}
    >
      <div className="absolute inset-0 bg-[url('/memory-space/family-living-room.jpg')] bg-cover bg-center opacity-[0.18]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_62%_24%,rgba(255,191,108,0.34),transparent_21rem),linear-gradient(90deg,rgba(9,12,42,0.08),rgba(9,12,42,0.82))]" />
      <div className="absolute right-[7%] top-[8%] h-56 w-56 rounded-full border border-starGold/22 bg-starGold/8 shadow-[0_0_90px_rgba(255,190,109,0.22)]" />

      <div className="relative flex h-full min-h-[32rem] flex-col justify-between gap-6 p-5">
        <div className="min-h-[23rem]">
          {source.kind === "model" ? (
            <AvatarPreview
              model={source.model}
              mouthActive={mouthActive}
              className="min-h-[24rem] border-0 bg-transparent shadow-none"
              canvasClassName="h-[24rem]"
            />
          ) : null}

          {source.kind === "preview" ? (
            <div
              className="min-h-[24rem] rounded-[1.5rem] bg-cover bg-center shadow-[inset_0_-90px_90px_rgba(9,12,42,0.42)]"
              style={{ backgroundImage: safeBackgroundUrl(source.previewImageUrl) }}
              aria-label={`${personaName}的数字人预览`}
            />
          ) : null}

          {source.kind === "placeholder" ? (
            <div className="star-avatar-placeholder" aria-label={`${personaName}的数字人占位`}>
              <div className="star-companion-portrait" aria-hidden="true">
                <div className="star-companion-orbit" />
                <div className="star-companion-face" />
                <div className="star-companion-body" />
              </div>
            </div>
          ) : null}
        </div>

        <div className="relative rounded-3xl border border-white/10 bg-black/18 p-4">
          <p className="inline-flex items-center gap-2 text-sm font-bold text-starGold">
            <Star className="h-4 w-4 fill-current" aria-hidden="true" />
            {source.kind === "placeholder" ? "默认星空形象" : "已连接数字人形象"}
          </p>
          <h2 className="mt-2 font-serif text-3xl font-bold text-starGold">{personaName}</h2>
          <p className="mt-3 text-sm font-semibold leading-7 text-starMist/72">
            {subtitle || "数字人形象会在生成或选择后出现在这里，继续陪你对话。"}
          </p>
          <p className="mt-3 inline-flex items-center gap-2 rounded-full bg-starGold/12 px-3 py-1 text-xs font-bold text-starCream">
            <Sparkles className="h-3.5 w-3.5 text-starGold" aria-hidden="true" />
            AI 模拟形象
          </p>
        </div>
      </div>
    </aside>
  );
}
