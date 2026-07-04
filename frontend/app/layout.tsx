import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import "./globals.css";
import { MemoryLogo } from "@/src/components/MemorySpace";
import { MEMORY_SPACE_NAV_ITEMS } from "@/src/lib/memory-space";

export const metadata: Metadata = {
  title: "可信人格记忆 Agent",
  description: "用可追溯记忆构建温暖、可信的记忆空间。"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <div className="min-h-screen">
          <header className="sticky top-0 z-40 border-b border-memoryLine/60 bg-memoryCream/86 backdrop-blur-xl">
            <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-10">
              <Link href="/" aria-label="返回首页">
                <MemoryLogo />
              </Link>
              <nav aria-label="主导航" className="flex flex-wrap gap-2">
                {MEMORY_SPACE_NAV_ITEMS.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="rounded-full px-4 py-2 text-sm font-semibold text-memoryText/72 transition hover:bg-white/70 hover:text-memoryAccent focus:outline-none focus:ring-4 focus:ring-memoryAccent/20"
                  >
                    {item.label}
                  </Link>
                ))}
              </nav>
            </div>
          </header>
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
