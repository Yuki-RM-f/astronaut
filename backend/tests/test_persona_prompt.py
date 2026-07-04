from app.models.persona import Persona


def test_prompt_context_uses_persona_relationship_and_calling_settings():
    from app.services.persona_prompt import build_persona_prompt_context

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
