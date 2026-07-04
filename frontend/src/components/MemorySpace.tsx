import Link from "next/link";
import Image from "next/image";
import type { CSSProperties, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {
  ChevronRight,
  Heart,
  HeartHandshake,
  ShieldCheck,
  Sparkles
} from "lucide-react";
import {
  MEMORY_JOURNEY_STEPS,
  MEMORY_SPACE_ASSETS,
  MEMORY_SPACE_COPY
} from "@/src/lib/memory-space";

type AssetKey = keyof typeof MEMORY_SPACE_ASSETS;

function cx(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

export function MemoryShell({
  children,
  background = "grandmotherTea",
  className
}: {
  children: ReactNode;
  background?: AssetKey;
  className?: string;
}) {
  const asset = MEMORY_SPACE_ASSETS[background];
  const style = {
    "--memory-bg": `url(${asset.src})`
  } as CSSProperties;

  return (
    <div
      className={cx(
        "memory-shell relative min-h-[calc(100vh-4.75rem)] overflow-hidden",
        className
      )}
      style={style}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_18%,rgba(255,244,229,0.78),transparent_30%),linear-gradient(90deg,rgba(255,251,244,0.95)_0%,rgba(255,248,238,0.78)_42%,rgba(95,44,23,0.08)_100%)]" />
      <div className="pointer-events-none absolute -left-20 top-32 h-72 w-72 rounded-full bg-memoryGlow/50 blur-3xl" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-96 w-96 rounded-full bg-memorySun/25 blur-3xl" />
      <div className="relative z-10">{children}</div>
    </div>
  );
}

export function MemoryContainer({
  children,
  className
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cx("mx-auto w-full max-w-7xl px-5 py-8 sm:px-8 lg:px-10", className)}>
      {children}
    </div>
  );
}

export function GlassPanel({
  children,
  className
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cx("memory-glass rounded-[2rem] border border-white/65 p-5 shadow-memory", className)}>
      {children}
    </section>
  );
}

export function PaperNote({
  children,
  className
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cx("paper-note relative rounded-2xl border border-memoryLine/60 bg-memoryPaper/92 p-5 text-memoryText shadow-soft", className)}>
      <span className="absolute -top-3 left-10 h-6 w-16 rotate-[-8deg] rounded-sm bg-[#e7caa0]/70" />
      {children}
    </div>
  );
}

export function PageKicker({ children }: { children: ReactNode }) {
  return (
    <p className="inline-flex items-center gap-2 text-sm font-semibold tracking-[0.08em] text-memoryAccent">
      <Sparkles className="h-4 w-4" aria-hidden="true" />
      {children}
    </p>
  );
}

export function MemoryTitle({
  title,
  subtitle,
  children,
  className
}: {
  title: string;
  subtitle?: string;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <header className={cx("max-w-3xl", className)}>
      <PageKicker>{MEMORY_SPACE_COPY.spaceName}</PageKicker>
      <h1 className="mt-4 font-serif text-4xl font-semibold leading-tight text-memoryText sm:text-5xl lg:text-6xl">
        {title}
      </h1>
      {subtitle ? (
        <p className="mt-5 max-w-2xl text-base leading-8 text-memoryText/76">{subtitle}</p>
      ) : null}
      {children}
    </header>
  );
}

export function AiReminder({ text = MEMORY_SPACE_COPY.aiReminder }: { text?: string }) {
  return (
    <div className="inline-flex max-w-full items-center gap-2 rounded-full border border-memoryLine/70 bg-white/68 px-4 py-2 text-xs font-medium text-memoryText/72 shadow-soft backdrop-blur">
      <ShieldCheck className="h-4 w-4 shrink-0 text-memoryAccent" aria-hidden="true" />
      <span>{text}</span>
    </div>
  );
}

export function PrimaryMemoryLink({
  href,
  children,
  className
}: {
  href: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cx(
        "memory-button inline-flex items-center justify-center gap-2 rounded-2xl bg-memoryAccent px-5 py-3 text-sm font-semibold text-white shadow-warm transition hover:-translate-y-0.5 hover:bg-memoryAccentDark focus:outline-none focus:ring-4 focus:ring-memoryAccent/25",
        className
      )}
    >
      {children}
      <ChevronRight className="h-4 w-4" aria-hidden="true" />
    </Link>
  );
}

export function SecondaryMemoryLink({
  href,
  children,
  className
}: {
  href: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-2xl border border-memoryLine/80 bg-white/72 px-5 py-3 text-sm font-semibold text-memoryText shadow-soft backdrop-blur transition hover:-translate-y-0.5 hover:border-memoryAccent/45 hover:text-memoryAccent focus:outline-none focus:ring-4 focus:ring-memoryAccent/20",
        className
      )}
    >
      {children}
    </Link>
  );
}

export function StepRibbon({
  activeIndex = 0,
  className
}: {
  activeIndex?: number;
  className?: string;
}) {
  return (
    <GlassPanel className={cx("px-4 py-4", className)}>
      <ol className="grid gap-3 md:grid-cols-4">
        {MEMORY_JOURNEY_STEPS.map((step, index) => (
          <li key={step.title} className="flex items-center gap-3">
            <span
              className={cx(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-full border text-sm font-semibold shadow-soft",
                index <= activeIndex
                  ? "border-memoryAccent bg-memoryAccent text-white"
                  : "border-memoryLine bg-white/72 text-memoryText/60"
              )}
            >
              {index + 1}
            </span>
            <div>
              <p className="text-sm font-semibold text-memoryText">{step.title}</p>
              <p className="mt-0.5 hidden text-xs leading-5 text-memoryText/60 lg:block">
                {step.description}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </GlassPanel>
  );
}

export function MemoryActionCard({
  href,
  title,
  text,
  icon: Icon,
  primary = false
}: {
  href: string;
  title: string;
  text: string;
  icon: LucideIcon;
  primary?: boolean;
}) {
  return (
    <Link
      href={href}
      className={cx(
        "memory-card group flex min-h-36 flex-col justify-between rounded-3xl border p-5 shadow-soft transition hover:-translate-y-1 hover:shadow-warm focus:outline-none focus:ring-4 focus:ring-memoryAccent/20",
        primary
          ? "border-memoryAccent/40 bg-memoryAccent text-white"
          : "border-white/70 bg-white/72 text-memoryText backdrop-blur"
      )}
    >
      <span
        className={cx(
          "flex h-12 w-12 items-center justify-center rounded-2xl",
          primary ? "bg-white/18 text-white" : "bg-memoryWarm text-memoryAccent"
        )}
      >
        <Icon className="h-6 w-6" aria-hidden="true" />
      </span>
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className={cx("mt-2 text-sm leading-6", primary ? "text-white/82" : "text-memoryText/68")}>
          {text}
        </p>
      </div>
    </Link>
  );
}

export function TrustBadge({
  score,
  label,
  className
}: {
  score: number;
  label: string;
  className?: string;
}) {
  return (
    <div className={cx("rounded-3xl border border-white/70 bg-white/76 px-5 py-4 text-memoryText shadow-soft backdrop-blur", className)}>
      <p className="text-sm font-semibold text-memoryText/62">记忆可信度</p>
      <div className="mt-1 flex items-end gap-2">
        <span className="font-serif text-5xl font-semibold leading-none text-memoryAccent">
          {score}
        </span>
        <span className="pb-1 text-xl font-semibold text-memoryAccent">%</span>
      </div>
      <p className="mt-1 text-sm font-medium text-memoryText/68">{label}</p>
    </div>
  );
}

export function PhotoStack({
  primary = "grandmotherTea",
  secondary = "familyAlbum",
  className
}: {
  primary?: AssetKey;
  secondary?: AssetKey;
  className?: string;
}) {
  const first = MEMORY_SPACE_ASSETS[primary];
  const second = MEMORY_SPACE_ASSETS[secondary];

  return (
    <div className={cx("relative min-h-72", className)}>
      <Image
        src={first.src}
        alt={first.alt}
        width={288}
        height={224}
        className="memory-float absolute right-0 top-4 h-56 w-72 rotate-3 rounded-[1.75rem] border-4 border-white/85 object-cover shadow-memory"
      />
      <Image
        src={second.src}
        alt={second.alt}
        width={224}
        height={160}
        className="memory-float-delayed absolute bottom-0 left-4 h-40 w-56 -rotate-6 rounded-[1.4rem] border-4 border-white/85 object-cover shadow-memory"
      />
      <PaperNote className="absolute left-0 top-20 max-w-64 rotate-[-4deg]">
        <p className="font-serif text-lg leading-8">
          愿你被世界温柔以待，
          <br />
          要记得常回家看看。
        </p>
      </PaperNote>
    </div>
  );
}

export function VoiceWave({ label = "奶奶的声音" }: { label?: string }) {
  return (
    <div className="memory-float inline-flex items-center gap-3 rounded-2xl border border-white/75 bg-white/72 px-4 py-3 text-memoryText shadow-soft backdrop-blur">
      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-memoryAccent text-white">
        <Heart className="h-4 w-4 fill-current" aria-hidden="true" />
      </span>
      <span className="text-sm font-semibold">{label}</span>
      <span className="flex h-8 items-center gap-1" aria-hidden="true">
        {[12, 20, 16, 28, 18, 24, 14, 22, 12].map((height, index) => (
          <span
            key={`${height}-${index}`}
            className="w-1 rounded-full bg-memoryAccent/70"
            style={{ height }}
          />
        ))}
      </span>
      <span className="text-xs text-memoryText/50">00:28</span>
    </div>
  );
}

export function MemoryLogo({ className }: { className?: string }) {
  return (
    <span className={cx("inline-flex items-center gap-3 font-serif text-xl font-semibold text-memoryText", className)}>
      <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-memoryWarm text-memoryAccent shadow-soft">
        <HeartHandshake className="h-6 w-6" aria-hidden="true" />
      </span>
      {MEMORY_SPACE_COPY.productName}
    </span>
  );
}

export function StatPill({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-memoryLine/70 bg-white/62 px-4 py-3 shadow-soft backdrop-blur">
      <p className="text-xs font-semibold tracking-[0.08em] text-memoryText/48">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-memoryText">{value}</p>
    </div>
  );
}
