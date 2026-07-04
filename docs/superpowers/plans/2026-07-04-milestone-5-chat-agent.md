# Milestone 5 First-Person Chat Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement PRD Milestone 5 so a user can create/list conversations, send a text message, receive a first-person persona reply, review citations, and correct a cited memory so the next reply immediately uses the corrected memory.

**Architecture:** Reuse existing `conversations`, `messages`, and `message_citations` tables from the initial schema. Backend owns conversation scoping, deterministic memory retrieval, first-person mock chat generation, citation persistence, and correction routing to existing memory audit behavior. Frontend owns `/personas/{id}/chat`, conversation/message helpers, citation display, and correction affordance. Docs sync stays last and records only verified behavior.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, Next.js, React, TypeScript, Tailwind CSS, Node test runner.

## Global Constraints

- Follow `docs/可信人格记忆Agent_mvp_prd.md` Milestone 5 only; do not implement Milestone 6 voice/TTS, Milestone 7 avatar/3D, Milestone 8 story/export, public community, payment, or advanced compliance.
- Chat replies must use the persona's first person and naturally use `user_nickname_by_persona`.
- Chat replies must not self-identify as an AI assistant, language model, generic system, or say `我真的回来了`.
- Fact answers must prefer `corrected` memories over `confirmed`, then manual profile fields, then high-confidence memories, then medium pending memories as weak reference.
- Retrieval must ignore `rejected`, `disabled`, and deleted memories.
- Every reply that uses a concrete memory must persist `message_citations` with `memory_card_id`, `source_material_id`, `parsed_chunk_id`, `quote`, and `source_location` where available.
- Insufficient evidence must produce a gentle uncertainty response instead of inventing a fact.
- `POST /api/messages/{id}/correct-memory` must update the cited memory through the same corrected-memory contract used by the memory audit API, and the next chat retrieval must use the corrected content.
- The implementation must default to the mock provider path and must not require `.env/runtime.env` secrets; real OpenAI-compatible config can remain unused until a later provider task.
- Verification must include backend tests, frontend tests, lint, build, `docker compose config`, `docs/init.sh`, and `git diff --check`.

---

## File Structure

- `backend/app/schemas/chat.py`: conversation, message, citation, send-message, and correction schemas.
- `backend/app/services/chat.py`: retrieval, prompt context building, deterministic mock response generation, conversation/message/citation helpers.
- `backend/app/api/routes/chat.py`: PRD Chat API routes except voice-message, which remains Milestone 6.
- `backend/app/providers/gateway.py`: mock `chat_llm` provider capability.
- `backend/app/main.py`: include chat router.
- `backend/tests/test_chat.py`: backend chat API, retrieval, citations, correction, provider metadata, and user-scope tests.
- `backend/tests/test_provider_gateway.py`: mock `chat_llm` gateway output test.
- `frontend/src/lib/api.ts`: chat API paths.
- `frontend/src/lib/routes.ts`: `personaChat(id)` route helper.
- `frontend/src/lib/chat.ts`: chat types, API helpers, citation helpers, UI labels.
- `frontend/app/personas/[id]/chat/page.tsx`: text chat page with evidence and correction actions.
- `frontend/app/personas/[id]/page.tsx`: link to chat page and show current chat capability.
- `frontend/tests/chat.test.mjs`: route/helper/label tests.
- `frontend/tests/routes.test.mjs`: chat route/API path tests.
- `docs/README.md`, `docs/feature-list.json`, `docs/progress.md`, `docs/prd-checklist.md`, `docs/平台说明.md`: sync Milestone 5 facts and evidence after verification passes.
- `docs/init.sh`, `frontend/app/page.tsx`: update visible milestone copy if stale.

---

### Task 1: Backend Chat API, Retrieval, Citations, And Correction

**Files:**
- Create: `backend/app/schemas/chat.py`
- Create: `backend/app/services/chat.py`
- Create: `backend/app/api/routes/chat.py`
- Modify: `backend/app/providers/gateway.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_chat.py`
- Modify: `backend/tests/test_provider_gateway.py`

**Interfaces:**
- Produces: `GET /api/personas/{id}/conversations`
- Produces: `POST /api/personas/{id}/conversations`
- Produces: `GET /api/conversations/{id}/messages`
- Produces: `POST /api/conversations/{id}/messages`
- Produces: `GET /api/messages/{id}/citations`
- Produces: `POST /api/messages/{id}/correct-memory`
- Defers: `POST /api/conversations/{id}/voice-message` to Milestone 6.

- [x] **Step 1: Write failing backend chat tests**

Create `backend/tests/test_chat.py` with tests for:

- creating and listing conversations scoped to the current user/persona;
- sending a text message creates a user message, an assistant/persona message, and citations;
- assistant reply uses first person and the configured user nickname;
- assistant reply does not include `AI 助手`, `语言模型`, or `我真的回来了`;
- corrected memories outrank confirmed memories for the same query;
- rejected/disabled/deleted memories are not cited;
- a low-evidence question returns a gentle uncertainty response and no citation;
- `GET /api/messages/{id}/citations` returns persisted citation rows;
- `POST /api/messages/{id}/correct-memory` updates the cited memory to `corrected`, writes `user_correction`, refreshes profile/trust through the memory audit contract, and a subsequent chat answer uses the corrected content;
- cross-user access to conversations/messages/citations/correction returns 404.

- [x] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest backend/tests/test_chat.py -q
```

Expected: FAIL because chat schemas/routes/services do not exist.

- [x] **Step 3: Implement chat schemas**

Create `backend/app/schemas/chat.py`:

- `ConversationCreate`: optional `title`.
- `ConversationRead`: `id`, `user_id`, `persona_id`, `title`, `created_at`, `updated_at`.
- `ConversationListResponse`: `items`.
- `MessageSend`: required `content`.
- `MessageRead`: `id`, `conversation_id`, `role`, `content`, `audio_url`, `metadata_json`, `created_at`, optional `citations`.
- `MessageListResponse`: `items`.
- `MessageCitationRead`: `id`, `message_id`, `memory_card_id`, `source_material_id`, `parsed_chunk_id`, `quote`, `source_location`, `created_at`.
- `MemoryCorrectionCreate`: `memory_id`, `content`, optional `title`.
- `MemoryCorrectionResponse`: corrected memory and next-step copy.

- [x] **Step 4: Implement retrieval and response service**

Create `backend/app/services/chat.py`:

- `get_conversation_or_404(db, user, conversation_id)` and `get_message_or_404(db, user, message_id)`.
- `retrieve_memories(db, persona, user_message, limit=4)` using deterministic scoring:
  - status priority: `corrected` > `confirmed` > high-confidence pending > medium pending;
  - keyword overlap from normalized Chinese/English text;
  - category boosts for expression/emotional/shared-event terms;
  - exclude rejected/disabled/deleted memories.
- `build_conversation_history(db, conversation, limit=8)`.
- `generate_persona_reply(persona, profile, retrieved_memories, history, user_message)`:
  - always first person;
  - naturally includes `user_nickname_by_persona`;
  - if no strong memory match, uses gentle uncertainty: `这件事我记不太清...`;
  - if the user expresses sadness/missing/regret, respond to emotion before suggestions;
  - avoids forbidden expressions and the hard-banned phrases above;
  - uses profile summary when available.
- `send_text_message(db, conversation, persona, content)` persists the user message, persona reply, and citations for used memories.
- `correct_cited_memory(db, user, message, payload)` updates the memory content/title, sets status `corrected`, saves `user_correction`, refreshes profile/trust, and returns the corrected memory.

Keep all logic deterministic and local; do not call a real LLM provider in this milestone.

- [x] **Step 5: Implement chat routes**

Create `backend/app/api/routes/chat.py`:

- Use `get_persona_or_404` for persona routes.
- `GET /personas/{persona_id}/conversations`: list non-deleted conversations.
- `POST /personas/{persona_id}/conversations`: create conversation; default title can be the first non-empty title or `和 {persona.name} 的对话`.
- `GET /conversations/{conversation_id}/messages`: list messages with citations for persona replies.
- `POST /conversations/{conversation_id}/messages`: send text, return the persona reply with citations.
- `GET /messages/{message_id}/citations`: return citations only if the message belongs to the current user.
- `POST /messages/{message_id}/correct-memory`: correct a cited memory owned by the same user/persona.

Register router in `backend/app/main.py`.

- [x] **Step 6: Run backend checks**

Run:

```powershell
python -m pytest backend/tests/test_provider_gateway.py backend/tests/test_chat.py -q
python -m pytest backend/tests -q
```

Expected: focused tests pass; full backend suite passes.

- [x] **Step 7: Commit**

```powershell
git add backend/app/schemas/chat.py backend/app/services/chat.py backend/app/api/routes/chat.py backend/app/providers/gateway.py backend/app/main.py backend/tests/test_chat.py backend/tests/test_provider_gateway.py
git commit -m "feat: add first-person chat API"
```

---

### Task 2: Frontend Chat Page, Evidence, And Correction UI

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/routes.ts`
- Create: `frontend/src/lib/chat.ts`
- Create: `frontend/app/personas/[id]/chat/page.tsx`
- Modify: `frontend/app/personas/[id]/page.tsx`
- Create: `frontend/tests/chat.test.mjs`
- Modify: `frontend/tests/routes.test.mjs`

**Interfaces:**
- Consumes: Task 1 chat APIs.
- Produces: `ROUTES.personaChat(id)`.
- Produces: `listConversations`, `createConversation`, `listMessages`, `sendMessage`, `listMessageCitations`, and `correctMessageMemory`.

- [x] **Step 1: Write failing frontend tests**

Create `frontend/tests/chat.test.mjs`:

- route/API helper tests for all Milestone 5 text-chat paths;
- chat role label tests for `user` and `persona`;
- citation summary helper tests that render memory/source labels without claiming voice/avatar support;
- correction payload helper tests.

Update `frontend/tests/routes.test.mjs` to assert `/personas/{id}/chat`.

- [x] **Step 2: Run tests to verify they fail**

Run:

```powershell
npm.cmd --prefix frontend run test
```

Expected: FAIL because chat helpers/routes do not exist.

- [x] **Step 3: Implement frontend chat helpers**

Create `frontend/src/lib/chat.ts`:

- types matching backend schemas;
- API helpers using JWT bearer auth and `readApiJson`;
- role labels and citation summary helpers;
- small validation helper that prevents blank message sends and blank correction content.

Update `frontend/src/lib/api.ts` and `frontend/src/lib/routes.ts` with chat paths.

- [x] **Step 4: Implement chat page**

Create `frontend/app/personas/[id]/chat/page.tsx`:

- require login token and load/create a conversation for the persona;
- show a compact left panel placeholder for avatar/voice status as future Milestones 6/7, without claiming those features are implemented;
- show right-side message flow, text input, send button, and PRD empty state copy;
- after sending, append the returned persona message;
- show `查看依据` for each persona message with citations;
- provide `纠正这条记忆` action for cited memories, posting to `correct-memory` and refreshing messages/citations;
- do not implement voice input, TTS playback, 3D loading, story generation, or favorites in this milestone.

Update `frontend/app/personas/[id]/page.tsx` to link to chat and clearly label chat as text-first Milestone 5.

- [x] **Step 5: Run frontend checks**

Run:

```powershell
npm.cmd --prefix frontend run test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
```

Expected: tests, lint, and build pass.

- [x] **Step 6: Commit**

```powershell
git add frontend/src/lib/api.ts frontend/src/lib/routes.ts frontend/src/lib/chat.ts frontend/app/personas/[id]/chat/page.tsx frontend/app/personas/[id]/page.tsx frontend/tests/chat.test.mjs frontend/tests/routes.test.mjs
git commit -m "feat: add text chat frontend"
```

---

### Task 3: Docs, Harness, And Final Milestone 5 Verification

**Files:**
- Modify: `docs/README.md`
- Modify: `docs/feature-list.json`
- Modify: `docs/progress.md`
- Modify: `docs/prd-checklist.md`
- Modify: `docs/平台说明.md`
- Modify: `docs/init.sh`
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: verified Task 1 and Task 2 behavior.
- Produces: docs truth surface for Milestone 5.

- [x] **Step 1: Update PRD checklist first**

Add Milestone 5 rows for:

- conversation list/create and message send APIs;
- first-person, nickname-aware persona reply;
- deterministic retrieval priority with `corrected` before `confirmed`;
- rejected/disabled/deleted memories excluded;
- persisted citations and `GET /api/messages/{id}/citations`;
- `correct-memory` immediately affecting subsequent chat;
- frontend `/personas/{id}/chat` text chat/evidence/correction page;
- voice-message route deferred to Milestone 6.

- [x] **Step 2: Run baseline verification before broader docs copy**

Run:

```powershell
python -m json.tool docs/feature-list.json
python -m pytest backend/tests -q
npm.cmd --prefix frontend run test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
docker compose config
& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh
```

- [x] **Step 3: Sync docs truth surface**

Update:

- `docs/README.md`: current state includes Milestone 5 text chat, conversation history, citations, and correction; voice/TTS/avatar/story/export remain later.
- `docs/feature-list.json`: add `feat-009` with dependencies on `feat-008`, status `completed`, evidence commands and files.
- `docs/progress.md`: latest session, status, risks, verification evidence, modified files, next milestone.
- `docs/平台说明.md`: user-operable text chat/evidence/correction instructions only.
- `docs/init.sh` and `frontend/app/page.tsx`: visible copy from Milestone 4 to Milestone 5 if stale.

- [x] **Step 4: Final verification**

Run:

```powershell
python -m json.tool docs/feature-list.json
python -m pytest backend/tests -q
npm.cmd --prefix frontend run test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
docker compose config
& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh
git diff --check
rg "Chat/vector retrieval.*仍未实现|对话 Agent.*尚未实现|Milestone 4 harness|chat.*future Milestone 5|Chat will read this profile summary in Milestone 5|no chat behavior is implemented|Milestone 5 is implemented" docs frontend/app -n --glob "!docs/superpowers/plans/**"
```

Expected: all commands pass; stale-copy search has no active docs/app hits claiming Milestone 5 chat is still unimplemented.

- [x] **Step 5: Commit**

```powershell
git add backend/app/models/user.py backend/tests/test_container_runtime.py docs/README.md docs/feature-list.json docs/progress.md docs/prd-checklist.md docs/平台说明.md docs/init.sh docs/superpowers/plans/2026-07-04-milestone-5-chat-agent.md frontend/app/page.tsx frontend/app/personas/[id]/profile/page.tsx
git commit -m "docs: sync Milestone 5 chat evidence"
```

---

## Review Gates

- After Task 1, request review for backend chat contract, retrieval priority, citation persistence, correction behavior, and user isolation.
- After Task 2, request review for frontend chat scope, evidence/correction UI, and copy that avoids claiming voice/avatar support.
- After Task 3, request review for docs truth surface and stale-copy consistency.

## Known Non-Goals For This Milestone

- Real LLM quality, embeddings provider, pgvector ANN tuning, voice input, ASR, TTS, cloned voice playback, 3D avatar rendering, story generation, favorites, exports, public sharing, payment, and advanced compliance remain out of scope.
- `POST /api/conversations/{id}/voice-message` is listed in the PRD API table but belongs to Milestone 6 and should be documented as deferred, not silently implemented.
