"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { ROUTES } from "@/src/lib/routes";

export function PersonaBackLink({ personaId }: { personaId: string }) {
  return (
    <Link
      href={ROUTES.personaDetail(personaId)}
      className="inline-flex items-center gap-2 rounded-full border border-starGold/18 bg-indigo-950/44 px-4 py-2 text-sm font-bold text-starGold transition hover:border-starGold/34 hover:bg-starGold/12"
    >
      <ArrowLeft className="h-4 w-4" aria-hidden="true" />
      返回人物总览
    </Link>
  );
}
