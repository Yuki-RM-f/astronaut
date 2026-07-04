# Milestone 0 Project Initialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the PRD Milestone 0 foundation: Next.js frontend, FastAPI backend, PostgreSQL/Redis/MinIO Docker Compose, SQLAlchemy/Alembic/JWT auth skeleton, provider gateway mock, and docs-driven validation commands.

**Architecture:** Keep the first slice small and verifiable. The backend owns API, settings, SQLAlchemy models, auth, and provider gateway interfaces. The frontend owns route/layout scaffolding and API connectivity surfaces. Docker Compose wires the PRD services, while `docs/init.sh` remains the single harness entrypoint.

**Tech Stack:** Next.js, React, TypeScript, Tailwind CSS, FastAPI, SQLAlchemy, Alembic, JWT Auth, PostgreSQL, Redis, MinIO, Docker Compose, pytest.

## Global Constraints

- Follow `docs/可信人格记忆Agent_mvp_prd.md`; do not add public community, complex payment, complex compliance review, full-body motion capture, commercial livestream, or cinematic-realistic avatar features.
- Read `.env/runtime.env` for local runtime overrides, but never hardcode or commit real secrets.
- If a required runtime value is absent, use mock providers or safe defaults and document the fallback.
- Backend must use FastAPI, PostgreSQL, Redis, MinIO/S3, SQLAlchemy, Alembic, JWT Auth, AI Job model, and Provider Gateway abstraction.
- Frontend must use Next.js, React, TypeScript, Tailwind, and basic layout/page routing.
- AI capability work in Milestone 0 is interface-only with a mock provider; no real OCR/ASR/VLM/TTS/voice/avatar model calls.
- Database schema scaffolding must match PRD section 8 field names and statuses where represented.
- Auth acceptance: user can register, login, fetch current user, and receive JWT bearer access tokens.
- Frontend acceptance: login/register/dashboard routes build and display PRD-aligned baseline UI without claiming unfinished features.
- Validation must include JSON validation and `docs/init.sh`; backend and frontend checks must be added once their scaffolds exist.

---

## File Structure

- `backend/app/main.py`: FastAPI app, CORS, router registration, health endpoint.
- `backend/app/core/config.py`: settings loaded from `.env/runtime.env` and environment variables with safe defaults.
- `backend/app/core/security.py`: password hashing and JWT helpers.
- `backend/app/db/base.py`: SQLAlchemy base and timestamp mixins.
- `backend/app/db/session.py`: engine/session factory.
- `backend/app/models/*.py`: PRD schema model scaffolding.
- `backend/app/schemas/auth.py`: auth request/response schemas.
- `backend/app/api/deps.py`: database and current-user dependencies.
- `backend/app/api/routes/auth.py`: register, login, and me endpoints.
- `backend/app/providers/gateway.py`: AI capability/provider gateway abstraction with mock provider.
- `backend/app/worker.py`: mock worker process entrypoint.
- `backend/alembic/*`: Alembic migration configuration and initial schema.
- `backend/tests/*`: pytest coverage for settings, health, auth, models, and provider gateway.
- `frontend/app/*`: Next.js app router pages for home/login/register/dashboard.
- `frontend/src/lib/*`: API client and route constants.
- `frontend/tests/*`: frontend source-level tests for route/API config helpers.
- `docker-compose.yml`: PRD services for frontend, backend, postgres, redis, minio, and mock workers.
- `docs/README.md`, `docs/init.sh`, `docs/progress.md`, `docs/prd-checklist.md`, `docs/feature-list.json`, `docs/平台说明.md`, `AGENTS.md`: harness updates reflecting real commands and Milestone 0 status.

---

### Task 1: Backend Foundation, Schema, Auth, and Provider Gateway

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/security.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/persona.py`
- Create: `backend/app/models/source_material.py`
- Create: `backend/app/models/parsed_chunk.py`
- Create: `backend/app/models/memory_card.py`
- Create: `backend/app/models/persona_profile.py`
- Create: `backend/app/models/ai_job.py`
- Create: `backend/app/models/conversation.py`
- Create: `backend/app/models/voice_avatar.py`
- Create: `backend/app/models/audit_log.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/routes/__init__.py`
- Create: `backend/app/api/routes/auth.py`
- Create: `backend/app/providers/__init__.py`
- Create: `backend/app/providers/gateway.py`
- Create: `backend/app/worker.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/0001_initial_schema.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`
- Create: `backend/tests/test_auth.py`
- Create: `backend/tests/test_models.py`
- Create: `backend/tests/test_provider_gateway.py`

**Interfaces:**
- Produces: FastAPI `app` in `backend/app/main.py`.
- Produces: `/health`, `/api/auth/register`, `/api/auth/login`, `/api/auth/me`.
- Produces: `get_settings()` loading `.env/runtime.env` without exposing values.
- Produces: SQLAlchemy models for PRD tables.
- Produces: `ProviderGateway` with mock capability calls and no real model dependency.

- [ ] **Step 1: Install backend test dependencies only after test files exist**

Create test files that express expected behavior before implementation. At minimum:

```python
# backend/tests/test_health.py
from fastapi.testclient import TestClient

def test_health_reports_ok(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

```python
# backend/tests/test_auth.py
def test_register_login_and_current_user(client):
    register = client.post(
        "/api/auth/register",
        json={"email": "demo@example.com", "password": "passw0rd", "display_name": "Demo"},
    )
    assert register.status_code == 201
    token = register.json()["access_token"]

    login = client.post(
        "/api/auth/login",
        json={"email": "demo@example.com", "password": "passw0rd"},
    )
    assert login.status_code == 200

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "demo@example.com"
```

```python
# backend/tests/test_provider_gateway.py
import pytest
from app.providers.gateway import ProviderGateway

@pytest.mark.asyncio
async def test_mock_gateway_returns_capability_result():
    result = await ProviderGateway().run("chat_llm", {"message": "你好"})
    assert result["provider_name"] == "mock"
    assert result["capability"] == "chat_llm"
    assert result["status"] == "succeeded"
```

- [ ] **Step 2: Run backend tests to verify RED**

Run: `python -m pytest backend/tests -q`

Expected: FAIL because `app` modules and implementation do not exist yet.

- [ ] **Step 3: Implement minimal backend**

Implement only the files listed for this task. Use SQLite in tests through an environment override, but keep PostgreSQL as the runtime default. Do not call `.env/runtime.env` model secrets.

- [ ] **Step 4: Run focused backend tests**

Run: `python -m pytest backend/tests -q`

Expected: all backend tests pass.

- [ ] **Step 5: Commit Task 1**

Run:

```bash
git add backend
git commit -m "feat: initialize FastAPI backend foundation"
```

---

### Task 2: Frontend Foundation and Route Skeleton

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.mjs`
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/app/globals.css`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx`
- Create: `frontend/app/login/page.tsx`
- Create: `frontend/app/register/page.tsx`
- Create: `frontend/app/dashboard/page.tsx`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/routes.ts`
- Create: `frontend/tests/routes.test.mjs`

**Interfaces:**
- Consumes: backend `/health` and `/api/auth/*` route contract from Task 1.
- Produces: Next.js app router pages for `/`, `/login`, `/register`, and `/dashboard`.
- Produces: `npm.cmd run test`, `npm.cmd run lint`, and `npm.cmd run build` commands.

- [ ] **Step 1: Write frontend tests first**

Create a Node test that verifies the route map and API base fallback before UI implementation:

```javascript
// frontend/tests/routes.test.mjs
import assert from "node:assert/strict";
import test from "node:test";
import { ROUTES } from "../src/lib/routes.js";
import { getApiBaseUrl } from "../src/lib/api.js";

test("PRD P0 routes are exposed for Milestone 0 shell", () => {
  assert.equal(ROUTES.home, "/");
  assert.equal(ROUTES.login, "/login");
  assert.equal(ROUTES.register, "/register");
  assert.equal(ROUTES.dashboard, "/dashboard");
});

test("API base URL defaults to local FastAPI backend", () => {
  assert.equal(getApiBaseUrl(), "http://localhost:8000");
});
```

- [ ] **Step 2: Run frontend tests to verify RED**

Run: `npm.cmd --prefix frontend run test`

Expected: FAIL because `src/lib/routes.js` and `src/lib/api.js` do not exist yet.

- [ ] **Step 3: Implement minimal frontend**

Implement the route constants, API base helper, Tailwind shell, and four pages. The UI may mention unfinished modules as disabled or upcoming, but it must not claim upload, memory, voice, or 3D features are already implemented.

- [ ] **Step 4: Run frontend checks**

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
git add frontend
git commit -m "feat: initialize Next.js frontend shell"
```

---

### Task 3: Docker Compose, Harness, and Documentation Integration

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `docker-compose.yml`
- Modify: `docs/README.md`
- Modify: `docs/init.sh`
- Modify: `docs/feature-list.json`
- Modify: `docs/progress.md`
- Modify: `docs/prd-checklist.md`
- Modify: `docs/平台说明.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: backend and frontend commands from Tasks 1 and 2.
- Produces: `docker compose config` validation and optional `docker compose up --build` smoke path.
- Produces: `docs/init.sh` that runs JSON validation, backend tests, frontend tests/lint/build, and compose config when dependencies are installed.

- [ ] **Step 1: Write harness expectation before implementation**

Update `docs/prd-checklist.md` with Milestone 0 acceptance rows marked in-progress before changing the harness. This creates the review target for implementation.

- [ ] **Step 2: Run current harness to capture the pre-change baseline**

Run:

```bash
python -m json.tool docs/feature-list.json
& "C:\Program Files\Git\bin\bash.exe" ./docs/init.sh
```

Expected: current docs-only harness passes.

- [ ] **Step 3: Add Docker and harness integration**

Add Dockerfiles and Compose services for frontend, backend, postgres, redis, minio, and mock worker processes. Update `docs/init.sh` to run the checks introduced by Tasks 1 and 2 and `docker compose config`.

- [ ] **Step 4: Run full Milestone 0 verification**

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

Expected: all commands exit 0. If `docker compose up --build` is run, `/health` must return `{"status":"ok"}` and frontend must load.

- [ ] **Step 5: Commit Task 3**

Run:

```bash
git add backend/Dockerfile frontend/Dockerfile docker-compose.yml docs AGENTS.md
git commit -m "chore: wire Milestone 0 harness and compose"
```

---

## Self-Review Notes

- Spec coverage: this plan covers PRD Milestone 0 only, with schema scaffolding from PRD section 8 and auth/API connectivity from section 9. It deliberately does not implement Milestones 1-9.
- Scope guard: AI capabilities are limited to provider gateway and mock worker abstractions.
- Placeholder scan: no task contains `TBD`, `TODO`, or "implement later" as requirements.
- Type consistency: route and API names are stable across tasks.
