"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Archive, Heart, Search, Sparkles, Volume2 } from "lucide-react";
import {
  PageTitle,
  StarNav,
  StarPanel,
  StarShell
} from "@/src/components/StarSite";
import { PersonaBackLink } from "@/src/components/PersonaBackLink";
import { ensureDemoSession } from "@/src/lib/auth";
import { formatRelevanceScore, searchAuditMemories, SearchResultItem } from "@/src/lib/audit";
import { memoryCategoryLabel } from "@/src/lib/memories";
import {
  createStory,
  listStories,
  MemoryStoryRead,
  storySourceSummary,
  updateStoryFavorite
} from "@/src/lib/stories";

type PageState = "loading" | "ready" | "error";

export default function PersonaMemoriesPage() {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<PageState>("loading");
  const [stories, setStories] = useState<MemoryStoryRead[]>([]);
  const [storyTheme, setStoryTheme] = useState("共同回忆");
  const [storyBusy, setStoryBusy] = useState(false);
  const [favoriteBusyId, setFavoriteBusyId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [searchBusy, setSearchBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!personaId) {
      setError("缺少人物 ID。");
      setState("error");
      return;
    }

    let isCurrent = true;
    setState("loading");
    setError(null);

    ensureDemoSession()
      .then(() => listStories(personaId))
      .then((items) => {
        if (!isCurrent) {
          return;
        }
        setStories(items);
        setState("ready");
      })
      .catch((caught) => {
        if (!isCurrent) {
          return;
        }
        setError(caught instanceof Error ? caught.message : "无法加载回忆讲述。");
        setState("error");
      });

    return () => {
      isCurrent = false;
    };
  }, [personaId]);

  async function handleCreateStory() {
    if (!personaId) {
      return;
    }
    setStoryBusy(true);
    setError(null);
    setNotice(null);
    try {
      const story = await createStory(personaId, storyTheme);
      setStories((currentStories) => [
        story,
        ...currentStories.filter((item) => item.id !== story.id)
      ]);
      setNotice("已生成一段回忆讲述。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法生成回忆讲述。");
    } finally {
      setStoryBusy(false);
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!personaId || !searchQuery.trim()) {
      return;
    }

    setSearchBusy(true);
    setError(null);
    setNotice(null);
    try {
      const results = await searchAuditMemories(personaId, searchQuery, 6);
      setSearchResults(results.items);
      setNotice(results.items.length > 0 ? "已完成语义搜索。" : "未找到匹配记忆。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法完成语义搜索。");
    } finally {
      setSearchBusy(false);
    }
  }

  async function handleToggleFavorite(story: MemoryStoryRead) {
    setFavoriteBusyId(story.id);
    setError(null);
    setNotice(null);
    try {
      const updated = await updateStoryFavorite(story.id, !story.is_favorite);
      setStories((currentStories) =>
        currentStories.map((item) => (item.id === updated.id ? updated : item))
      );
      setNotice(updated.is_favorite ? "已收藏这段回忆。" : "已取消收藏。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法更新收藏状态。");
    } finally {
      setFavoriteBusyId(null);
    }
  }

  return (
    <StarShell>
      <StarNav />
      <main className="mx-auto w-full max-w-7xl px-5 pb-10 sm:px-8 lg:px-10">
        {personaId ? <PersonaBackLink personaId={personaId} /> : null}

        <PageTitle
          title="记忆档案馆"
          subtitle="让TA讲几段回忆，或在已整理的记忆里做语义搜索。"
        />

        {state === "loading" ? <Notice text="正在读取回忆..." /> : null}
        {state === "error" ? <Notice text={error ?? "无法加载回忆讲述。"} /> : null}

        {state === "ready" ? (
          <div className="mt-6 grid gap-5">
            <StoryArchivePanel
              stories={stories}
              theme={storyTheme}
              busy={storyBusy}
              favoriteBusyId={favoriteBusyId}
              onThemeChange={setStoryTheme}
              onGenerate={() => void handleCreateStory()}
              onToggleFavorite={(story) => void handleToggleFavorite(story)}
            />

            {error ? <Alert tone="error" text={error} /> : null}
            {notice ? <Alert tone="success" text={notice} /> : null}

            <SemanticSearchPanel
              query={searchQuery}
              results={searchResults}
              busy={searchBusy}
              onQueryChange={setSearchQuery}
              onSearch={(event) => void handleSearch(event)}
            />
          </div>
        ) : null}
      </main>
    </StarShell>
  );
}

function StoryArchivePanel({
  stories,
  theme,
  busy,
  favoriteBusyId,
  onThemeChange,
  onGenerate,
  onToggleFavorite
}: {
  stories: MemoryStoryRead[];
  theme: string;
  busy: boolean;
  favoriteBusyId: string | null;
  onThemeChange: (value: string) => void;
  onGenerate: () => void;
  onToggleFavorite: (story: MemoryStoryRead) => void;
}) {
  return (
    <StarPanel className="overflow-hidden p-0">
      <div className="grid gap-0 lg:grid-cols-[0.38fr_0.62fr]">
        <div className="border-b border-white/8 bg-[url('/memory-space/family-album.jpg')] bg-cover bg-center lg:border-b-0 lg:border-r">
          <div className="flex min-h-[18rem] flex-col justify-end bg-indigo-950/68 p-6">
            <p className="inline-flex items-center gap-2 text-sm font-bold text-starGold">
              <Archive className="h-4 w-4" aria-hidden="true" />
              回忆讲述
            </p>
            <h2 className="mt-3 font-serif text-3xl font-bold text-starGold">
              让TA讲几段回忆
            </h2>
            <p className="mt-3 text-sm font-semibold leading-7 text-starMist/72">
              只从已确认或已修正的记忆里生成第一人称文本，保留来源线索，方便继续追问和核对。
            </p>
          </div>
        </div>
        <div className="p-5 sm:p-6">
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              value={theme}
              onChange={(event) => onThemeChange(event.target.value)}
              className="star-input min-h-12 flex-1"
              placeholder="共同回忆、生日、家常、鼓励..."
            />
            <button
              type="button"
              disabled={busy}
              onClick={onGenerate}
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full border border-starGold/30 bg-starGold/14 px-6 text-sm font-bold text-starCream transition hover:bg-starGold/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              {busy ? "正在生成..." : "让TA讲一段回忆"}
            </button>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-3">
            {stories.slice(0, 3).map((story) => (
              <StoryCard
                key={story.id}
                story={story}
                busy={favoriteBusyId === story.id}
                onToggleFavorite={onToggleFavorite}
              />
            ))}
            {false ? stories.slice(0, 3).map((story) => (
              <article
                key={story.id}
                className="rounded-3xl border border-white/8 bg-white/6 p-4"
              >
                <p className="text-xs font-bold text-starMist/48">{story.theme}</p>
                <h3 className="mt-2 font-serif text-xl font-bold text-starGold">
                  {story.title}
                </h3>
                <p className="mt-2 line-clamp-5 text-sm font-semibold leading-7 text-starMist/74">
                  {story.content}
                </p>
                <p className="mt-3 text-xs font-semibold leading-5 text-starMist/48">
                  来源：{storySourceSummary(story)}
                </p>
                {story.audio_url ? (
                  <p className="mt-3 inline-flex items-center gap-2 rounded-full bg-starGold/12 px-3 py-1 text-xs font-bold text-starGold">
                    <Volume2 className="h-3.5 w-3.5" aria-hidden="true" />
                    已生成语音讲述
                  </p>
                ) : null}
              </article>
            )) : null}
            {stories.length === 0 ? (
              <p className="rounded-3xl border border-white/8 bg-white/6 p-4 text-sm font-semibold leading-7 text-starMist/68 md:col-span-3">
                还没有回忆讲述。输入主题后生成第一段。
              </p>
            ) : null}
          </div>
        </div>
      </div>
    </StarPanel>
  );
}

function StoryCard({
  story,
  busy,
  onToggleFavorite
}: {
  story: MemoryStoryRead;
  busy: boolean;
  onToggleFavorite: (story: MemoryStoryRead) => void;
}) {
  const sourceCount = story.source_memories.length || story.source_memory_ids.length;

  return (
    <article className="rounded-3xl border border-white/8 bg-white/6 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold text-starMist/48">{story.theme}</p>
          <h3 className="mt-2 font-serif text-xl font-bold text-starGold">{story.title}</h3>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={() => onToggleFavorite(story)}
          aria-label={story.is_favorite ? "取消收藏故事" : "收藏故事"}
          className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-rose-200/18 bg-rose-300/10 text-rose-100 transition hover:bg-rose-300/18 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Heart className={`h-4 w-4 ${story.is_favorite ? "fill-current" : ""}`} />
        </button>
      </div>
      <p className="mt-2 line-clamp-5 text-sm font-semibold leading-7 text-starMist/74">
        {story.content}
      </p>
      <details className="mt-3 rounded-2xl border border-sky-200/14 bg-sky-300/8 p-3 text-xs font-semibold leading-6 text-sky-100/82">
        <summary className="cursor-pointer list-none font-bold text-sky-100">
          来源 {sourceCount} 条
        </summary>
        <p className="mt-2 text-starMist/58">{storySourceSummary(story)}</p>
        {story.source_memories.length > 0 ? (
          <ul className="mt-2 grid gap-2">
            {story.source_memories.map((source) => (
              <li key={source.memory_card_id} className="rounded-xl bg-white/6 p-2">
                <span className="block font-bold text-starCream">{source.title}</span>
                <span className="mt-1 block text-starMist/58">{source.quote}</span>
                {source.source_location ? (
                  <span className="mt-1 block text-starMist/42">{source.source_location}</span>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
      </details>
      {story.audio_url ? (
        <p className="mt-3 inline-flex items-center gap-2 rounded-full bg-starGold/12 px-3 py-1 text-xs font-bold text-starGold">
          <Volume2 className="h-3.5 w-3.5" aria-hidden="true" />
          已生成语音讲述
        </p>
      ) : null}
    </article>
  );
}

function SemanticSearchPanel({
  query,
  results,
  busy,
  onQueryChange,
  onSearch
}: {
  query: string;
  results: SearchResultItem[];
  busy: boolean;
  onQueryChange: (value: string) => void;
  onSearch: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <StarPanel className="p-5">
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-full bg-starGold/12 text-starGold">
          <Search className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <h2 className="font-serif text-2xl font-bold text-starGold">语义搜索</h2>
          <p className="text-sm font-semibold text-starMist/58">
            输入关键词，在长期/短期记忆中查找可追溯来源记忆。
          </p>
        </div>
      </div>

      <form onSubmit={onSearch} className="mt-5 flex flex-col gap-3 sm:flex-row">
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          className="star-input min-h-11 flex-1"
          placeholder="输入关键词，例如：馄饨、生日、慢慢来"
        />
        <button
          type="submit"
          disabled={busy || !query.trim()}
          className="rounded-xl border border-starGold/26 bg-starGold/14 px-5 py-2 text-sm font-bold text-starCream transition hover:bg-starGold/22 disabled:cursor-not-allowed disabled:opacity-45"
        >
          {busy ? "搜索中" : "搜索"}
        </button>
      </form>

      <div className="mt-5 grid gap-3">
        {results.length === 0 ? (
          <p className="rounded-2xl border border-white/8 bg-white/6 p-4 text-sm font-semibold text-starMist/58">
            暂无搜索结果。
          </p>
        ) : (
          results.slice(0, 6).map((result) => (
            <article key={result.memory.id} className="rounded-2xl border border-white/8 bg-white/6 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-sm font-black text-starCream">{result.memory.title}</h3>
                <span className="rounded-full bg-starGold/12 px-2 py-0.5 text-xs font-bold text-starGold">
                  {formatRelevanceScore(result.relevance_score)}
                </span>
                <span className="rounded-full bg-white/8 px-2 py-0.5 text-xs font-bold text-starMist/70">
                  {memoryCategoryLabel(result.memory.category)}
                </span>
              </div>
              <p className="mt-2 text-sm font-semibold leading-7 text-starMist/74">
                {result.memory.content}
              </p>
              <p className="mt-2 text-xs font-semibold leading-5 text-starMist/50">
                来源摘录：{result.source_excerpt ?? result.memory.source_quote ?? "暂无摘录"}
              </p>
              {result.memory.source_location ? (
                <p className="mt-1 text-xs font-semibold leading-5 text-starMist/50">
                  来源位置：{result.memory.source_location}
                </p>
              ) : null}
            </article>
          ))
        )}
      </div>
    </StarPanel>
  );
}

function Alert({ tone, text }: { tone: "error" | "success"; text: string }) {
  return (
    <div
      className={`rounded-2xl border p-4 text-center text-sm font-semibold ${
        tone === "error"
          ? "border-rose-300/20 bg-rose-500/15 text-rose-100"
          : "border-emerald-200/20 bg-emerald-400/12 text-emerald-100"
      }`}
    >
      {text}
    </div>
  );
}

function Notice({ text }: { text: string }) {
  return (
    <StarPanel className="mx-auto mt-8 max-w-3xl p-5 text-center text-starMist/72">
      {text}
    </StarPanel>
  );
}
