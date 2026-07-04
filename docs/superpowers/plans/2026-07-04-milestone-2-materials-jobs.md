# Milestone 2 Materials And Jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement PRD Milestone 2 so an authenticated user can upload text/image/audio/video materials, add manual material, persist `SourceMaterial`, create AI jobs, and view/retry/cancel task statuses.

**Architecture:** Backend owns material persistence, local storage fallback, AI job creation, status transitions, and user-scoped APIs. Frontend owns persona upload and job status pages that consume the backend contracts. Docs/harness updates remain last so they reflect verified implementation facts.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, local file storage fallback, Next.js, React, TypeScript, Tailwind CSS, Node test runner.

## Global Constraints

- Follow `docs/可信人格记忆Agent_mvp_prd.md` Milestone 2 only; do not implement OCR, ASR, VLM, memory extraction, embeddings, chat, voice clone, TTS, avatar generation, export, public community, payment, or advanced compliance.
- Supported material types for Milestone 2 are exactly `text`, `image`, `audio`, `video`, and `manual`.
- Upload endpoints must create `SourceMaterial` rows and at least one `AIJob` per file/manual material.
- Job statuses must be limited to `pending`, `running`, `succeeded`, `failed`, `retrying`, and `canceled`.
- Initial upload/manual jobs should default to `pending`; retry moves non-running jobs to `retrying` and increments `retry_count`; cancel moves pending/running/retrying jobs to `canceled`.
- APIs must be scoped to the authenticated user; one user must not read, delete, retry, or cancel another user’s materials/jobs.
- File storage may use local `storage/materials/...` fallback while keeping MinIO/S3 configuration in place; do not require real MinIO credentials for local tests.
- Frontend pages must not claim actual parsing/OCR/ASR/memory extraction is implemented; they may show queued mock/parse jobs and statuses.
- Keep `.env/runtime.env` uncommitted and do not print or commit real secrets.
- Verification must include backend tests, frontend tests, lint, build, `docker compose config`, and `docs/init.sh`.

---

## File Structure

- `backend/app/schemas/material.py`: material request/response schemas.
- `backend/app/schemas/job.py`: AI job response/status schemas.
- `backend/app/services/materials.py`: material type inference, local storage, job type mapping.
- `backend/app/api/routes/materials.py`: material upload/manual/list/detail/delete/reparse routes.
- `backend/app/api/routes/jobs.py`: persona job list, job detail, retry, cancel routes.
- `backend/app/main.py`: include material and job routers.
- `backend/requirements.txt`: add multipart upload dependency if missing.
- `backend/tests/test_materials.py`: upload/manual/list/detail/delete/reparse coverage.
- `backend/tests/test_jobs.py`: job list/detail/retry/cancel coverage.
- `frontend/src/lib/routes.ts`: upload and job route helpers.
- `frontend/src/lib/api.ts`: material/job API paths.
- `frontend/src/lib/materials.ts`: material type labels, client helpers, validation.
- `frontend/src/lib/jobs.ts`: job status labels/helpers.
- `frontend/app/personas/[id]/uploads/page.tsx`: upload/manual material page.
- `frontend/app/personas/[id]/jobs/page.tsx`: job status page.
- `frontend/app/personas/[id]/page.tsx`: link to uploads/jobs.
- `frontend/tests/materials.test.mjs`: material helper tests.
- `frontend/tests/routes.test.mjs`: route/API path tests.
- `docs/README.md`, `docs/feature-list.json`, `docs/progress.md`, `docs/prd-checklist.md`, `docs/平台说明.md`: sync Milestone 2 facts and evidence after checks pass.

---

### Task 1: Backend Materials And AI Jobs API

**Files:**
- Create: `backend/app/schemas/material.py`
- Create: `backend/app/schemas/job.py`
- Create: `backend/app/services/materials.py`
- Create: `backend/app/api/routes/materials.py`
- Create: `backend/app/api/routes/jobs.py`
- Create: `backend/tests/test_materials.py`
- Create: `backend/tests/test_jobs.py`
- Modify: `backend/app/main.py`
- Modify: `backend/requirements.txt`

**Interfaces:**
- Consumes: authenticated persona ownership from Milestone 1.
- Produces: `POST /api/personas/{id}/materials/upload`, `POST /api/personas/{id}/materials/manual`, `GET /api/personas/{id}/materials`, `GET /api/materials/{id}`, `DELETE /api/materials/{id}`, `POST /api/materials/{id}/parse`.
- Produces: `GET /api/personas/{id}/jobs`, `GET /api/jobs/{id}`, `POST /api/jobs/{id}/retry`, `POST /api/jobs/{id}/cancel`.

- [ ] **Step 1: Write failing backend tests**

Add tests that:

```python
def test_upload_text_image_audio_video_creates_materials_and_jobs(client):
    token = register_user(client, "materials@example.com")
    persona = create_persona(client, token)
    files = [
        ("files", ("note.txt", b"hello", "text/plain")),
        ("files", ("photo.jpg", b"jpg", "image/jpeg")),
        ("files", ("voice.mp3", b"mp3", "audio/mpeg")),
        ("files", ("clip.mp4", b"mp4", "video/mp4")),
    ]
    response = client.post(
        f"/api/personas/{persona['id']}/materials/upload",
        headers=auth(token),
        files=files,
        data={"importance": "important", "user_description": "demo batch"},
    )
    assert response.status_code == 201
    items = response.json()["items"]
    assert [item["file_type"] for item in items] == ["text", "image", "audio", "video"]
    assert all(item["parse_status"] == "pending" for item in items)
    assert all(item["jobs"] for item in items)
```

```python
def test_manual_material_creates_pending_parse_job(client):
    token = register_user(client, "manual@example.com")
    persona = create_persona(client, token)
    response = client.post(
        f"/api/personas/{persona['id']}/materials/manual",
        headers=auth(token),
        json={"manual_text": "外婆喜欢包馄饨", "importance": "very_important"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["file_type"] == "manual"
    assert body["jobs"][0]["status"] == "pending"
```

```python
def test_jobs_are_user_scoped_and_retry_cancel_statuses(client):
    owner_token = register_user(client, "owner@example.com")
    other_token = register_user(client, "other@example.com")
    persona = create_persona(client, owner_token)
    material = create_manual_material(client, owner_token, persona["id"])
    job_id = material["jobs"][0]["id"]

    assert client.get(f"/api/jobs/{job_id}", headers=auth(other_token)).status_code == 404
    retry = client.post(f"/api/jobs/{job_id}/retry", headers=auth(owner_token))
    assert retry.status_code == 200
    assert retry.json()["status"] == "retrying"
    cancel = client.post(f"/api/jobs/{job_id}/cancel", headers=auth(owner_token))
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "canceled"
```

- [ ] **Step 2: Run backend tests to verify RED**

Run: `python -m pytest backend/tests/test_materials.py backend/tests/test_jobs.py -q`

Expected: FAIL because material/job routes and schemas do not exist yet.

- [ ] **Step 3: Implement backend material/job routes**

Implement local file storage under `storage/materials/{user_id}/{persona_id}/{material_id}-{file_name}`. Infer file type from MIME type and filename extension. Reject unsupported files with 400. Create one initial job per material with job type mapping: `text/manual -> parse_text`, `image -> ocr_image`, `audio -> asr_audio`, `video -> extract_video_audio`. Use user-scoped lookups on every route.

- [ ] **Step 4: Run backend verification**

Run:

```bash
python -m pytest backend/tests/test_materials.py backend/tests/test_jobs.py -q
python -m pytest backend/tests -q
```

Expected: all backend tests pass.

- [ ] **Step 5: Commit Task 1**

Run:

```bash
git add backend/app/main.py backend/app/api/routes/materials.py backend/app/api/routes/jobs.py backend/app/schemas/material.py backend/app/schemas/job.py backend/app/services/materials.py backend/requirements.txt backend/tests/test_materials.py backend/tests/test_jobs.py
git commit -m "feat: add material upload and job APIs"
```

---

### Task 2: Frontend Uploads And Jobs Pages

**Files:**
- Modify: `frontend/src/lib/routes.ts`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/materials.ts`
- Create: `frontend/src/lib/jobs.ts`
- Create: `frontend/app/personas/[id]/uploads/page.tsx`
- Create: `frontend/app/personas/[id]/jobs/page.tsx`
- Modify: `frontend/app/personas/[id]/page.tsx`
- Create: `frontend/tests/materials.test.mjs`
- Modify: `frontend/tests/routes.test.mjs`

**Interfaces:**
- Consumes: Task 1 material/job APIs.
- Produces: upload/manual material UI and job status page.

- [ ] **Step 1: Write failing frontend tests**

Add tests that:

```javascript
test("Milestone 2 routes are exposed", () => {
  assert.equal(ROUTES.personaUploads("p1"), "/personas/p1/uploads");
  assert.equal(ROUTES.personaJobs("p1"), "/personas/p1/jobs");
});
```

```javascript
test("material type helper accepts PRD Milestone 2 types only", () => {
  assert.deepEqual(MATERIAL_TYPE_OPTIONS.map((option) => option.value), ["text", "image", "audio", "video", "manual"]);
});
```

```javascript
test("job status helper exposes PRD statuses", () => {
  assert.deepEqual(JOB_STATUSES, ["pending", "running", "succeeded", "failed", "retrying", "canceled"]);
});
```

- [ ] **Step 2: Run frontend tests to verify RED**

Run: `npm.cmd --prefix frontend run test`

Expected: FAIL because material/job helpers and routes do not exist.

- [ ] **Step 3: Implement frontend upload/jobs pages**

Uploads page should allow file selection for text/image/audio/video, manual text entry, optional description/importance, and show existing materials. Jobs page should list job status, type, retry count, and expose retry/cancel buttons. Workbench page should link to uploads and jobs. Copy must state parsing is queued/mock until later milestones.

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
git add frontend/src/lib frontend/app/personas frontend/tests
git commit -m "feat: add materials and jobs frontend"
```

---

### Task 3: Milestone 2 Docs And Harness Sync

**Files:**
- Modify: `docs/README.md`
- Modify: `docs/feature-list.json`
- Modify: `docs/progress.md`
- Modify: `docs/prd-checklist.md`
- Modify: `docs/平台说明.md`
- Modify: `AGENTS.md` only if commands or agent workflow changed.

**Interfaces:**
- Consumes: verified Task 1 and Task 2 behavior.
- Produces: docs truth surface for Milestone 2 and updated evidence.

- [ ] **Step 1: Update checklist first**

Add Milestone 2 acceptance rows for upload/manual material creation, per-file AI job creation, job status visibility, retry/cancel behavior, user scoping, frontend upload/jobs pages, and local storage fallback.

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

Update feature ledger and handoff docs to describe Milestone 2 completed scope only. Do not claim parsing, OCR, ASR, memory card generation, chat, voice, or avatar capabilities are implemented.

- [ ] **Step 4: Run full verification after docs edits**

Run the same commands from Step 2 again.

Expected: all commands exit 0.

- [ ] **Step 5: Commit Task 3**

Run:

```bash
git add docs AGENTS.md
git commit -m "docs: sync Milestone 2 material evidence"
```

---

## Self-Review Notes

- Spec coverage: this plan covers PRD Milestone 2 only. It queues AI jobs but does not execute multimodal parsing or generate memories.
- Storage fallback: local storage is explicit so missing MinIO credentials do not block the MVP loop.
- Validation shape: every implementation task includes RED/GREEN focused checks plus full suite checks.
