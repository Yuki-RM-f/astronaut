"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { DemoEntry } from "@/src/components/DemoEntry";
import {
  GlassPanel,
  MemoryContainer,
  MemoryShell,
  MemoryTitle,
  PaperNote
} from "@/src/components/MemorySpace";
import { loginWithPassword } from "@/src/lib/auth";
import { ROUTES } from "@/src/lib/routes";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await loginWithPassword({ email, password });
      router.push(ROUTES.dashboard);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "登录失败。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <MemoryShell background="memoryStringLights">
      <MemoryContainer className="grid min-h-[calc(100vh-4.75rem)] gap-8 py-10 md:grid-cols-[0.95fr_1.05fr] md:items-center">
        <div>
          <MemoryTitle
            title="回到你的记忆空间"
            subtitle="已有账号可以继续整理私有人物；也可以不注册，直接进入外婆示例，把完整链路先走一遍。"
          />
          <PaperNote className="mt-8 max-w-md rotate-[-2deg]">
            <p className="font-serif text-lg leading-8 text-memoryText/80">
              写下 TA 的信息，
              <br />
              上传珍贵的资料，
              <br />
              我们会帮你用心解析，让陪伴更真实、更温暖。
            </p>
          </PaperNote>
        </div>

        <GlassPanel>
          <div className="grid gap-5">
            <div>
              <p className="text-sm font-semibold tracking-[0.08em] text-memoryAccent">
                先试试看
              </p>
              <h1 className="mt-3 font-serif text-3xl font-semibold text-memoryText">
                无需注册也可以进入完整示例
              </h1>
              <p className="mt-3 text-sm leading-7 text-memoryText/70">
                系统会自动创建本地演示会话，准备虚构人物「外婆」和已确认记忆，直接进入记忆空间。
              </p>
              <div className="mt-5">
                <DemoEntry label="立即体验示例" />
              </div>
            </div>

            <div className="h-px bg-memoryLine/70" />

            <form className="grid gap-4" aria-label="登录表单" onSubmit={handleSubmit}>
              <h2 className="font-serif text-2xl font-semibold text-memoryText">
                登录已有账号
              </h2>
              <label className="grid gap-2 text-sm font-semibold text-memoryText">
                邮箱
                <input
                  type="email"
                  name="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className={inputClass}
                />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-memoryText">
                密码
                <input
                  type="password"
                  name="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className={inputClass}
                />
              </label>
              {error ? (
                <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </p>
              ) : null}
              <button
                type="submit"
                disabled={isSubmitting}
                className="memory-button rounded-2xl bg-memoryAccent px-5 py-3 text-sm font-semibold text-white shadow-warm transition hover:bg-memoryAccentDark focus:outline-none focus:ring-4 focus:ring-memoryAccent/25 disabled:cursor-not-allowed disabled:bg-memoryText/30"
              >
                {isSubmitting ? "正在登录..." : "登录已有账号"}
              </button>
            </form>
            <p className="text-sm text-memoryText/68">
              还没有账号？{" "}
              <Link href={ROUTES.register} className="font-semibold text-memoryAccent">
                创建正式账号
              </Link>
            </p>
          </div>
        </GlassPanel>
      </MemoryContainer>
    </MemoryShell>
  );
}

const inputClass =
  "rounded-2xl border border-memoryLine/80 bg-white/72 px-4 py-3 text-sm text-memoryText outline-none transition focus:border-memoryAccent focus:ring-4 focus:ring-memoryAccent/20";
