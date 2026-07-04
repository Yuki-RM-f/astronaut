import { API_PATHS, buildApiUrl, readApiJson } from "./api";
import { authHeaders } from "./auth";

export type StoryMemorySource = {
  memory_card_id: string;
  title: string;
  quote: string;
  source_location: string | null;
};

export type MemoryStoryRead = {
  id: string;
  persona_id: string;
  theme: string;
  title: string;
  content: string;
  audio_url: string | null;
  source_memory_ids: string[];
  source_memories: StoryMemorySource[];
  is_favorite: boolean;
  metadata_json: Record<string, unknown> | unknown[] | null;
  created_at: string;
  updated_at: string;
};

type MemoryStoryListResponse = {
  items: MemoryStoryRead[];
};

export function normalizeStoryTheme(value: string): string {
  return value.trim() || "共同回忆";
}

export function storySourceSummary(story: MemoryStoryRead): string {
  if (story.source_memories.length === 0) {
    return "暂无已关联的记忆来源";
  }

  return story.source_memories
    .slice(0, 2)
    .map((source) =>
      source.source_location ? `${source.title}（${source.source_location}）` : source.title
    )
    .join(" · ");
}

export async function listStories(personaId: string): Promise<MemoryStoryRead[]> {
  const response = await fetch(buildApiUrl(API_PATHS.stories.list(personaId)), {
    headers: authHeaders()
  });
  const data = await readApiJson<MemoryStoryListResponse>(
    response,
    "无法加载回忆故事。"
  );
  return data.items;
}

export async function createStory(
  personaId: string,
  theme: string
): Promise<MemoryStoryRead> {
  const response = await fetch(buildApiUrl(API_PATHS.stories.list(personaId)), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify({ theme: normalizeStoryTheme(theme) })
  });
  return readApiJson<MemoryStoryRead>(response, "无法生成回忆故事。");
}

export async function updateStoryFavorite(
  storyId: string,
  isFavorite: boolean
): Promise<MemoryStoryRead> {
  const response = await fetch(buildApiUrl(API_PATHS.stories.favorite(storyId)), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify({ is_favorite: isFavorite })
  });
  return readApiJson<MemoryStoryRead>(response, "无法更新收藏状态。");
}
