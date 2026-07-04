import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

function readSource(path) {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

test("global navigation is route-aware and compact on mobile", () => {
  const source = readSource("../src/components/StarSite.tsx");

  assert.match(source, /usePathname/);
  assert.match(source, /Menu/);
  assert.match(source, /X/);
  assert.match(source, /打开导航/);
  assert.match(source, /aria-current/);
  assert.match(source, /md:hidden/);
});

test("persona feature pages use a single back link without restoring workspace toolbar", () => {
  assert.equal(
    existsSync(new URL("../src/components/PersonaWorkspaceToolbar.tsx", import.meta.url)),
    false
  );

  const backLinkPath = new URL("../src/components/PersonaBackLink.tsx", import.meta.url);
  assert.equal(existsSync(backLinkPath), true);
  const backLinkSource = readFileSync(backLinkPath, "utf8");
  assert.match(backLinkSource, /返回人物总览/);
  assert.match(backLinkSource, /ROUTES\.personaDetail\(personaId\)/);
  assert.doesNotMatch(backLinkSource, /getPersonaWorkspaceNavGroups/);
  assert.doesNotMatch(backLinkSource, /当前星星/);

  for (const sourceFile of [
    "../app/personas/[id]/uploads/page.tsx",
    "../app/personas/[id]/jobs/page.tsx",
    "../app/personas/[id]/memories/page.tsx",
    "../app/personas/[id]/chat/page.tsx",
    "../src/components/GuidedExperiencePage.tsx",
    "../app/personas/[id]/voice/page.tsx",
    "../app/personas/[id]/avatar/page.tsx"
  ]) {
    const source = readSource(sourceFile);
    assert.match(source, /PersonaBackLink/, sourceFile);
    assert.doesNotMatch(source, /PersonaWorkspaceToolbar/, sourceFile);
    assert.doesNotMatch(source, /当前星星/, sourceFile);
  }

  const personaOverviewSource = readSource("../app/personas/[id]/page.tsx");
  assert.doesNotMatch(personaOverviewSource, /PersonaBackLink/);
  assert.doesNotMatch(personaOverviewSource, /PersonaWorkspaceToolbar/);
});

test("legacy stories deep link redirects to the memory archive", () => {
  const routePath = new URL("../app/personas/[id]/stories/page.tsx", import.meta.url);
  assert.equal(existsSync(routePath), true);
  const source = readFileSync(routePath, "utf8");

  assert.match(source, /redirect/);
  assert.match(source, /ROUTES\.personaMemories\(id\)/);
  assert.doesNotMatch(source, /personaStories/);
});

test("conversation pages use an always-visible equal-height workspace", () => {
  const workspaceSource = readSource("../src/components/ConversationWorkspace.tsx");
  assert.match(workspaceSource, /export function ConversationWorkspace/);
  assert.match(workspaceSource, /export function ChatComposer/);
  assert.match(workspaceSource, /conversation-scroll/);
  assert.match(workspaceSource, /scrollTop = scrollContainer\.scrollHeight/);
  assert.match(workspaceSource, /sticky bottom-0/);
  assert.match(workspaceSource, /items-stretch/);
  assert.match(workspaceSource, /xl:grid-cols-\[minmax\(0,0\.66fr\)_minmax\(20rem,0\.34fr\)\]/);
  assert.match(workspaceSource, /min-h-\[37rem\]/);
  assert.doesNotMatch(workspaceSource, /avatarOpen/);
  assert.doesNotMatch(workspaceSource, /hidden lg:block/);
  assert.doesNotMatch(workspaceSource, /数字人预览/);
  assert.doesNotMatch(workspaceSource, /max-h-\[32rem\]/);

  const chatSource = readSource("../app/personas/[id]/chat/page.tsx");
  assert.match(chatSource, /ConversationWorkspace/);
  assert.match(chatSource, /ChatComposer/);
  assert.match(chatSource, /CHAT_QUICK_PROMPTS/);
  assert.match(chatSource, /h-full xl:min-h-\[37rem\]/);
  assert.doesNotMatch(chatSource, /scrollIntoView/);

  const guidedSource = readSource("../src/components/GuidedExperiencePage.tsx");
  assert.match(guidedSource, /ConversationWorkspace/);
  assert.match(guidedSource, /ChatComposer/);
  assert.doesNotMatch(guidedSource, /scrollIntoView/);
});

test("demo-first page polish keeps primary actions visible and less destructive", () => {
  const homeSource = readSource("../app/page.tsx");
  assert.doesNotMatch(homeSource, /AI 模拟体验/);
  assert.match(homeSource, /items-center/);

  const dashboardSource = readSource("../app/dashboard/page.tsx");
  assert.match(dashboardSource, /进入星星/);
  assert.match(dashboardSource, /aria-label=\{`进入星星/);
  assert.match(dashboardSource, /删除/);

  const newPersonaSource = readSource("../app/personas/new/page.tsx");
  assert.match(newPersonaSource, /fixed inset-x-4 bottom-4/);
  assert.match(newPersonaSource, /保存这颗星星/);
});

test("memories page supports story favorites and collapsible source details", () => {
  const source = readSource("../app/personas/[id]/memories/page.tsx");

  assert.match(source, /updateStoryFavorite/);
  assert.match(source, /StoryCard/);
  assert.match(source, /来源/);
  assert.match(source, /<details/);
  assert.match(source, /is_favorite/);
});
