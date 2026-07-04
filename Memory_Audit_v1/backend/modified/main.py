from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.avatar import router as avatar_router
from app.api.routes.chat import router as chat_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.materials import router as materials_router
from app.api.routes.memories import router as memories_router
from app.api.routes.personas import router as personas_router
from app.api.routes.profile import router as profile_router
from app.api.routes.audit import router as audit_router
from app.api.routes.stories import router as stories_router
from app.api.routes.voice import router as voice_router
from app.core.config import get_settings


app = FastAPI(title="可信人格记忆Agent Backend")
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router, prefix="/api")
app.include_router(avatar_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(materials_router, prefix="/api")
app.include_router(memories_router, prefix="/api")
app.include_router(personas_router, prefix="/api")
app.include_router(profile_router, prefix="/api")
app.include_router(stories_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
