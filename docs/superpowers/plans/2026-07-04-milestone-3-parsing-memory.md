# Milestone 3 Parsing And Memory Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement PRD Milestone 3 so uploaded/manual demo materials are parsed through the mock Provider Gateway into `ParsedChunk` and source-backed `MemoryCard` records, and users can audit, confirm, edit, disable, reject, or delete those memory cards.

**Architecture:** Keep the existing SQLAlchemy tables and add behavior over them. Backend owns deterministic mock parsing, memory extraction, job completion, and user-scoped memory audit APIs; frontend owns the `/personas/{id}/memories` audit page and helper calls. Docs sync stays last and records only verified behavior.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, existing mock Provider Gateway, Next.js, React, TypeScript, Tailwind CSS, Node test runner.

## Global Constraints

- Follow `docs/可信人格记忆Agent_mvp_prd.md` Milestone 3 only; do not implement Milestone 4 trust recalculation/profile aggregation, Milestone 5 chat/vector retrieval, Milestone 6 voice/TTS, Milestone 7 avatar/3D, Milestone 8 story/export, public community, payment, or advanced compliance.
- All AI capabilities must go through `backend/app/providers/gateway.py`; real OCR, ASR, VLM, embedding, or LLM providers must not block MVP and must fall back to deterministic mock output.
- Do not commit or print `.env/runtime.env` secrets; only refer to variable names or sanitized presence.
- Every parse operation must write/update an `ai_jobs` record and leave the job visible on the jobs page with a PRD status.
- Supported job statuses remain exactly `pending`, `running`, `succeeded`, `failed`, `retrying`, and `canceled`.
- Supported memory statuses are exactly `pending_review`, `confirmed`, `corrected`, `rejected`, `disabled`, and `auto_generated`.
- Supported memory categories are exactly `basic_fact`, `relationship`, `preference`, `habit`, `expression_style`, `shared_event`, `value`, `emotional_pattern`, `story_material`, and `unknown`.
- Supported confidence levels are exactly `high`, `medium`, and `low`; `confidence_score` must stay in `0..100`.
- Every `MemoryCard` must have `source_material_id`, `source_type`, `source_quote`, and `source_location`.
- Editing a memory through the audit API must set status to `corrected`, preserve source fields, and store `user_correction`.
- Confirmed/corrected memories are future-usable; rejected/disabled/deleted memories must be excluded from active memory lists.
- Verification must include backend tests, frontend tests, lint, build, `docker compose config`, `docs/init.sh`, and `git diff --check`.

---

## File Structure

- `backend/app/providers/gateway.py`: add deterministic mock outputs for `text_parser`, `ocr`, `asr`, `image_understanding`, `video_understanding`, and `memory_extraction`.
- `backend/app/services/parsing.py`: orchestrate material parsing, ParsedChunk creation, MemoryCard creation, material parse status, and job status transitions.
- `backend/app/services/materials.py`: call the parsing service after creating or re-queueing parse jobs.
- `backend/app/schemas/memory.py`: memory audit request/response schemas and enum literals.
- `backend/app/api/routes/memories.py`: PRD memory list/create/detail/update/confirm/reject/disable/delete routes.
- `backend/app/main.py`: include memory router.
- `backend/tests/test_parsing.py`: mock parsing and job completion coverage.
- `backend/tests/test_memories.py`: memory audit API, status transitions, source requirements, and user scoping coverage.
- `frontend/src/lib/api.ts`: memory API paths.
- `frontend/src/lib/routes.ts`: `personaMemories(id)` route helper.
- `frontend/src/lib/memories.ts`: memory types, labels, filters, and API helpers.
- `frontend/app/personas/[id]/memories/page.tsx`: memory audit dashboard.
- `frontend/app/personas/[id]/page.tsx`: link to the memory audit page and update current-scope copy.
- `frontend/tests/memories.test.mjs`: memory status/category helper tests.
- `frontend/tests/routes.test.mjs`: memory route/API path tests.
- `docs/README.md`, `docs/feature-list.json`, `docs/progress.md`, `docs/prd-checklist.md`, `docs/平台说明.md`: sync Milestone 3 facts and evidence after verification passes.

---

### Task 1: Backend Mock Parsing And Memory Generation

**Files:**
- Modify: `backend/app/providers/gateway.py`
- Create: `backend/app/services/parsing.py`
- Modify: `backend/app/services/materials.py`
- Create: `backend/tests/test_parsing.py`
- Modify if needed: `backend/tests/test_materials.py`
- Modify if needed: `backend/tests/test_jobs.py`

**Interfaces:**
- Consumes: `SourceMaterial`, `ParsedChunk`, `MemoryCard`, and `AIJob` models already present in the initial schema.
- Produces: `run_parse_job(db: Session, material: SourceMaterial, job: AIJob) -> list[MemoryCard]`.
- Produces: upload/manual/reparse flows that create an AI job, run deterministic mock parsing, create at least one source-backed `ParsedChunk`, create one or more source-backed `MemoryCard` records, set `SourceMaterial.parse_status = "succeeded"`, and set job status to `succeeded`.

- [ ] **Step 1: Write failing backend parsing tests**

Create `backend/tests/test_parsing.py` with tests for:

```python
def test_manual_material_generates_source_backed_memory_cards(client):
    token = register_user(client, "m3-manual@example.com")
    persona = create_persona(client, token)
    response = client.post(
        f"/api/personas/{persona['id']}/materials/manual",
        headers=auth(token),
        json={
            "manual_text": "外婆喜欢包馄饨。她常说慢慢来。",
            "importance": "very_important",
        },
    )
    assert response.status_code == 201
    material = response.json()
    assert material["parse_status"] == "succeeded"
    assert material["jobs"][0]["status"] == "succeeded"
```

Add database assertions through the shared `db_session` fixture:

```python
chunks = db_session.scalars(select(ParsedChunk)).all()
memories = db_session.scalars(select(MemoryCard)).all()
assert len(chunks) >= 1
assert len(memories) >= 2
assert all(memory.source_material_id == material["id"] for memory in memories)
assert all(memory.source_quote for memory in memories)
assert all(memory.source_location for memory in memories)
assert {memory.status for memory in memories} == {"pending_review"}
```

Add file-type coverage:

```python
def test_upload_demo_files_generate_type_specific_chunks_and_jobs(client, db_session):
    # upload text/image/audio/video files and assert chunk_type values include
    # text, image, audio, and video; assert job statuses are succeeded.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_parsing.py -q`

Expected: FAIL because parsing service, gateway capabilities, and auto memory generation do not exist.

- [ ] **Step 3: Implement deterministic mock Provider Gateway capabilities**

In `backend/app/providers/gateway.py`, keep `run()` async and return PRD-shaped mock output by capability:

```python
if capability == "memory_extraction":
    return {
        "provider_name": self.provider_name,
        "capability": capability,
        "status": "succeeded",
        "input": payload,
        "output": {"memories": build_memory_candidates(payload)},
    }
```

Implement capability outputs for:

- `text_parser`: cleaned text and chunks.
- `ocr`: OCR text derived from file name/user description/manual text.
- `image_understanding`: caption, scene metadata, and memory candidate text.
- `asr`: transcript and sample metadata.
- `video_understanding`: transcript, scene summary, timestamps, and memory candidate text.
- `memory_extraction`: JSON-compatible list with `title`, `content`, `category`, `confidence_level`, `confidence_score`, `source_quote`, and `source_location`.

Keep output deterministic and local; do not call network APIs.

- [ ] **Step 4: Implement parsing service**

Create `backend/app/services/parsing.py` with:

```python
def run_parse_job(db: Session, material: SourceMaterial, job: AIJob) -> list[MemoryCard]:
    job.status = "running"
    job.started_at = utcnow()
    material.parse_status = "running"
    try:
        parsed_payload = run_gateway_for_material(material)
        chunk = create_parsed_chunk(db, material, parsed_payload)
        memories = create_memory_cards(db, material, chunk, parsed_payload)
        material.parse_status = "succeeded"
        job.status = "succeeded"
        job.output_json = {"memory_card_ids": [memory.id for memory in memories]}
        job.finished_at = utcnow()
        return memories
    except Exception as exc:
        material.parse_status = "failed"
        job.status = "failed"
        job.error_message = str(exc)
        job.finished_at = utcnow()
        return []
```

Use `asyncio.run(ProviderGateway().run(...))` from this synchronous service, and keep the mock payload small. If `material.storage_url` points to a local text file, read it as UTF-8 with `errors="ignore"`; for binary/image/audio/video files, use file name, user description, type, and deterministic mock descriptions instead.

- [ ] **Step 5: Wire material creation/reparse to run the mock job**

Modify `backend/app/services/materials.py` so `create_manual_material`, `create_uploaded_material`, and `queue_material_parse`:

1. create the `AIJob`;
2. flush the job;
3. call `run_parse_job`;
4. commit and refresh.

Update existing material/job tests from `pending` to `succeeded` where the mock parser now completes inline. Do not remove retry/cancel status tests for manually-created pending/running jobs.

- [ ] **Step 6: Run backend tests**

Run:

```powershell
python -m pytest backend/tests/test_parsing.py backend/tests/test_materials.py backend/tests/test_jobs.py -q
python -m pytest backend/tests -q
```

Expected: parsing/materials/jobs focused tests pass; full backend suite passes.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/providers/gateway.py backend/app/services/parsing.py backend/app/services/materials.py backend/tests/test_parsing.py backend/tests/test_materials.py backend/tests/test_jobs.py
git commit -m "feat: add mock material parsing"
```

---

### Task 2: Backend Memory Audit API

**Files:**
- Create: `backend/app/schemas/memory.py`
- Create: `backend/app/api/routes/memories.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_memories.py`
- Modify if needed: `backend/tests/test_personas.py`

**Interfaces:**
- Consumes: `MemoryCard` records generated by Task 1.
- Produces: `GET /api/personas/{id}/memories`, `POST /api/personas/{id}/memories`, `GET /api/memories/{id}`, `PATCH /api/memories/{id}`, `POST /api/memories/{id}/confirm`, `POST /api/memories/{id}/reject`, `POST /api/memories/{id}/disable`, and `DELETE /api/memories/{id}`.
- Produces: `MemoryRead` with PRD fields: `id`, `persona_id`, `title`, `content`, `category`, `confidence_level`, `confidence_score`, `source_material_id`, `parsed_chunk_id`, `source_type`, `source_quote`, `source_location`, `evidence_json`, `status`, `user_correction`, `created_by`, `created_at`, `updated_at`.

- [ ] **Step 1: Write failing memory API tests**

Create `backend/tests/test_memories.py` with:

```python
def test_memory_list_detail_and_filters_are_user_scoped(client):
    owner_token = register_user(client, "memory-owner@example.com")
    other_token = register_user(client, "memory-other@example.com")
    persona = create_persona(client, owner_token)
    create_manual_material(client, owner_token, persona["id"])
    listed = client.get(f"/api/personas/{persona['id']}/memories", headers=auth(owner_token))
    assert listed.status_code == 200
    memory = listed.json()["items"][0]
    assert memory["source_material_id"]
    assert memory["source_quote"]
    assert memory["source_location"]
    assert client.get(f"/api/memories/{memory['id']}", headers=auth(other_token)).status_code == 404
```

Add status transition tests:

```python
def test_confirm_edit_disable_reject_and_delete_memory(client):
    # confirm -> status confirmed
    # patch title/content -> status corrected and user_correction stores new content
    # disable -> status disabled
    # reject -> status rejected
    # delete -> 204 and memory no longer appears in list
```

Add source validation tests:

```python
def test_manual_memory_requires_source_fields(client):
    response = client.post(
        f"/api/personas/{persona['id']}/memories",
        headers=auth(token),
        json={"title": "No source", "content": "Missing source", "category": "unknown"},
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_memories.py -q`

Expected: FAIL because memory schemas/routes are not implemented.

- [ ] **Step 3: Implement schemas**

Create `backend/app/schemas/memory.py` with `Literal` enums for allowed category/status/confidence values, plus:

- `MemoryRead`
- `MemoryListResponse`
- `MemoryCreate`
- `MemoryUpdate`

Use Pydantic validators to reject blank `title`, `content`, `source_quote`, and `source_location`; require `source_material_id` on create; clamp or validate `confidence_score` with `ge=0, le=100`.

- [ ] **Step 4: Implement user-scoped routes**

Create `backend/app/api/routes/memories.py`:

- Use `get_persona_or_404` for persona-scoped list/create.
- Fetch single memories by joining/checking the owning persona’s `user_id`.
- Exclude `deleted_at` rows from list/detail.
- Support optional query filters: `status`, `category`, and `confidence_level`.
- On PATCH, update only provided fields and set `status = "corrected"` plus `user_correction = content` when `title` or `content` changes.
- On confirm/reject/disable, set status exactly `confirmed`, `rejected`, or `disabled`.
- On DELETE, soft-delete with `deleted_at`.

Register the router in `backend/app/main.py`.

- [ ] **Step 5: Keep persona stats aligned**

If existing persona detail stats count all non-deleted `memory_cards`, keep that behavior. Do not implement Milestone 4 trust recalculation yet; docs can say status changes are stored for future chat/trust use.

- [ ] **Step 6: Run backend tests**

Run:

```powershell
python -m pytest backend/tests/test_memories.py -q
python -m pytest backend/tests -q
```

Expected: focused memory tests pass; full backend suite passes.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/schemas/memory.py backend/app/api/routes/memories.py backend/app/main.py backend/tests/test_memories.py backend/tests/test_personas.py
git commit -m "feat: add memory audit API"
```

---

### Task 3: Frontend Memory Audit Dashboard

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/routes.ts`
- Create: `frontend/src/lib/memories.ts`
- Create: `frontend/app/personas/[id]/memories/page.tsx`
- Modify: `frontend/app/personas/[id]/page.tsx`
- Create: `frontend/tests/memories.test.mjs`
- Modify: `frontend/tests/routes.test.mjs`

**Interfaces:**
- Consumes: Task 2 memory APIs.
- Produces: route helper `ROUTES.personaMemories(id)`.
- Produces: memory client helpers `listMemories`, `confirmMemory`, `rejectMemory`, `disableMemory`, `deleteMemory`, `updateMemory`, status/category/confidence labels, and audit filters.

- [ ] **Step 1: Write failing frontend tests**

Create `frontend/tests/memories.test.mjs`:

```javascript
import test from "node:test";
import assert from "node:assert/strict";
import { memoryStatusLabel, memoryCategoryLabel, canUseMemoryInConversation } from "../src/lib/memories";

test("memory labels expose PRD Milestone 3 statuses and categories", () => {
  assert.equal(memoryStatusLabel("pending_review"), "Pending review");
  assert.equal(memoryStatusLabel("confirmed"), "Confirmed");
  assert.equal(memoryStatusLabel("corrected"), "Corrected");
  assert.equal(memoryStatusLabel("rejected"), "Rejected");
  assert.equal(memoryStatusLabel("disabled"), "Disabled");
  assert.equal(memoryStatusLabel("auto_generated"), "Auto generated");
  assert.equal(memoryCategoryLabel("shared_event"), "Shared event");
});

test("only confirmed and corrected memories are future usable", () => {
  assert.equal(canUseMemoryInConversation("confirmed"), true);
  assert.equal(canUseMemoryInConversation("corrected"), true);
  assert.equal(canUseMemoryInConversation("disabled"), false);
});
```

Update `frontend/tests/routes.test.mjs` to assert `/personas/{id}/memories` and API memory paths.

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm.cmd --prefix frontend run test`

Expected: FAIL because memory helpers/routes do not exist.

- [ ] **Step 3: Implement frontend API/helpers**

Add memory paths to `frontend/src/lib/api.ts`:

```typescript
memories: {
  list: (personaId: string) => `/api/personas/${encodeURIComponent(personaId)}/memories`,
  detail: (id: string) => `/api/memories/${encodeURIComponent(id)}`,
  confirm: (id: string) => `/api/memories/${encodeURIComponent(id)}/confirm`,
  reject: (id: string) => `/api/memories/${encodeURIComponent(id)}/reject`,
  disable: (id: string) => `/api/memories/${encodeURIComponent(id)}/disable`
}
```

Add `ROUTES.personaMemories(id)`.

Create `frontend/src/lib/memories.ts` with the API helper functions and exact PRD enum unions.

- [ ] **Step 4: Implement memory audit page**

Create `frontend/app/personas/[id]/memories/page.tsx` with:

- signed-out, loading, ready, and error states consistent with uploads/jobs pages;
- links back to workbench and uploads/jobs;
- status/category/confidence filters;
- card list showing title, content, category, status, confidence, source quote, source location, source type, and source material id;
- actions: confirm, edit title/content, reject, disable, delete;
- copy from PRD: “这些是我从资料中整理出的记忆。你可以确认、修改或划掉它们。你修正后的内容，会立刻影响 TA 之后的回复。”;
- a clear note that chat/trust recalculation is not implemented until later milestones.

Use compact workbench styling and avoid nested decorative cards.

- [ ] **Step 5: Link from persona workbench**

Update `frontend/app/personas/[id]/page.tsx` to add a `Review memories` action and update scope copy from “memory review remains outside this task” to “memory review is available; conversation, voice, avatar, export remain later milestones.”

- [ ] **Step 6: Run frontend checks**

Run:

```powershell
npm.cmd --prefix frontend run test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
```

Expected: tests/lint/build pass and build includes `/personas/[id]/memories`.

- [ ] **Step 7: Commit**

```powershell
git add frontend/src/lib/api.ts frontend/src/lib/routes.ts frontend/src/lib/memories.ts frontend/app/personas/[id]/memories/page.tsx frontend/app/personas/[id]/page.tsx frontend/tests/memories.test.mjs frontend/tests/routes.test.mjs
git commit -m "feat: add memory audit frontend"
```

---

### Task 4: Docs, Harness Evidence, And Final Review

**Files:**
- Modify: `docs/README.md`
- Modify: `docs/feature-list.json`
- Modify: `docs/progress.md`
- Modify: `docs/prd-checklist.md`
- Modify: `docs/平台说明.md`
- Modify if needed: `docs/init.sh`
- Modify if needed: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: verified backend and frontend Milestone 3 behavior from Tasks 1-3.
- Produces: docs truth surface that states Milestone 3 is implemented only to the verified mock-provider extent.

- [ ] **Step 1: Write/update PRD checklist rows first**

Add Milestone 3 rows:

- uploaded/manual demo materials generate `ParsedChunk` and `MemoryCard`;
- OCR/ASR/VLM/video behavior is deterministic mock provider output, not real model quality;
- every memory has `source_material_id`, `source_quote`, and `source_location`;
- memory list/detail are user-scoped;
- memory confirm/edit/reject/disable/delete are implemented;
- frontend `/personas/{id}/memories` supports filters and audit actions;
- chat/trust/profile recalculation remain later milestones.

- [ ] **Step 2: Run baseline verification before broad docs sync**

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

Expected: all exit 0 before marking docs complete.

- [ ] **Step 3: Sync docs truth surface**

Update:

- `docs/README.md`: current state and residual risk now include Milestone 3 mock parsing/memory audit.
- `docs/feature-list.json`: add `feat-007` with dependencies on `feat-006`, status `completed`, and evidence files/commands.
- `docs/progress.md`: current state, latest update, evidence, risks, next milestone.
- `docs/平台说明.md`: user flow now includes generated memory cards and audit actions.
- `frontend/app/page.tsx` and `docs/init.sh` only if visible milestone copy is stale.

- [ ] **Step 4: Final verification**

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
```

Expected: all exit 0; `git diff --check` may print existing CRLF warnings but must exit 0.

- [ ] **Step 5: Commit**

```powershell
git add docs/README.md docs/feature-list.json docs/progress.md docs/prd-checklist.md docs/平台说明.md docs/init.sh frontend/app/page.tsx
git commit -m "docs: sync Milestone 3 memory evidence"
```

- [ ] **Step 6: Final review gate**

Run the subagent-driven final review over the Milestone 3 task range. Fix Critical/Important findings, rerun the relevant checks, and only then mark Milestone 3 complete in `.superpowers/sdd/progress.md`.

---

## Self-Review

- Spec coverage: This plan covers Milestone 3 delivery items: text parsing, OCR/ASR/image/video mock parsing, memory extraction, memory cards, and audit dashboard. Real provider quality, profile/trust recalculation, chat memory retrieval, voice, avatar, story/export, and full Demo polish are intentionally excluded by later milestones.
- Placeholder scan: No task uses TBD/TODO/fill-in placeholders; each task has concrete files, interfaces, tests, commands, and expected outcomes.
- Type consistency: Memory category/status/confidence enums match PRD section 7.5; job statuses match PRD section 10.3; API paths match PRD section 9.5.
