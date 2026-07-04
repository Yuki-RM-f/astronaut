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
import { registerAccount } from "@/src/lib/auth";
import { ROUTES } from "@/src/lib/routes";

export default function RegisterPage() {
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await registerAccount({
        display_name: displayName.trim() || undefined,
        email,
        password
      });
      router.push(ROUTES.dashboard);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "注册失败。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <MemoryShell background="familyAlbum">
      <MemoryContainer className="grid min-h-[calc(100vh-4.75rem)] gap-8 py-10 md:grid-cols-[0.95fr_1.05fr] md:items-center">
        <div>
          <MemoryTitle
            title="创建你的私有记忆空间"
            subtitle="正式账号会保留你创建的人物、资料、记忆审计和后续对话。暂时不想填写信息时，可以直接体验示例。"
          />
          <PaperNote className="mt-8 max-w-md rotate-[2deg]">
            <p className="font-serif text-lg leading-8 text-memoryText/80">
              每一份资料，
              <br />
              都是爱的延续。
              <br />
              先把真实来源留下，再让 TA 温柔开口。
            </p>
          </PaperNote>
        </div>

        <GlassPanel>
          <div className="grid gap-5">
            <div>
              <p className="text-sm font-semibold tracking-[0.08em] text-memoryAccent">
                不想填写信息？
              </p>
              <h1 className="mt-3 font-serif text-3xl font-semibold text-memoryText">
                一键进入外婆示例
              </h1>
              <p className="mt-3 text-sm leading-7 text-memoryText/70">
                演示账号仅用于本地体验，不要求邮箱和密码。你可以先走完整链路，再决定是否创建正式账号。
              </p>
              <div className="mt-5">
                <DemoEntry label="立即体验示例" />
              </div>
            </div>

            <div className="h-px bg-memoryLine/70" />

            <form className="grid gap-4" aria-label="注册表单" onSubmit={handleSubmit}>
              <h2 className="font-serif text-2xl font-semibold text-memoryText">
                创建正式账号
              </h2>
              <label className="grid gap-2 text-sm font-semibold text-memoryText">
                昵称
                <input
                  type="text"
                  name="display_name"
                  autoComplete="name"
                  placeholder="可选"
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  className={inputClass}
                />
              </label>
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
                  autoComplete="new-password"
                  minLength={6}
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
                {isSubmitting ? "正在创建..." : "创建正式账号"}
              </button>
            </form>
            <p className="text-sm text-memoryText/68">
              已经有账号？{" "}
              <Link href={ROUTES.login} className="font-semibold text-memoryAccent">
                登录已有账号
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
