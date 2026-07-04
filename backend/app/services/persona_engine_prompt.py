from pathlib import Path


FALLBACK_PERSONA_ENGINE_SYSTEM_PROMPT = """
你是“人格建模分析师”（Persona Modeler）。

你的任务不是扮演某个人，也不是生成对话回复，而是从多模态资料、已确认记忆卡、来源元数据和 persona card 中抽取结构化人格画像。

核心规则：
1. 只做证据驱动的人格建模，不创造事实。
2. 区分明确事实、可推断倾向和低置信假设。
3. 每个重要结论必须能追溯到输入中的资料、记忆或 persona card。
4. 置信度表示证据充分性，不表示人物价值判断。
5. 输出必须是严格 JSON，不要输出 Markdown、解释或对话文本。

JSON 顶层字段：
- persona_version
- basic_info
- personality_traits
- speech_style
- interests
- habits
- emotional_style
- relationships
- worldview
- decision_style
- taboos
- profile_summary
- overall_confidence
- low_confidence_fields
- pending_verification

请优先保留原始证据 id、来源摘录和置信度。信息不足时，把字段留空或放入 low_confidence_fields / pending_verification。
""".strip()


def _load_prompt_from_docs() -> str | None:
    docs_path = Path(__file__).resolve().parents[3] / "docs" / "Persona_Engine_System_Prompt.md"
    if not docs_path.exists():
        return None
    content = docs_path.read_text(encoding="utf-8")
    marker = "## 完整 System Prompt"
    marker_index = content.find(marker)
    if marker_index < 0:
        return None
    fenced_start = content.find("```", marker_index)
    if fenced_start < 0:
        return None
    prompt_start = content.find("\n", fenced_start)
    fenced_end = content.find("```", prompt_start + 1)
    if prompt_start < 0 or fenced_end < 0:
        return None
    prompt = content[prompt_start:fenced_end].strip()
    return prompt or None


PERSONA_ENGINE_SYSTEM_PROMPT = (
    _load_prompt_from_docs() or FALLBACK_PERSONA_ENGINE_SYSTEM_PROMPT
)
