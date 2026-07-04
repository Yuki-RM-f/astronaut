# Milestone 4 Profile And Trust Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement PRD Milestone 4 so confirmed/corrected memories can generate and edit a `PersonaProfile`, recalculate an explainable `trust_score`, show upload suggestions, and expose the profile summary to later chat prompt context.

**Architecture:** Reuse the existing `persona_profiles` and `personas.trust_score` schema. Backend owns profile aggregation, trust component calculation, profile edit/regenerate/recalculate APIs, and synchronous recalculation after memory audit actions. Frontend owns `/personas/{id}/profile` and workbench trust display. Docs sync stays last and records only verified behavior.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, Next.js, React, TypeScript, Tailwind CSS, Node test runner.

## Global Constraints

- Follow `docs/可信人格记忆Agent_mvp_prd.md` Milestone 4 only; do not implement Milestone 5 chat/vector retrieval, Milestone 6 voice/TTS, Milestone 7 avatar/3D, Milestone 8 story/export, public community, payment, or advanced compliance.
- Profile aggregation must use active `MemoryCard` rows and prefer `confirmed`/`corrected` memories over `pending_review` or `auto_generated`; `rejected`, `disabled`, and deleted memories must not enter the generated profile.
- Profile dimensions are exactly: `basic_facts`, `relationships`, `preferences`, `habits`, `expression_style`, `shared_events`, `values_json`, and `emotional_patterns`.
- Profile dimension entries must retain source memory IDs so the UI can show provenance.
- User profile edits through PATCH are allowed for each dimension and `profile_summary`; do not require a real model provider.
- Trust score must be explainable and deterministic, range `0..100`, and stored on `personas.trust_score`.
- Trust dimensions follow PRD weights: material coverage 25%, memory review rate 25%, source traceability 20%, expression habit completeness 15%, multimodal completeness 15%.
- Memory confirm/edit/reject/disable/delete actions must immediately refresh profile/trust enough that a subsequent persona/profile request sees the changed score.
- The profile summary returned in `PersonaRead.prompt_context.profile_summary` must reflect the current `PersonaProfile`.
- If API-triggered profile/trust recalculation creates jobs, they must use existing `ai_jobs` statuses and stay visible on the jobs page; synchronous memory audit recalculation may update records directly.
- Verification must include backend tests, frontend tests, lint, build, `docker compose config`, `docs/init.sh`, and `git diff --check`.

---

## File Structure

- `backend/app/schemas/profile.py`: profile read/update and trust report schemas.
- `backend/app/services/profile.py`: profile aggregation, trust score calculation, suggestions, and job recording helpers.
- `backend/app/api/routes/profile.py`: `GET/PATCH/POST /api/personas/{id}/profile` and `POST /api/personas/{id}/recalculate-trust`.
- `backend/app/api/routes/memories.py`: call profile/trust refresh after audit status/content/delete changes.
- `backend/app/main.py`: include profile router.
- `backend/tests/test_profile.py`: profile generation/edit/regenerate/trust/user-scope tests.
- `backend/tests/test_memories.py`: add regression that memory audit changes trust score immediately.
- `frontend/src/lib/api.ts`: profile and recalculate-trust API paths.
- `frontend/src/lib/routes.ts`: `personaProfile(id)` route helper.
- `frontend/src/lib/profile.ts`: profile/trust types, labels, API helpers.
- `frontend/app/personas/[id]/profile/page.tsx`: profile and trust dashboard/editor.
- `frontend/app/personas/[id]/page.tsx`: link to profile page, show trust level/suggestions summary.
- `frontend/tests/profile.test.mjs`: trust level/helper tests.
- `frontend/tests/routes.test.mjs`: profile route/API path tests.
- `docs/README.md`, `docs/feature-list.json`, `docs/progress.md`, `docs/prd-checklist.md`, `docs/平台说明.md`: sync Milestone 4 facts and evidence after verification passes.
- `docs/init.sh`, `frontend/app/page.tsx`: update visible milestone copy if stale.

---

### Task 1: Backend Profile Aggregation And Trust API

**Files:**
- Create: `backend/app/schemas/profile.py`
- Create: `backend/app/services/profile.py`
- Create: `backend/app/api/routes/profile.py`
- Modify: `backend/app/api/routes/memories.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_profile.py`
- Modify: `backend/tests/test_memories.py`

**Interfaces:**
- Consumes: Milestone 3 `MemoryCard`, `SourceMaterial`, `PersonaProfile`, `AIJob`, and persona ownership.
- Produces: `GET /api/personas/{id}/profile`, `PATCH /api/personas/{id}/profile`, `POST /api/personas/{id}/profile/regenerate`, and `POST /api/personas/{id}/recalculate-trust`.
- Produces: `refresh_profile_and_trust(db: Session, persona: Persona) -> TrustReport`.
- Produces: `PersonaProfileRead` with profile dimensions, `profile_summary`, `source_memory_ids`, `trust_score`, trust component breakdown, trust level, and upload suggestions.

- [ ] **Step 1: Write failing backend profile tests**

Create `backend/tests/test_profile.py` with:

```python
def test_confirmed_memory_generates_profile_and_changes_trust(client):
    token = register_user(client, "m4-profile@example.com")
    persona = create_persona(client, token)
    create_manual_material(client, token, persona["id"])
    memories = client.get(f"/api/personas/{persona['id']}/memories", headers=auth(token)).json()["items"]
    before = client.get(f"/api/personas/{persona['id']}/profile", headers=auth(token)).json()
    confirmed = client.post(f"/api/memories/{memories[0]['id']}/confirm", headers=auth(token)).json()
    after = client.get(f"/api/personas/{persona['id']}/profile", headers=auth(token)).json()
    assert confirmed["status"] == "confirmed"
    assert after["trust_score"] > before["trust_score"]
    assert after["source_memory_ids"]
    assert after["profile_summary"]
```

Add tests for:

- `PATCH /api/personas/{id}/profile` edits every dimension and `profile_summary`.
- `POST /api/personas/{id}/profile/regenerate` rebuilds from confirmed/corrected memories.
- `POST /api/personas/{id}/recalculate-trust` returns score, components, level, suggestions, and creates a succeeded `calculate_trust_score` job.
- user scoping rejects another user reading/editing/regenerating/recalculating the profile.
- disabled/rejected/deleted memories do not enter the generated profile.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_profile.py -q`

Expected: FAIL because profile schemas/routes/services do not exist.

- [ ] **Step 3: Implement profile schemas**

Create `backend/app/schemas/profile.py`:

- `ProfileDimensionEntry`: `memory_id`, `title`, `content`, `category`, `confidence_level`, `status`.
- `TrustComponent`: `name`, `score`, `weight`, `weighted_score`, `evidence`.
- `TrustReport`: `trust_score`, `trust_level`, `components`, `suggestions`.
- `PersonaProfileRead`: profile DB fields plus trust report fields.
- `PersonaProfileUpdate`: optional `basic_facts`, `relationships`, `preferences`, `habits`, `expression_style`, `shared_events`, `values_json`, `emotional_patterns`, `profile_summary`.

Validate profile dimension values are JSON-compatible lists/dicts; reject explicit null update values.

- [ ] **Step 4: Implement aggregation and trust service**

Create `backend/app/services/profile.py`:

- `get_or_create_profile(db, persona)`.
- `build_profile_from_memories(db, persona)` using only `confirmed` and `corrected` non-deleted memories.
- Map categories to dimensions:
  - `basic_fact` -> `basic_facts`
  - `relationship` -> `relationships`
  - `preference` -> `preferences`
  - `habit` -> `habits`
  - `expression_style` -> `expression_style`
  - `shared_event` and `story_material` -> `shared_events`
  - `value` -> `values_json`
  - `emotional_pattern` -> `emotional_patterns`
  - `unknown` -> omit from generated dimensions
- `profile_summary` should be a compact deterministic sentence/paragraph from persona name plus the highest-priority confirmed/corrected entries.
- `source_memory_ids` should be a dict keyed by dimension with memory id lists.
- `calculate_trust_report(db, persona)` using PRD weights:
  - material coverage: score by material count and type diversity.
  - memory review rate: confirmed/corrected active memories divided by active memories.
  - source traceability: active memories with `source_quote` and `source_location`.
  - expression habit completeness: expression memories plus persona speaking/calling style fields.
  - multimodal completeness: material types text/manual, image, audio, video; voice/avatar unavailable in this milestone should lower but not block score.
- `refresh_profile_and_trust(db, persona)` updates `PersonaProfile` and `Persona.trust_score`.
- `record_profile_job` creates succeeded `AIJob` rows for explicit regenerate/recalculate endpoints with job types `update_profile` and `calculate_trust_score`.

Keep all logic deterministic and local.

- [ ] **Step 5: Implement routes and memory hooks**

Create `backend/app/api/routes/profile.py`:

- Use `get_persona_or_404` from `app.services.materials`.
- `GET /personas/{persona_id}/profile`: return current profile/trust, creating an empty profile if needed.
- `PATCH /personas/{persona_id}/profile`: update provided dimensions/summary and refresh trust score.
- `POST /personas/{persona_id}/profile/regenerate`: rebuild from confirmed/corrected memories, create succeeded `update_profile` job, return profile.
- `POST /personas/{persona_id}/recalculate-trust`: update trust score, create succeeded `calculate_trust_score` job, return trust report/profile.

Register router in `backend/app/main.py`.

Modify `backend/app/api/routes/memories.py` so update/confirm/reject/disable/delete call `refresh_profile_and_trust` before commit/response, ensuring the next persona/profile read sees updated trust/profile.

- [ ] **Step 6: Run backend checks**

Run:

```powershell
python -m pytest backend/tests/test_profile.py backend/tests/test_memories.py -q
python -m pytest backend/tests -q
```

Expected: focused tests pass; full backend suite passes.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/schemas/profile.py backend/app/services/profile.py backend/app/api/routes/profile.py backend/app/api/routes/memories.py backend/app/main.py backend/tests/test_profile.py backend/tests/test_memories.py
git commit -m "feat: add profile and trust API"
```

---

### Task 2: Frontend Profile And Trust Dashboard

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/routes.ts`
- Create: `frontend/src/lib/profile.ts`
- Create: `frontend/app/personas/[id]/profile/page.tsx`
- Modify: `frontend/app/personas/[id]/page.tsx`
- Create: `frontend/tests/profile.test.mjs`
- Modify: `frontend/tests/routes.test.mjs`

**Interfaces:**
- Consumes: Task 1 profile/trust APIs.
- Produces: `ROUTES.personaProfile(id)`.
- Produces: `getPersonaProfile`, `updatePersonaProfile`, `regeneratePersonaProfile`, `recalculateTrust`, trust level labels, component labels, and suggestion helpers.

- [ ] **Step 1: Write failing frontend tests**

Create `frontend/tests/profile.test.mjs`:

```javascript
import test from "node:test";
import assert from "node:assert/strict";
import { trustLevelForScore, trustLevelLabel, profileDimensionLabel } from "../src/lib/profile";

test("trust level helper follows PRD score bands", () => {
  assert.equal(trustLevelForScore(0), "initial");
  assert.equal(trustLevelForScore(31), "usable");
  assert.equal(trustLevelForScore(61), "trusted");
  assert.equal(trustLevelForScore(81), "high_trust");
  assert.equal(trustLevelLabel("high_trust"), "High trust");
});

test("profile dimension labels cover PRD dimensions", () => {
  assert.equal(profileDimensionLabel("basic_facts"), "Basic facts");
  assert.equal(profileDimensionLabel("emotional_patterns"), "Emotional patterns");
});
```

Update `frontend/tests/routes.test.mjs` to assert `/personas/{id}/profile`, profile API paths, regenerate, and recalculate-trust paths.

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm.cmd --prefix frontend run test`

Expected: FAIL because profile helpers/routes do not exist.

- [ ] **Step 3: Implement frontend helpers**

Add API paths:

- `API_PATHS.profile.detail(personaId)`
- `API_PATHS.profile.regenerate(personaId)`
- `API_PATHS.profile.recalculateTrust(personaId)`

Add route helper `ROUTES.personaProfile(id)`.

Create `frontend/src/lib/profile.ts` with:

- profile/trust TypeScript types matching backend.
- trust level helper bands from PRD: `0-30 initial`, `31-60 usable`, `61-80 trusted`, `81-100 high_trust`.
- API helpers for GET/PATCH/regenerate/recalculate.
- label helpers for dimensions and components.

- [ ] **Step 4: Implement profile page**

Create `frontend/app/personas/[id]/profile/page.tsx` with existing workbench page patterns:

- signed-out/loading/error/ready states.
- links back to workbench and memory audit.
- trust score summary, trust level copy, component breakdown, and upload suggestions.
- profile dimension sections showing entries and source memory ids.
- editable `profile_summary` and dimension JSON textareas or compact text inputs; keep validation simple and explicit.
- buttons for Save profile, Regenerate from reviewed memories, and Recalculate trust.
- clear bounded copy: “Chat will read this profile summary in Milestone 5; no chat behavior is implemented here.”

- [ ] **Step 5: Update workbench**

Update `frontend/app/personas/[id]/page.tsx`:

- add `Profile and trust` action.
- show trust score with trust level label and short upload suggestion if available from persona/profile helper only where data is loaded.
- remove stale copy saying trust recalculation remains later; keep chat/voice/avatar/export later.

- [ ] **Step 6: Run frontend checks**

Run:

```powershell
npm.cmd --prefix frontend run test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
```

Expected: tests/lint/build pass and build includes `/personas/[id]/profile`.

- [ ] **Step 7: Commit**

```powershell
git add frontend/src/lib/api.ts frontend/src/lib/routes.ts frontend/src/lib/profile.ts frontend/app/personas/[id]/profile/page.tsx frontend/app/personas/[id]/page.tsx frontend/tests/profile.test.mjs frontend/tests/routes.test.mjs
git commit -m "feat: add profile trust frontend"
```

---

### Task 3: Docs, Evidence, And Review

**Files:**
- Modify: `docs/README.md`
- Modify: `docs/feature-list.json`
- Modify: `docs/progress.md`
- Modify: `docs/prd-checklist.md`
- Modify: `docs/平台说明.md`
- Modify if needed: `docs/init.sh`
- Modify if needed: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: verified backend/frontend Milestone 4 behavior.
- Produces: docs truth surface that states Milestone 4 profile/trust is implemented only to the deterministic local calculation extent.

- [ ] **Step 1: Update PRD checklist first**

Add Milestone 4 rows:

- `PersonaProfile` generated from confirmed/corrected memories.
- profile dimensions retain source memory IDs.
- profile GET/PATCH/regenerate APIs are user-scoped.
- trust score recalculates after memory audit.
- trust score uses explainable PRD weighted components.
- frontend `/personas/{id}/profile` displays and edits profile/trust/suggestions.
- chat reads `prompt_context.profile_summary` when future chat is implemented, but Milestone 5 chat itself remains pending.

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

- `docs/README.md`: current state and residual risk include Milestone 4 profile/trust.
- `docs/feature-list.json`: add `feat-008` with dependency on `feat-007`, status `completed`, and evidence.
- `docs/progress.md`: current state, latest update, evidence, risks, and next milestone.
- `docs/平台说明.md`: user flow now includes profile/trust page and upload suggestions.
- `docs/init.sh` and `frontend/app/page.tsx` only if visible milestone copy is stale.

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
git commit -m "docs: sync Milestone 4 profile trust evidence"
```

- [ ] **Step 6: Review gate**

Generate a review package for the task range, dispatch a scoped reviewer, and fix all Critical/Important findings before marking Milestone 4 complete in `.superpowers/sdd/progress.md`.

---

## Self-Review

- Spec coverage: This plan covers Milestone 4 delivery items: PersonaProfile aggregation, trust calculation, trust display, upload suggestions, editable profile, profile prompt context readiness, and audit-triggered trust changes.
- Scope boundaries: The plan explicitly excludes chat, vector retrieval, voice/TTS, avatar/3D, story/export, and full Demo polish.
- Type consistency: Profile dimensions match PRD section 7.6 and existing `persona_profiles` columns; trust weights match PRD section 7.7; API paths match PRD sections 9.2 and 9.6.
