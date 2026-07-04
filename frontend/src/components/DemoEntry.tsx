"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { startDemoSession } from "@/src/lib/auth";
import { ROUTES } from "@/src/lib/routes";

type DemoEntryProps = {
  label?: string;
  loadingLabel?: string;
  className?: string;
  errorClassName?: string;
};

export function DemoEntry({
  label = "无需注册，体验示例",
  loadingLabel = "正在准备外婆的记忆空间...",
  className = "memory-button inline-flex items-center justify-center rounded-2xl bg-memoryAccent px-5 py-3 text-sm font-semibold text-white shadow-warm transition hover:-translate-y-0.5 hover:bg-memoryAccentDark focus:outline-none focus:ring-4 focus:ring-memoryAccent/25 disabled:cursor-not-allowed disabled:bg-memoryText/30",
  errorClassName = "mt-3 text-sm text-red-700"
}: DemoEntryProps) {
  const router = useRouter();
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStart() {
    setError(null);
    setIsStarting(true);
    try {
      const session = await startDemoSession();
      router.push(ROUTES.personaDetail(session.demo_persona_id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法创建演示会话。");
    } finally {
      setIsStarting(false);
    }
  }

  return (
    <div>
      <button
        type="button"
        disabled={isStarting}
        onClick={handleStart}
        className={className}
      >
        {isStarting ? loadingLabel : label}
      </button>
      {error ? <p className={errorClassName}>{error}</p> : null}
    </div>
  );
}
