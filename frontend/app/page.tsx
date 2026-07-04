"use client";

import Link from "next/link";
import { Sparkles } from "lucide-react";
import { StarNav, StarShell } from "@/src/components/StarSite";
import { StarPlanetScene } from "@/src/components/StarPlanetScene";
import { ROUTES } from "@/src/lib/routes";

export default function HomePage() {
  return (
    <StarShell hero className="star-home-shell">
      <StarPlanetScene />
      <StarNav floating />
      <main className="relative z-10 flex min-h-screen w-full items-end justify-center px-6 pb-14 pt-28 sm:px-10 md:pb-16">
        <section className="star-hero-copy mx-auto flex w-full max-w-md flex-col items-center text-center">
          <h1 className="font-serif text-[clamp(1.5rem,3.6vw,2.65rem)] font-bold leading-[1.24] text-starCream drop-shadow-[0_4px_22px_rgba(0,0,0,0.42)]">
            每一颗星，
            <br />
            都是爱与记忆的光。
          </h1>

          <Link
            href={ROUTES.personasNew}
            className="star-button star-cta mt-5 w-full max-w-[15.5rem] text-sm sm:text-base"
          >
            创建属于TA的星星
            <Sparkles className="ml-3 h-5 w-5" />
          </Link>
        </section>
      </main>
    </StarShell>
  );
}
