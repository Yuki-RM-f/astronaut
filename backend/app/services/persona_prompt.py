from app.models.persona import Persona
from app.models.persona_profile import PersonaProfile


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def build_persona_prompt_context(
    persona: Persona, profile: PersonaProfile | None = None
) -> dict[str, str]:
    return {
        "persona_name": _text(persona.name),
        "persona_type": _text(persona.persona_type),
        "relationship_to_user": _text(persona.relationship_to_user),
        "user_nickname_by_persona": _text(persona.user_nickname_by_persona),
        "speaking_style": _text(persona.speaking_style),
        "emotional_style": _text(persona.emotional_style),
        "forbidden_expressions": _text(persona.forbidden_expressions),
        "profile_summary": _text(profile.profile_summary if profile else None),
    }
