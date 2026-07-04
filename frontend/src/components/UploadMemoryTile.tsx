"use client";

import type { LucideIcon } from "lucide-react";

export function UploadMemoryTile({
  kind,
  label,
  icon: Icon,
  count,
  accept,
  onPick
}: {
  kind: string;
  label: string;
  icon: LucideIcon;
  count: number;
  accept: string;
  onPick: (files: File[]) => void;
}) {
  return (
    <label className="grid min-h-[8.6rem] cursor-pointer place-items-center rounded-2xl border border-dashed border-starGold/20 bg-indigo-950/18 p-5 text-center transition hover:border-starGold/50 hover:bg-indigo-900/24">
      <input
        type="file"
        accept={accept}
        multiple
        className="sr-only"
        onChange={(event) => onPick(Array.from(event.target.files ?? []))}
      />
      <span className="grid h-14 w-14 place-items-center rounded-2xl bg-violet-400/22 text-violet-200 shadow-[0_0_30px_rgba(181,128,255,0.35)]">
        <Icon className="h-8 w-8" />
      </span>
      <span className="mt-3 block text-lg font-bold text-starCream">{kind}</span>
      <span className="block text-sm font-semibold text-starMist/52">
        {count > 0 ? `已选择 ${count} 个文件` : label}
      </span>
    </label>
  );
}
