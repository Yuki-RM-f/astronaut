"use client";

import { FormEvent, ReactNode, useEffect, useRef } from "react";
import { Mic2, Send } from "lucide-react";
import { StarButton, StarPanel } from "@/src/components/StarSite";

export function ConversationWorkspace({
  modeBar,
  children,
  composer,
  avatar,
  scrollKey,
  className = ""
}: {
  modeBar?: ReactNode;
  children: ReactNode;
  composer: ReactNode;
  avatar?: ReactNode;
  scrollKey?: string | number;
  className?: string;
}) {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const scrollContainer = scrollRef.current;
    if (!scrollContainer) {
      return;
    }
    scrollContainer.scrollTop = scrollContainer.scrollHeight;
  }, [scrollKey]);

  return (
    <div
      className={`grid items-stretch gap-5 xl:grid-cols-[minmax(0,0.66fr)_minmax(20rem,0.34fr)] ${className}`}
    >
      <StarPanel className="flex min-h-[37rem] flex-col overflow-hidden p-0 xl:h-full">
        {modeBar ? (
          <div className="shrink-0 border-b border-white/8 bg-indigo-950/24 p-3 sm:p-4">
            {modeBar}
          </div>
        ) : null}
        <div
          ref={scrollRef}
          className="conversation-scroll min-h-0 flex-1 overflow-y-auto p-4 sm:p-5"
        >
          {children}
        </div>
        <div className="sticky bottom-0 z-10 shrink-0 border-t border-white/8 bg-indigo-950/86 p-4 backdrop-blur sm:p-5">
          {composer}
        </div>
      </StarPanel>

      {avatar ? <div className="grid h-full">{avatar}</div> : null}
    </div>
  );
}

export function ChatComposer({
  value,
  onValueChange,
  onSubmit,
  placeholder,
  disabled = false,
  submitLabel,
  quickPrompts,
  rightAction
}: {
  value: string;
  onValueChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  placeholder: string;
  disabled?: boolean;
  submitLabel?: ReactNode;
  quickPrompts?: readonly string[];
  rightAction?: ReactNode;
}) {
  return (
    <form onSubmit={onSubmit} className="grid gap-3">
      {quickPrompts?.length ? (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {quickPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="shrink-0 rounded-full border border-sky-200/18 bg-sky-300/10 px-3 py-2 text-xs font-bold text-sky-100 transition hover:bg-sky-300/16"
              onClick={() => onValueChange(prompt)}
            >
              {prompt}
            </button>
          ))}
        </div>
      ) : null}
      <div className="flex gap-2 sm:gap-3">
        <input
          value={value}
          onChange={(event) => onValueChange(event.target.value)}
          className="star-input min-h-[3.3rem] flex-1"
          placeholder={placeholder}
        />
        {rightAction ?? (
          <button
            type="button"
            className="hidden h-[3.3rem] w-[3.3rem] shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/6 text-starMist/72 sm:inline-flex"
            aria-label="语音消息"
          >
            <Mic2 className="h-5 w-5" aria-hidden="true" />
          </button>
        )}
        <StarButton
          type="submit"
          disabled={disabled}
          className="min-w-20 px-5 sm:min-w-24 sm:px-6"
        >
          {submitLabel ?? <Send className="h-5 w-5" aria-hidden="true" />}
        </StarButton>
      </div>
    </form>
  );
}
