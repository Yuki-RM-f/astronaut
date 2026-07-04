# Milestone 6 Voice, TTS, And Voice Clone Implementation Plan

**Goal:** Implement PRD Milestone 6 in small verified loops: default TTS, voice sample extraction, voice clone mock provider with fallback, voice-message ASR-to-chat-to-TTS, and frontend voice controls/playback.

**Scope Boundaries:**
- Follow `docs/可信人格记忆Agent_mvp_prd.md` Milestone 6 only.
- Do not implement Milestone 7 avatar/3D, Milestone 8 story/export, public community, payment, advanced compliance, or cinematic/high-fidelity voice claims.
- Use deterministic mock providers unless `.env/runtime.env` defines real voice/TTS provider variables. Current local `runtime.env` only declares OpenAI variables, so Milestone 6 starts with mock/default provider behavior.
- Default TTS must always surface: `当前使用系统默认声音，不是 TA 的真实声音。上传 TA 的清晰语音后，可以尝试生成模拟音色。`
- All async/provider-like actions must write `ai_jobs` with PRD statuses.

## Task 1: Backend Default TTS And Speech Synthesis

**Status:** Complete.

**Files:**
- Create: `backend/app/schemas/voice.py`
- Create: `backend/app/services/voice.py`
- Create: `backend/app/api/routes/voice.py`
- Modify: `backend/app/providers/gateway.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_voice.py`

**Acceptance:**
- `GET /api/personas/{id}/voice` returns `no_voice` before configuration.
- `POST /api/personas/{id}/voice/default-tts` stores one selected `VoiceModel` with status `default_tts`.
- Default TTS response includes the exact PRD warning that it is not TA's real voice.
- `POST /api/personas/{id}/voice/synthesize` uses mock `tts`, creates a succeeded `synthesize_speech` AI job, and returns a deterministic playable mock audio URL plus provider metadata.
- Cross-user access returns 404.

**Checks:**
```powershell
python -m pytest backend/tests/test_voice.py -q
python -m pytest backend/tests -q
```

## Task 2: Backend Voice Sample Extraction And Voice Clone Fallback

**Status:** Complete.

**Files:**
- Modify: `backend/app/schemas/voice.py`
- Modify: `backend/app/services/voice.py`
- Modify: `backend/app/api/routes/voice.py`
- Modify: `backend/app/providers/gateway.py`
- Modify: `backend/tests/test_voice.py`

**Acceptance:**
- `POST /api/personas/{id}/voice/samples` can create a sample from an owned audio `SourceMaterial`.
- Sample extraction writes a succeeded `extract_voice_sample` AI job and a `VoiceModel` with status `sample_ready`.
- `POST /api/personas/{id}/voice/clone` writes a `clone_voice` AI job and uses mock `voice_clone`.
- Clone success marks a selected `VoiceModel` as `cloned_ready`.
- Clone failure marks `clone_failed`, keeps or creates a selected `default_tts` fallback, and returns the default TTS warning.

**Checks:**
```powershell
python -m pytest backend/tests/test_voice.py -q
python -m pytest backend/tests -q
```

## Task 3: Backend Voice Message API

**Status:** Complete.

**Files:**
- Modify: `backend/app/schemas/chat.py`
- Modify: `backend/app/services/chat.py`
- Modify: `backend/app/api/routes/chat.py`
- Modify: `backend/tests/test_chat.py`
- Modify: `backend/tests/test_voice.py`

**Acceptance:**
- `POST /api/conversations/{id}/voice-message` accepts a voice payload.
- Mock ASR creates a user text message from transcript.
- Chat uses the existing first-person reply, memory retrieval, citations, and banned-expression filters.
- TTS/clone/default fallback produces `audio_url` on the persona message.
- ASR and synthesis write `asr_audio` and `synthesize_speech` AI jobs.

**Checks:**
```powershell
python -m pytest backend/tests/test_chat.py backend/tests/test_voice.py -q
python -m pytest backend/tests -q
```

## Task 4: Frontend Voice Settings And Playback

**Files:**
- Create: `frontend/src/lib/voice.ts`
- Create: `frontend/app/personas/[id]/voice/page.tsx`
- Modify: `frontend/app/personas/[id]/chat/page.tsx`
- Modify: `frontend/app/personas/[id]/page.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/routes.ts`
- Create: `frontend/tests/voice.test.mjs`
- Modify: `frontend/tests/routes.test.mjs`

**Acceptance:**
- `/personas/{id}/voice` shows current voice status, default TTS options, exact PRD warning, sample/clone status, and synthesize test action.
- Chat page exposes voice input affordance and plays returned `audio_url` when present.
- UI copy does not claim real TA voice unless status is `cloned_ready`, and still avoids high-fidelity claims.

**Checks:**
```powershell
npm.cmd --prefix frontend run test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
```

## Task 5: Docs, Harness, And Milestone 6 Verification

**Files:**
- Modify: `docs/README.md`
- Modify: `docs/feature-list.json`
- Modify: `docs/progress.md`
- Modify: `docs/prd-checklist.md`
- Modify: `docs/平台说明.md`
- Modify: `docs/init.sh`
- Modify: `frontend/app/page.tsx`

**Acceptance:**
- Docs truth surface says Milestone 6 is complete only after backend and frontend checks pass.
- Remaining Milestone 7/8 gaps stay explicit.
- `docs/init.sh` banner and checks match the current milestone.

**Checks:**
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
