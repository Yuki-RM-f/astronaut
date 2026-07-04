from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models import (  # noqa: E402,F401
    ai_job,
    audit_log,
    conversation,
    memory_card,
    parsed_chunk,
    persona,
    persona_profile,
    source_material,
    user,
    voice_avatar,
)
