"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ComponentType, type ReactNode } from "react";
import { ChevronDown, Menu, Sparkles, Star, X } from "lucide-react";
import { MEMORY_SPACE_NAV_ITEMS } from "@/src/lib/memory-space";
import { ROUTES } from "@/src/lib/routes";

export function StarShell({
  children,
  className = "",
  hero = false
}: {
  children: ReactNode;
  className?: string;
  hero?: boolean;
}) {
  return (
    <div className={`star-shell ${hero ? "star-shell-hero" : ""} ${className}`}>
      <div className="star-field" aria-hidden="true" />
      <div className="relative z-10 min-h-screen">{children}</div>
    </div>
  );
}

export function StarNav({ floating = false }: { floating?: boolean }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const isActive = (href: string) =>
    pathname === href || (href !== ROUTES.home && pathname?.startsWith(`${href}/`));

  return (
    <header className={floating ? "absolute inset-x-0 top-0 z-30" : "relative z-30"}>
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-5 py-4 sm:px-8 md:gap-6 lg:px-10">
        <Link
          href={ROUTES.home}
          className="flex shrink-0 items-center gap-3 text-starCream"
          onClick={() => setMenuOpen(false)}
        >
          <span className="grid h-9 w-9 place-items-center rounded-full bg-starGold/15 text-starGold shadow-[0_0_24px_rgba(255,205,123,0.35)]">
            <Star className="h-6 w-6 fill-current" />
          </span>
          <span className="text-2xl font-bold tracking-wide">星记</span>
        </Link>

        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-starGold/18 bg-indigo-950/52 text-starCream md:hidden"
          aria-label={menuOpen ? "关闭导航" : "打开导航"}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((current) => !current)}
        >
          {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>

        <nav className="hidden items-center gap-6 text-sm font-semibold text-starMist/78 md:flex">
          {MEMORY_SPACE_NAV_ITEMS.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.label}
                aria-current={active ? "page" : undefined}
                className={`shrink-0 rounded-full border px-3 py-2 transition ${
                  active
                    ? "border-starGold/28 bg-starGold/14 text-starGold"
                    : "border-transparent hover:border-starGold/18 hover:text-starGold"
                }`}
                href={item.href}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="hidden h-10 w-10 md:block" aria-hidden="true" />
      </div>
      {menuOpen ? (
        <nav className="mx-5 mb-4 grid gap-2 rounded-[1.5rem] border border-white/10 bg-indigo-950/88 p-3 text-sm font-semibold text-starMist/78 shadow-[0_20px_60px_rgba(0,0,0,0.32)] backdrop-blur md:hidden">
          {MEMORY_SPACE_NAV_ITEMS.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.label}
                aria-current={active ? "page" : undefined}
                className={`rounded-2xl border px-4 py-3 transition ${
                  active
                    ? "border-starGold/28 bg-starGold/14 text-starGold"
                    : "border-transparent bg-white/5 hover:border-starGold/18 hover:text-starGold"
                }`}
                href={item.href}
                onClick={() => setMenuOpen(false)}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      ) : null}
    </header>
  );
}

export function StarPanel({
  children,
  className = ""
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={`star-panel ${className}`}>{children}</section>;
}

export function StarButton({
  children,
  className = "",
  type = "button",
  disabled = false,
  onClick
}: {
  children: ReactNode;
  className?: string;
  type?: "button" | "submit";
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`star-button ${className}`}
    >
      {children}
    </button>
  );
}

export function StarInput({
  label,
  children,
  className = ""
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={`grid gap-2 text-sm font-semibold text-starMist/78 ${className}`}>
      {label}
      {children}
    </label>
  );
}

export function FeatureTile({
  icon: Icon,
  title,
  text,
  accent = ""
}: {
  icon: ComponentType<{ className?: string }>;
  title: string;
  text: string;
  accent?: string;
}) {
  return (
    <div className="star-tile">
      <span className={`grid h-14 w-14 place-items-center rounded-2xl bg-violet-400/18 text-violet-200 shadow-[0_0_28px_rgba(181,128,255,0.32)] ${accent}`}>
        <Icon className="h-8 w-8" />
      </span>
      <div>
        <h3 className="text-lg font-bold text-starCream">{title}</h3>
        <p className="mt-1 text-sm leading-6 text-starMist/62">{text}</p>
      </div>
    </div>
  );
}

export function PageTitle({
  title,
  subtitle,
  className = ""
}: {
  title: string;
  subtitle?: string;
  className?: string;
}) {
  return (
    <div className={`text-center ${className}`}>
      <h1 className="font-serif text-4xl font-bold leading-tight text-starGold sm:text-5xl">
        {title}
      </h1>
      {subtitle ? (
        <p className="mx-auto mt-4 max-w-3xl text-sm font-semibold leading-7 text-starMist/66">
          {subtitle}
        </p>
      ) : null}
    </div>
  );
}

export function PlanetStar({ className = "" }: { className?: string }) {
  return (
    <div className={`planet-star ${className}`} aria-hidden="true">
      <div className="planet-star-ring" />
      <Star className="h-20 w-20 fill-current text-starGold" />
    </div>
  );
}

export function DownCue() {
  return (
    <div className="absolute bottom-5 left-1/2 -translate-x-1/2 text-starMist/72">
      <ChevronDown className="h-7 w-7 animate-bounce" />
    </div>
  );
}

export function TwinkleLabel({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 text-starGold">
      {children}
      <Sparkles className="h-4 w-4" />
    </span>
  );
}
