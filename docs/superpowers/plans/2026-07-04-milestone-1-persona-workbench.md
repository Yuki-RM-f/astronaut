# Milestone 1 Persona Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement PRD Milestone 1 so an authenticated user can create supported persona types, list them, open a persona workbench, edit relationship/calling settings, and expose persona settings for later Agent prompts.

**Architecture:** Reuse the Milestone 0 FastAPI/JWT foundation and existing PRD schema. Backend owns authenticated persona APIs, workbench statistics, and prompt-context assembly. Frontend owns auth form wiring, persona list/create/detail pages, and client-side required-field validation. Docs/harness updates remain last so they reflect verified implementation facts.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, Next.js, React, TypeScript, Tailwind CSS, Node test runner.

## Global Constraints

- Follow `docs/可信人格记忆Agent_mvp_prd.md` Milestone 1 only; do not implement uploads, parsing, memory extraction, chat, voice, TTS, voice clone, avatar generation, export, public community, payment, or advanced compliance.
- Supported persona types for Milestone 1 are exactly `deceased_relative`, `living_relative`, `public_figure`, and `fictional_character`; `expert_role` remains reserved and must not be accepted.
- Creating a persona must require `name`, `persona_type`, `relationship_to_user`, `user_nickname_by_persona`, `gender`, `language`, `status`, `short_bio`, `speaking_style`, `emotional_style`, and `forbidden_expressions`.
- Persona workbench statistics may use zero counts until Milestone 2/3 records exist, but must be derived from persisted rows when records exist.
- Persona APIs must be scoped to the authenticated user; one user must not read, update, list, or delete another user’s personas.
- Prompt context must expose persona settings needed by the PRD chat prompt: persona name/type, relationship, user nickname, speaking style, emotional style, forbidden expressions, and profile summary placeholder.
- Frontend forms must block missing required persona fields before submission.
- Frontend copy must not claim upload, memory, voice, chat, or 3D features are implemented.
- Keep `.env/runtime.env` uncommitted and do not print or commit real secrets.
- Verification must include backend tests, frontend tests, lint, build, `docker compose config`, and `docs/init.sh`.

---

## File Structure

- `backend/app/schemas/persona.py`: persona request/response schemas, enum validation, workbench stats shape.
- `backend/app/services/persona_prompt.py`: prompt-context builder for persona settings.
- `backend/app/api/routes/personas.py`: authenticated persona list/create/detail/update/delete routes.
- `backend/app/main.py`: include persona router.
- `backend/tests/test_personas.py`: authenticated persona API coverage.
- `backend/tests/test_persona_prompt.py`: prompt-context coverage.
- `frontend/src/lib/routes.ts`: persona route helpers.
- `frontend/src/lib/api.ts`: persona/auth API paths and request helper.
- `frontend/src/lib/auth.ts`: browser token session helpers.
- `frontend/src/lib/persona.ts`: persona enum labels, required fields, validation helper.
- `frontend/app/login/page.tsx`, `frontend/app/register/page.tsx`: enable auth form submission.
- `frontend/app/dashboard/page.tsx`: show persona list entry point.
- `frontend/app/personas/new/page.tsx`: four-step PRD-aligned create form.
- `frontend/app/personas/[id]/page.tsx`: persona workbench basics and stats.
- `frontend/tests/routes.test.mjs`: expand route/API assertions.
- `frontend/tests/persona.test.mjs`: validate required persona fields and supported types.
- `docs/README.md`, `docs/feature-list.json`, `docs/progress.md`, `docs/prd-checklist.md`, `docs/平台说明.md`: sync Milestone 1 facts and evidence after checks pass.

---

### Task 1: Backend Persona API And Prompt Context

**Files:**
- Create: `backend/app/schemas/persona.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/persona_prompt.py`
- Create: `backend/app/api/routes/personas.py`
- Create: `backend/tests/test_personas.py`
- Create: `backend/tests/test_persona_prompt.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `get_current_user`, `get_db`, `Persona`, `SourceMaterial`, `MemoryCard`, `Conversation`, and `PersonaProfile`.
- Produces: `GET /api/personas`, `POST /api/personas`, `GET /api/personas/{id}`, `PATCH /api/personas/{id}`, `DELETE /api/personas/{id}`.
- Produces: `build_persona_prompt_context(persona, profile=None) -> dict[str, str]`.

- [ ] **Step 1: Write failing backend tests**

Add tests that:

```python
def test_create_list_detail_and_update_persona(client):
    token = register_user(client, "owner@example.com")
    created = create_persona(client, token, persona_type="deceased_relative")
    assert created["name"] == "外婆"
    assert created["relationship_to_user"] == "外婆"
    assert created["user_nickname_by_persona"] == "小铭"
    assert created["stats"]["materials_count"] == 0

    listed = client.get("/api/personas", headers=auth(token))
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [created["id"]]

    patched = client.patch(
        f"/api/personas/{created['id']}",
        headers=auth(token),
        json={"relationship_to_user": "奶奶", "user_nickname_by_persona": "小明"},
    )
    assert patched.status_code == 200
    assert patched.json()["relationship_to_user"] == "奶奶"
    assert patched.json()["prompt_context"]["user_nickname_by_persona"] == "小明"
```

```python
def test_supported_persona_types_and_rejects_reserved_expert_role(client):
    token = register_user(client, "types@example.com")
    for persona_type in ["deceased_relative", "living_relative", "public_figure", "fictional_character"]:
        assert create_persona(client, token, persona_type=persona_type)["persona_type"] == persona_type

    response = client.post("/api/personas", headers=auth(token), json=persona_payload(persona_type="expert_role"))
    assert response.status_code == 422
```

```python
def test_persona_access_is_user_scoped(client):
    owner_token = register_user(client, "owner@example.com")
    other_token = register_user(client, "other@example.com")
    persona = create_persona(client, owner_token)

    assert client.get(f"/api/personas/{persona['id']}", headers=auth(other_token)).status_code == 404
    assert client.patch(f"/api/personas/{persona['id']}", headers=auth(other_token), json={"name": "x"}).status_code == 404
    assert client.delete(f"/api/personas/{persona['id']}", headers=auth(other_token)).status_code == 404
```

```python
def test_prompt_context_uses_persona_relationship_and_calling_settings():
    persona = Persona(
        name="外婆",
        persona_type="deceased_relative",
        relationship_to_user="外婆",
        user_nickname_by_persona="小铭",
        speaking_style="温柔、慢慢说",
        emotional_style="安慰、鼓励",
        forbidden_expressions="不要说我真的回来了",
    )
    context = build_persona_prompt_context(persona)
    assert context["persona_name"] == "外婆"
    assert context["user_nickname_by_persona"] == "小铭"
    assert "我真的回来了" in context["forbidden_expressions"]
```

- [ ] **Step 2: Run backend tests to verify RED**

Run: `python -m pytest backend/tests/test_personas.py backend/tests/test_persona_prompt.py -q`

Expected: FAIL because persona routes, schemas, and prompt service do not exist yet.

- [ ] **Step 3: Implement backend persona routes and service**

Implement only the Task 1 files. Use authenticated user scoping on every route. Use soft delete by setting `deleted_at`. Use `select(func.count(...))` for stats from existing tables. Return `prompt_context` in detail/create/update responses.

- [ ] **Step 4: Run backend verification**

Run:

```bash
python -m pytest backend/tests/test_personas.py backend/tests/test_persona_prompt.py -q
python -m pytest backend/tests -q
```

Expected: all backend tests pass.

- [ ] **Step 5: Commit Task 1**

Run:

```bash
git add backend/app/main.py backend/app/api/routes/personas.py backend/app/schemas/persona.py backend/app/services backend/tests/test_personas.py backend/tests/test_persona_prompt.py
git commit -m "feat: add persona workbench API"
```

---

### Task 2: Frontend Auth Flow And Persona Pages

**Files:**
- Modify: `frontend/src/lib/routes.ts`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/auth.ts`
- Create: `frontend/src/lib/persona.ts`
- Modify: `frontend/app/login/page.tsx`
- Modify: `frontend/app/register/page.tsx`
- Modify: `frontend/app/dashboard/page.tsx`
- Create: `frontend/app/personas/new/page.tsx`
- Create: `frontend/app/personas/[id]/page.tsx`
- Modify: `frontend/tests/routes.test.mjs`
- Create: `frontend/tests/persona.test.mjs`

**Interfaces:**
- Consumes: Task 1 persona APIs and Milestone 0 auth APIs.
- Produces: browser auth session helpers, persona create form, dashboard persona list, and persona detail/workbench page.

- [ ] **Step 1: Write failing frontend tests**

Add route and persona validation tests:

```javascript
test("Milestone 1 persona routes are exposed", () => {
  assert.equal(ROUTES.personasNew, "/personas/new");
  assert.equal(ROUTES.personaDetail("abc"), "/personas/abc");
});
```

```javascript
test("persona form validation requires PRD Milestone 1 fields", () => {
  const result = validatePersonaDraft({ name: "", persona_type: "deceased_relative" });
  assert.equal(result.ok, false);
  assert.ok(result.missingFields.includes("name"));
  assert.ok(result.missingFields.includes("user_nickname_by_persona"));
});
```

```javascript
test("reserved expert role is not a create option", () => {
  assert.deepEqual(
    PERSONA_TYPE_OPTIONS.map((option) => option.value),
    ["deceased_relative", "living_relative", "public_figure", "fictional_character"],
  );
});
```

- [ ] **Step 2: Run frontend tests to verify RED**

Run: `npm.cmd --prefix frontend run test`

Expected: FAIL because persona validation helpers and routes do not exist yet.

- [ ] **Step 3: Implement frontend auth and persona pages**

Enable login/register form submission to store the JWT token in `localStorage`. Dashboard should fetch `/api/personas` when a token exists and render persona cards. The create page must block missing required fields before POST. The detail page must fetch `/api/personas/{id}` and show relationship, calling name, speaking style, emotional style, forbidden expressions, trust score, and basic stats.

- [ ] **Step 4: Run frontend verification**

Run:

```bash
npm.cmd --prefix frontend run test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
```

Expected: all frontend checks pass.

- [ ] **Step 5: Commit Task 2**

Run:

```bash
git add frontend/src/lib frontend/app frontend/tests
git commit -m "feat: add persona frontend workflow"
```

---

### Task 3: Milestone 1 Docs And Harness Sync

**Files:**
- Modify: `docs/README.md`
- Modify: `docs/feature-list.json`
- Modify: `docs/progress.md`
- Modify: `docs/prd-checklist.md`
- Modify: `docs/平台说明.md`
- Modify: `AGENTS.md` only if commands or agent workflow changed.

**Interfaces:**
- Consumes: verified Task 1 and Task 2 behavior.
- Produces: docs truth surface for Milestone 1 and updated evidence.

- [ ] **Step 1: Update checklist first**

Update `docs/prd-checklist.md` with Milestone 1 acceptance rows:

- supported persona types can be created;
- reserved `expert_role` rejected;
- persona APIs are user-scoped;
- prompt context exposes relationship and user nickname;
- frontend required-field validation blocks incomplete persona drafts;
- dashboard/new/detail persona routes build.

- [ ] **Step 2: Run current verification before docs edits**

Run:

```bash
python -m json.tool docs/feature-list.json
python -m pytest backend/tests -q
npm.cmd --prefix frontend run test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
docker compose config
& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh
```

Expected: all commands exit 0.

- [ ] **Step 3: Sync docs**

Update `feature-list.json` with a completed Milestone 1 feature after verification. Update `progress.md` with current state, evidence, risks, and next step: Milestone 2资料上传与任务队列. Update README and 平台说明 only for actual persona/auth workflow facts. Do not claim uploads, memory extraction, voice, chat, or 3D features.

- [ ] **Step 4: Run full verification after docs edits**

Run the same commands from Step 2 again.

Expected: all commands exit 0.

- [ ] **Step 5: Commit Task 3**

Run:

```bash
git add docs AGENTS.md
git commit -m "docs: sync Milestone 1 persona evidence"
```

---

## Self-Review Notes

- Spec coverage: this plan covers PRD Milestone 1 only. It does not implement Milestone 2 uploads or any AI/media capability.
- Scope guard: `expert_role` remains reserved; upload, memory, chat, voice, avatar, and export routes remain absent or marked unavailable.
- Verification shape: every implementation task has test-first RED/GREEN checks, and docs update comes after verified code.
