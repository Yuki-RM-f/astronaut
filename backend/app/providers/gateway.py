from __future__ import annotations

import asyncio
import re
from typing import Any

from app.core.config import Settings, get_settings
from app.providers.dashscope import DashScopeProvider
from app.providers.minimax import MiniMaxProvider
from app.providers.openai_next import OpenAINextTextProvider


REAL_PARSE_CAPABILITIES = {
    "text_parser",
    "ocr",
    "image_understanding",
    "asr",
    "video_understanding",
    "memory_extraction",
}
REAL_VOICE_CAPABILITIES = {"tts", "voice_clone"}
REAL_TEXT_LLM_CAPABILITIES = {
    "chat_llm",
    "story_generation",
    "memory_context_compression",
    "persona_profile_analysis",
    "memory_document_generation",
    "guided_memory_extraction",
}


class ProviderGateway:
    def __init__(
        self,
        provider_name: str | None = None,
        *,
        settings: Settings | None = None,
        dashscope_client: DashScopeProvider | None = None,
        minimax_client: MiniMaxProvider | None = None,
        openai_next_client: OpenAINextTextProvider | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.provider_name = provider_name or self.settings.default_llm_provider
        self._dashscope_client = dashscope_client
        self._minimax_client = minimax_client
        self._openai_next_client = openai_next_client

    async def run(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0)
        if self._should_use_dashscope(capability):
            dashscope = self._dashscope()
            output = await dashscope.run(capability, payload)
            return {
                "provider_type": getattr(dashscope, "provider_type", "third_party"),
                "provider_name": getattr(dashscope, "provider_name", "dashscope"),
                "capability": capability,
                "status": "succeeded",
                "input": payload,
                "output": output,
            }
        if self._should_use_minimax(capability):
            minimax = self._minimax()
            try:
                output = await minimax.run(capability, payload)
            except Exception as exc:
                if not self._should_use_openai_next_text_fallback(capability):
                    raise
                openai_next = self._openai_next()
                output = await openai_next.run(capability, payload)
                return {
                    "provider_type": getattr(openai_next, "provider_type", "third_party"),
                    "provider_name": getattr(openai_next, "provider_name", "openai_next"),
                    "capability": capability,
                    "status": "succeeded",
                    "input": payload,
                    "output": _normalize_real_provider_output(capability, output, payload),
                    "fallback_from_provider": "minimax",
                    "fallback_reason": _sanitize_fallback_reason(exc, self.settings),
                }
            return {
                "provider_type": getattr(minimax, "provider_type", "third_party"),
                "provider_name": getattr(minimax, "provider_name", "minimax"),
                "capability": capability,
                "status": "succeeded",
                "input": payload,
                "output": _normalize_real_provider_output(capability, output, payload),
            }
        return self._mock_result(capability, payload)

    def _should_use_dashscope(self, capability: str) -> bool:
        if capability not in REAL_PARSE_CAPABILITIES:
            return False
        if self.provider_name not in {"dashscope", "qwen", "aliyun_dashscope"}:
            return False
        return self._dashscope().is_configured

    def _dashscope(self) -> DashScopeProvider:
        if self._dashscope_client is None:
            self._dashscope_client = DashScopeProvider(self.settings)
        return self._dashscope_client

    def _should_use_minimax(self, capability: str) -> bool:
        if capability not in REAL_VOICE_CAPABILITIES | REAL_TEXT_LLM_CAPABILITIES:
            return False
        if self.settings.app_env == "test":
            return False
        minimax = self._minimax()
        if capability in REAL_TEXT_LLM_CAPABILITIES:
            return bool(
                getattr(minimax, "is_text_configured", minimax.is_configured)
                and self.settings.openai_compatible_model
            )
        return minimax.is_configured

    def _minimax(self) -> MiniMaxProvider:
        if self._minimax_client is None:
            self._minimax_client = MiniMaxProvider(self.settings)
        return self._minimax_client

    def _should_use_openai_next_text_fallback(self, capability: str) -> bool:
        if capability not in REAL_TEXT_LLM_CAPABILITIES:
            return False
        if self.settings.app_env == "test":
            return False
        return self._openai_next().is_configured

    def _openai_next(self) -> OpenAINextTextProvider:
        if self._openai_next_client is None:
            self._openai_next_client = OpenAINextTextProvider(self.settings)
        return self._openai_next_client

    def _mock_result(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        if capability == "text_parser":
            output = _text_parser_output(payload)
        elif capability == "ocr":
            output = _ocr_output(payload)
        elif capability == "image_understanding":
            output = _image_understanding_output(payload)
        elif capability == "asr":
            output = _asr_output(payload)
        elif capability == "video_understanding":
            output = _video_understanding_output(payload)
        elif capability == "memory_extraction":
            output = _memory_extraction_output(payload)
        elif capability == "chat_llm":
            output = _chat_llm_output(payload)
        elif capability == "story_generation":
            output = _story_generation_output(payload)
        elif capability == "memory_context_compression":
            output = _memory_context_compression_output(payload)
        elif capability == "persona_profile_analysis":
            output = _persona_profile_analysis_output(payload)
        elif capability == "memory_document_generation":
            output = _memory_document_generation_output(payload)
        elif capability == "guided_memory_extraction":
            output = _guided_memory_extraction_output(payload)
        elif capability == "tts":
            output = _tts_output(payload)
        elif capability == "extract_voice_sample":
            output = _voice_sample_output(payload)
        elif capability == "voice_clone":
            output = _voice_clone_output(payload)
        elif capability == "avatar_3d":
            output = _avatar_3d_output(payload)
        else:
            output = {"message": "mock provider result"}

        return {
            "provider_type": "local",
            "provider_name": "mock",
            "capability": capability,
            "status": "succeeded",
            "input": payload,
            "output": output,
        }


def _normalize_real_provider_output(
    capability: str,
    output: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    if capability != "memory_document_generation":
        return output
    if not isinstance(output, dict) or output.get("structured_memory_md"):
        return output
    document_json = output.get("structured_memory_document_json")
    if not isinstance(document_json, dict):
        return output
    return {
        **output,
        "structured_memory_md": _render_memory_document_markdown(document_json, payload),
    }


def _render_memory_document_markdown(
    document_json: dict[str, Any],
    payload: dict[str, Any],
) -> str:
    sections = (
        "资料来源",
        "基础信息",
        "人物关系",
        "兴趣偏好",
        "生活习惯",
        "表达习惯",
        "共同经历",
        "待用户确认",
    )
    section_lines: dict[str, list[str]] = {section: [] for section in sections}
    for source in document_json.get("sources") or []:
        if not isinstance(source, dict):
            continue
        label = source.get("label") or source.get("file_name") or source.get("id") or "未命名资料"
        section_lines["资料来源"].append(f"- {source.get('file_type') or 'material'}: {label}")

    persona_card = payload.get("persona_card") if isinstance(payload.get("persona_card"), dict) else {}
    for label, value in [
        ("姓名", persona_card.get("name")),
        ("关系", persona_card.get("relationship_to_user")),
        ("年龄/享年", persona_card.get("age")),
        ("简介", persona_card.get("short_bio")),
    ]:
        if value not in {None, ""}:
            section_lines["基础信息"].append(f"- {label}: {value}")

    modules = document_json.get("modules") if isinstance(document_json.get("modules"), dict) else {}
    section_by_module = {
        "basic_fact": "基础信息",
        "relationship": "人物关系",
        "preference": "兴趣偏好",
        "habit": "生活习惯",
        "expression_style": "表达习惯",
        "shared_event": "共同经历",
    }
    for module, section in section_by_module.items():
        for item in modules.get(module) or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "未命名记忆").strip()
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            status = str(item.get("status") or "pending_review")
            source_location = str(item.get("source_location") or "").strip()
            importance = "[important] " if bool(item.get("is_important")) else ""
            suffix = f"（来源：{source_location}）" if source_location else ""
            line = f"- {importance}[{status}] {title}: {content}{suffix}"
            section_lines[section].append(line)
            if status not in REVIEWED_MEMORY_STATUSES:
                section_lines["待用户确认"].append(line)

    if not section_lines["资料来源"]:
        section_lines["资料来源"].append("- 暂无已解析资料")
    for section in sections:
        if not section_lines[section]:
            section_lines[section].append("- 暂无明确资料")
    return "\n\n".join(
        f"## {section}\n" + "\n".join(section_lines[section])
        for section in sections
    )


def _sanitize_fallback_reason(exc: Exception, settings: Settings) -> str:
    text = re.sub(r"\s+", " ", str(exc)).strip()
    for secret in [
        settings.minimax_api_key,
        settings.openai_compatible_api_key,
        settings.openai_next_api_key,
        settings.dashscope_api_key,
        settings.tripo_api_key,
    ]:
        if secret:
            text = text.replace(secret, "[redacted]")
    return text[:500] or exc.__class__.__name__


def _text_parser_output(payload: dict[str, Any]) -> dict[str, Any]:
    text = _clean_text(payload.get("text") or payload.get("manual_text") or "")
    if not text:
        text = _fallback_text(payload)
    return {
        "cleaned_text": text,
        "chunks": [
            {
                "chunk_type": "text",
                "content": text,
                "summary": _summarize(text),
                "source_location": payload.get("source_location") or "text:body",
            }
        ],
    }


def _ocr_output(payload: dict[str, Any]) -> dict[str, Any]:
    file_name = payload.get("file_name") or "image"
    description = payload.get("user_description") or payload.get("manual_text") or "未填写说明"
    return {
        "ocr_text": f"{file_name} 中可见文字线索：{description}",
        "source_location": f"image:{file_name}:ocr",
    }


def _image_understanding_output(payload: dict[str, Any]) -> dict[str, Any]:
    file_name = payload.get("file_name") or "image"
    description = payload.get("user_description") or "家庭照片"
    return {
        "caption": f"{file_name} 是一张与人物相关的图片资料，说明为：{description}",
        "scene_metadata": {
            "scene_type": "family_memory",
            "detected_people_count": 1,
            "emotion_tone": "warm",
        },
        "memory_candidate_text": f"{description}。这张图片可作为一段温暖回忆的来源。",
        "source_location": f"image:{file_name}",
    }


def _asr_output(payload: dict[str, Any]) -> dict[str, Any]:
    file_name = payload.get("file_name") or "audio"
    description = payload.get("user_description") or "音频资料"
    return {
        "transcript": f"{description}。音频 {file_name} 中保留了人物相关的声音线索。",
        "sample_metadata": {
            "start_time": "00:00",
            "end_time": "00:05",
            "speaker": "unknown",
        },
        "source_location": f"audio:{file_name}#00:00-00:05",
    }


def _video_understanding_output(payload: dict[str, Any]) -> dict[str, Any]:
    file_name = payload.get("file_name") or "video"
    description = payload.get("user_description") or "视频资料"
    return {
        "transcript": f"{description}。视频 {file_name} 中包含人物相关的片段。",
        "scene_summary": f"{file_name} 展示了一段可用于生成记忆的视频场景。",
        "timestamps": [{"start": "00:00", "end": "00:10", "label": "demo_scene"}],
        "memory_candidate_text": f"{description}。视频里有一段值得保留的共同经历。",
        "source_location": f"video:{file_name}#00:00-00:10",
    }


MEMORY_EXTRACTION_MODULES = (
    "basic_fact",
    "relationship",
    "preference",
    "habit",
    "expression_style",
    "shared_event",
)
MEMORY_EXTRACTION_MODULE_SET = set(MEMORY_EXTRACTION_MODULES)


def _memory_extraction_output(payload: dict[str, Any]) -> dict[str, Any]:
    memories = _build_memory_candidates(payload)
    structured_memory_json = _structured_memory_json(payload, memories)
    return {
        "structured_memory_json": structured_memory_json,
        "memories": memories,
    }


def _build_memory_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    text = _clean_text(payload.get("content") or payload.get("text") or _fallback_text(payload))
    source_type = payload.get("source_type") or payload.get("file_type") or "material"
    base_location = payload.get("source_location") or f"{source_type}:body"
    sentences = _sentences(text)

    memories: list[dict[str, Any]] = []
    for index, sentence in enumerate(sentences[:12], start=1):
        quote = sentence[:120]
        memories.append(
            {
                "title": _title_for(sentence, source_type, index),
                "content": sentence,
                "category": _memory_module_for(_category_for(sentence, source_type)),
                "confidence_level": "high" if source_type in {"manual", "text"} else "medium",
                "confidence_score": 85 if source_type in {"manual", "text"} else 70,
                "source_quote": quote,
                "source_location": f"{base_location}#{index}",
            }
        )
    return memories


def _structured_memory_json(
    payload: dict[str, Any],
    memories: list[dict[str, Any]],
) -> dict[str, Any]:
    modules: dict[str, list[dict[str, Any]]] = {
        category: [] for category in MEMORY_EXTRACTION_MODULES
    }
    warnings: list[str] = []
    unclassified: list[dict[str, Any]] = []
    for memory in memories:
        category = _memory_module_for(memory.get("category"))
        if category not in MEMORY_EXTRACTION_MODULE_SET:
            unclassified.append(memory)
            warnings.append(f"跳过无法归类的候选记忆：{memory.get('title') or '未命名'}")
            continue
        normalized = {**memory, "category": category}
        modules[category].append(normalized)
    return {
        "source_material_id": str(payload.get("source_material_id") or ""),
        "modules": modules,
        "unclassified": unclassified,
        "warnings": warnings,
    }


def _chat_llm_output(payload: dict[str, Any]) -> dict[str, Any]:
    draft_reply = _clean_text(payload.get("draft_reply") or "")
    if not draft_reply:
        nickname = payload.get("user_nickname_by_persona") or "你"
        if payload.get("conversation_kind") == "wishes" or payload.get("context_kind") == "wishes":
            draft_reply = (
                f"{nickname}，我听见这个心愿了。我们先把它放成今天能做的一小步，"
                "慢慢向前走。"
            )
        else:
            draft_reply = f"{nickname}，这件事我记不太清，不能硬说成真的。"
    return {
        "reply_text": draft_reply,
        "used_memory_ids": payload.get("used_memory_ids") or [],
        "prompt_variables": {
            "persona_name": payload.get("persona_name"),
            "persona_type": payload.get("persona_type"),
            "relationship_to_user": payload.get("relationship_to_user"),
            "user_nickname_by_persona": payload.get("user_nickname_by_persona"),
            "speaking_style": payload.get("speaking_style"),
            "emotional_style": payload.get("emotional_style"),
            "conversation_kind": payload.get("conversation_kind"),
            "guided_system_prompt": payload.get("guided_system_prompt"),
            "confidence_score": payload.get("confidence_score"),
        },
    }


def _story_generation_output(payload: dict[str, Any]) -> dict[str, Any]:
    nickname = payload.get("user_nickname_by_persona") or "你"
    theme = _clean_text(payload.get("story_theme") or "共同回忆")
    memories = payload.get("retrieved_memories") or []
    source_memories: list[dict[str, Any]] = []
    memory_lines: list[str] = []

    for memory in memories[:3]:
        content = _clean_text(str(memory.get("content") or ""))
        memory_id = memory.get("id")
        if not content or not memory_id:
            continue
        source_memories.append(
            {
                "memory_card_id": str(memory_id),
                "title": str(memory.get("title") or "来源记忆"),
                "quote": _clean_text(str(memory.get("quote") or content)),
                "source_location": memory.get("source_location"),
            }
        )
        memory_lines.append(content)

    if not memory_lines:
        return {
            "title": f"{theme}里的回忆",
            "content": f"{nickname}，这段回忆我还需要更多已确认的资料，不能硬说成真的。",
            "source_memory_ids": [],
            "source_memories": [],
        }

    joined_memories = "；".join(memory_lines)
    return {
        "title": f"{theme}里的回忆",
        "content": (
            f"{nickname}，我想给你讲一段关于{theme}的回忆。我记得{joined_memories}。"
            "这些我只能按已经确认的记忆慢慢说给你听。"
        ),
        "source_memory_ids": [item["memory_card_id"] for item in source_memories],
        "source_memories": source_memories,
    }


def _memory_context_compression_output(payload: dict[str, Any]) -> dict[str, Any]:
    long_md = str(payload.get("long_term_memory_md") or "")
    short_md = str(payload.get("short_term_memory_md") or "")
    max_long = int(payload.get("max_long_term_chars") or 12000)
    max_short = int(payload.get("max_short_term_chars") or 6000)
    max_ids = int(payload.get("max_selected_memory_ids") or 8)
    selected_ids = _memory_ids_from_markdown(long_md)[:max_ids]
    return {
        "long_term_memory_md": _trim_markdown(long_md, max_long),
        "short_term_memory_md": _trim_markdown(short_md, max_short),
        "selected_memory_ids": selected_ids,
    }


def _persona_profile_analysis_output(payload: dict[str, Any]) -> dict[str, Any]:
    persona_card = payload.get("persona_card") if isinstance(payload.get("persona_card"), dict) else {}
    memories = payload.get("active_memory_cards") if isinstance(payload.get("active_memory_cards"), list) else []
    evidence = [
        str(memory.get("id"))
        for memory in memories
        if isinstance(memory, dict) and memory.get("id")
    ]
    texts = [
        _clean_text(str(memory.get("content") or ""))
        for memory in memories
        if isinstance(memory, dict) and memory.get("content")
    ]
    joined = "；".join(texts[:3])
    confidence = 0.45 + min(len(memories), 5) * 0.08
    return {
        "persona_version": "persona_engine_v2_mock",
        "basic_info": {
            "name": persona_card.get("name"),
            "relationship_to_user": persona_card.get("relationship_to_user"),
            "evidence": ["persona_card"],
        },
        "personality_traits": [
            {"trait": "温和", "confidence": round(confidence, 2), "evidence": evidence[:2]}
        ],
        "speech_style": {
            "summary": "语气温和，常用“慢慢来”式的安抚表达。",
            "evidence": evidence[:3],
        },
        "interests": [
            {"name": "家庭记忆", "evidence": evidence[:3], "confidence": round(confidence, 2)}
        ],
        "habits": [],
        "emotional_style": {
            "summary": "倾向先安抚，再给出具体陪伴。",
            "evidence": evidence[:3],
        },
        "relationships": [
            {
                "name": persona_card.get("relationship_to_user"),
                "summary": persona_card.get("relationship_to_user"),
                "evidence": ["persona_card"],
            }
        ],
        "worldview": {"summary": "重视陪伴和确定的生活细节。", "evidence": evidence[:3]},
        "decision_style": {"summary": "偏谨慎、循序渐进。", "evidence": evidence[:3]},
        "taboos": [],
        "profile_summary": joined or "TA 的人格画像仍需要更多已确认记忆；当前可先保持慢慢来、重视陪伴的表达基调。",
        "overall_confidence": round(min(confidence, 0.9), 2),
        "low_confidence_fields": [] if memories else ["personality_traits", "habits"],
        "pending_verification": [] if memories else ["继续确认更多记忆卡片"],
        "source_memory_ids": evidence,
    }


MEMORY_DOCUMENT_SECTIONS = (
    "资料来源",
    "基础信息",
    "人物关系",
    "兴趣偏好",
    "生活习惯",
    "表达习惯",
    "共同经历",
    "待用户确认",
)

CATEGORY_SECTION_MAP = {
    "basic_fact": "基础信息",
    "relationship": "人物关系",
    "preference": "兴趣偏好",
    "habit": "生活习惯",
    "expression_style": "表达习惯",
    "shared_event": "共同经历",
    "story_material": "共同经历",
    "value": "共同经历",
    "emotional_pattern": "共同经历",
}

REVIEWED_MEMORY_STATUSES = {"confirmed", "corrected"}


def _memory_document_generation_output(payload: dict[str, Any]) -> dict[str, Any]:
    persona_card = payload.get("persona_card") if isinstance(payload.get("persona_card"), dict) else {}
    source_metadata = (
        payload.get("source_metadata")
        if isinstance(payload.get("source_metadata"), list)
        else []
    )
    parsed_chunks = (
        payload.get("parsed_chunks") if isinstance(payload.get("parsed_chunks"), list) else []
    )
    memories = (
        payload.get("active_memory_cards")
        if isinstance(payload.get("active_memory_cards"), list)
        else []
    )
    section_lines = {section: [] for section in MEMORY_DOCUMENT_SECTIONS}
    document_sources: list[dict[str, Any]] = []
    document_modules: dict[str, list[dict[str, Any]]] = {
        module: [] for module in MEMORY_EXTRACTION_MODULES
    }

    for material in source_metadata:
        if not isinstance(material, dict):
            continue
        source_label = material.get("file_name") or material.get("manual_text_excerpt")
        if source_label:
            source_label = str(source_label)[:80]
        else:
            source_label = str(material.get("id") or "未命名资料")
        document_sources.append(
            {
                "id": str(material.get("id") or ""),
                "file_type": str(material.get("file_type") or "material"),
                "label": source_label,
                "parse_status": material.get("parse_status"),
            }
        )
        section_lines["资料来源"].append(
            f"- {material.get('file_type') or 'material'}: {source_label}"
        )

    for label, value in [
        ("姓名", persona_card.get("name")),
        ("关系", persona_card.get("relationship_to_user")),
        ("年龄/享年", persona_card.get("age")),
        ("简介", persona_card.get("short_bio")),
    ]:
        if value not in {None, ""}:
            section_lines["基础信息"].append(f"- {label}: {value}")

    active_memories = [memory for memory in memories if isinstance(memory, dict)]
    active_memories.sort(
        key=lambda memory: (
            0 if bool(memory.get("is_important")) else 1,
            0 if str(memory.get("status") or "") in REVIEWED_MEMORY_STATUSES else 1,
            str(memory.get("id") or ""),
        )
    )

    for memory in active_memories:
        status = str(memory.get("status") or "pending_review")
        title = str(memory.get("title") or "未命名记忆").strip()
        content = _clean_text(str(memory.get("content") or ""))
        if not content:
            continue
        location = memory.get("source_location")
        suffix = f"（来源：{location}）" if location else ""
        importance = "[important] " if bool(memory.get("is_important")) else ""
        line = f"- {importance}[{status}] {title}: {content}{suffix}"
        category = str(memory.get("category") or "")
        module = category if category in MEMORY_EXTRACTION_MODULE_SET else "shared_event"
        confidence_score = memory.get("confidence_score", 70)
        try:
            confidence_score = int(confidence_score)
        except (TypeError, ValueError):
            confidence_score = 70
        document_modules[module].append(
            {
                "id": str(memory.get("id") or ""),
                "title": title,
                "content": content,
                "category": module,
                "confidence_level": str(memory.get("confidence_level") or "medium"),
                "confidence_score": max(0, min(confidence_score, 100)),
                "source_quote": str(memory.get("source_quote") or content[:120]),
                "source_location": str(location or ""),
                "status": status,
                "is_important": bool(memory.get("is_important")),
            }
        )
        section = CATEGORY_SECTION_MAP.get(category, "待用户确认")
        section_lines[section].append(line)
        if status not in REVIEWED_MEMORY_STATUSES:
            section_lines["待用户确认"].append(line)

    if not section_lines["资料来源"]:
        section_lines["资料来源"].append("- 暂无已解析资料")
    for section in MEMORY_DOCUMENT_SECTIONS:
        if not section_lines[section]:
            section_lines[section].append("- 暂无明确资料")

    structured_memory_md = "\n\n".join(
        f"## {section}\n" + "\n".join(section_lines[section])
        for section in MEMORY_DOCUMENT_SECTIONS
    )
    profile_summary = _memory_document_profile_summary(persona_card, active_memories)
    traceable_count = sum(
        1
        for memory in active_memories
        if memory.get("source_quote") and memory.get("source_location")
    )
    reviewed_count = sum(
        1
        for memory in active_memories
        if memory.get("status") in REVIEWED_MEMORY_STATUSES
    )
    trust_score = _memory_document_trust_score(
        source_count=len(source_metadata),
        chunk_count=len(parsed_chunks),
        memory_count=len(memories),
        traceable_count=traceable_count,
        reviewed_count=reviewed_count,
    )
    suggestions = _memory_document_suggestions(source_metadata, memories, reviewed_count)
    return {
        "profile_summary": profile_summary,
        "trust_score": trust_score,
        "trust_level": _trust_level_for_score(trust_score),
        "trust_rationale": (
            f"基于 {len(source_metadata)} 份资料、{len(parsed_chunks)} 个解析片段、"
            f"{len(memories)} 张活跃记忆卡片生成；其中 {traceable_count} 张具备来源摘录与位置。"
        ),
        "suggestions": suggestions,
    }


def _memory_document_profile_summary(
    persona_card: dict[str, Any],
    memories: list[dict[str, Any]],
) -> str:
    name = str(persona_card.get("name") or "TA")
    candidates: list[str] = []
    for memory in memories:
        content = _clean_text(str(memory.get("content") or ""))
        if content:
            candidates.append(content)
        if len(candidates) >= 3:
            break
    if candidates:
        return f"{name}的档案摘要：" + "；".join(candidates) + "。"
    short_bio = _clean_text(str(persona_card.get("short_bio") or ""))
    if short_bio:
        return short_bio
    return "档案摘要将在更多资料解析后自动生成。"


def _memory_document_trust_score(
    *,
    source_count: int,
    chunk_count: int,
    memory_count: int,
    traceable_count: int,
    reviewed_count: int,
) -> int:
    if source_count == 0 and chunk_count == 0 and memory_count == 0:
        return 0
    traceability = traceable_count / memory_count if memory_count else 0
    review_rate = reviewed_count / memory_count if memory_count else 0
    score = (
        20
        + min(source_count, 4) * 8
        + min(chunk_count, 8) * 3
        + min(memory_count, 10) * 4
        + round(traceability * 15)
        + round(review_rate * 10)
    )
    return max(0, min(100, score))


def _memory_document_suggestions(
    source_metadata: list[Any],
    memories: list[Any],
    reviewed_count: int,
) -> list[str]:
    material_types = {
        str(material.get("file_type"))
        for material in source_metadata
        if isinstance(material, dict) and material.get("file_type")
    }
    suggestions: list[str] = []
    if "audio" not in material_types:
        suggestions.append("补充 TA 的清晰语音资料")
    if "image" not in material_types and "video" not in material_types:
        suggestions.append("补充照片或视频以增强共同经历证据")
    if memories and reviewed_count == 0:
        suggestions.append("在资料审核页确认或修正待审核记忆卡片")
    if not suggestions:
        suggestions.append("继续补充跨场景资料，保持记忆文档可追溯")
    return suggestions


def _trust_level_for_score(score: int) -> str:
    if score <= 30:
        return "initial"
    if score <= 60:
        return "usable"
    if score <= 80:
        return "trusted"
    return "high_trust"


GUIDED_MEMORY_KEYWORDS = {
    "regrets": (
        "遗憾",
        "没来得及",
        "来不及",
        "道歉",
        "对不起",
        "感谢",
        "想念",
        "告别",
        "心结",
        "后悔",
        "亏欠",
        "没说",
    ),
    "wishes": (
        "心愿",
        "愿望",
        "希望",
        "想完成",
        "未完成",
        "没完成",
        "想要",
        "想做",
        "继续",
        "替我",
        "盼",
        "花园",
    ),
}


def _guided_memory_extraction_output(payload: dict[str, Any]) -> dict[str, Any]:
    kind = "wishes" if payload.get("kind") == "wishes" else "regrets"
    keywords = GUIDED_MEMORY_KEYWORDS[kind]
    scored: list[tuple[int, dict[str, Any]]] = []
    for memory in payload.get("active_memory_cards") or []:
        if not isinstance(memory, dict):
            continue
        text = _clean_text(
            " ".join(
                str(memory.get(key) or "")
                for key in ("title", "content", "source_quote")
            )
        )
        score = sum(1 for keyword in keywords if keyword in text)
        if score <= 0:
            continue
        if memory.get("is_important"):
            score += 2
        scored.append((score, memory))
    scored.sort(
        key=lambda item: (
            -item[0],
            -int(item[1].get("confidence_score") or 0),
            str(item[1].get("id") or ""),
        )
    )
    items: list[dict[str, Any]] = []
    for _, memory in scored[: int(payload.get("max_candidates") or 3)]:
        summary = _clean_text(str(memory.get("content") or memory.get("source_quote") or ""))[:160]
        memory_id = str(memory.get("id") or "").strip()
        if not summary or not memory_id:
            continue
        items.append(
            {
                "memory_card_id": memory_id,
                "title": _clean_text(str(memory.get("title") or _guided_candidate_title(kind))),
                "summary": summary,
                "suggested_user_message": _guided_suggested_user_message(kind, summary),
                "source_quote": memory.get("source_quote"),
                "source_location": memory.get("source_location"),
            }
        )
    return {
        "items": items,
        "empty_reason": None if items else _guided_empty_reason(kind),
    }


def _guided_suggested_user_message(kind: str, summary: str) -> str:
    if kind == "wishes":
        return f"我想继续完成这件事：{summary}"
    return f"我想慢慢说说这段记忆：{summary}"


def _guided_candidate_title(kind: str) -> str:
    return "记忆里的心愿" if kind == "wishes" else "记忆里的遗憾"


def _guided_empty_reason(kind: str) -> str:
    label = "心愿" if kind == "wishes" else "遗憾"
    return f"没有在已审核记忆中找到可直接提取的{label}线索。"


def _tts_output(payload: dict[str, Any]) -> dict[str, Any]:
    persona_id = payload.get("persona_id") or "persona"
    job_id = payload.get("job_id") or "preview"
    text = _clean_text(payload.get("text") or "")
    return {
        "audio_url": f"mock://tts/{persona_id}/{job_id}.wav",
        "duration_ms": max(800, min(len(text) * 140, 12000)),
        "voice_status": payload.get("voice_status") or "default_tts",
        "voice_model_id": payload.get("voice_model_id"),
        "default_tts_notice": payload.get("default_tts_notice"),
    }


def _voice_sample_output(payload: dict[str, Any]) -> dict[str, Any]:
    source_material_id = payload.get("source_material_id") or "source"
    file_name = payload.get("file_name") or "audio"
    description = payload.get("user_description") or "清晰语音样本"
    return {
        "sample_text": f"{description}，来自 {file_name} 的 00:00-00:08 片段。",
        "sample_audio_url": payload.get("storage_url")
        or f"mock://voice-sample/{source_material_id}.wav",
        "start_time": "00:00",
        "end_time": "00:08",
        "quality_score": 76,
    }


def _voice_clone_output(payload: dict[str, Any]) -> dict[str, Any]:
    voice_model_id = payload.get("voice_model_id") or "voice-model"
    if payload.get("simulate_failure"):
        return {
            "clone_status": "failed",
            "error_message": "mock voice clone failed; fallback to default TTS",
        }
    return {
        "clone_status": "succeeded",
        "model_artifact_url": f"mock://voice-model/{voice_model_id}",
        "preview_audio_url": f"mock://voice-preview/{voice_model_id}.wav",
        "quality_score": 82,
    }


def _avatar_3d_output(payload: dict[str, Any]) -> dict[str, Any]:
    persona_id = payload.get("persona_id") or "persona"
    job_id = payload.get("job_id") or "avatar-job"
    style = payload.get("style") or "memorial"
    if payload.get("simulate_failure"):
        return {
            "generation_status": "failed",
            "error_message": "mock avatar generation failed; fallback to default memorial avatar",
        }
    return {
        "generation_status": "succeeded",
        "model_url": f"mock://avatar-model/{persona_id}/{job_id}.glb",
        "preview_image_url": f"mock://avatar-preview/{persona_id}/{job_id}.png",
        "format": "glb",
        "style": style,
        "expression_config_json": {
            "blink": True,
            "smile": True,
            "nod": True,
            "comfort": True,
        },
        "animation_config_json": {
            "idle_breath": True,
            "blink": True,
            "nod": True,
            "smile": True,
            "listen": True,
        },
        "lip_sync_config_json": {
            "mode": "audio_envelope",
            "mouth_open_blendshape": "aa",
            "sample_rate_ms": 80,
        },
    }


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _memory_ids_from_markdown(markdown: str) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for memory_id in re.findall(r"memory_card_id:\s*([A-Za-z0-9_-]+)", markdown):
        if memory_id not in seen:
            ids.append(memory_id)
            seen.add(memory_id)
    return ids


def _trim_markdown(markdown: str, max_chars: int) -> str:
    if len(markdown) <= max_chars:
        return markdown
    if max_chars <= 80:
        return markdown[:max_chars]
    head = max_chars // 3
    tail = max_chars - head - 48
    return f"{markdown[:head]}\n\n... 已压缩省略 ...\n\n{markdown[-tail:]}"


def _sentences(text: str) -> list[str]:
    parts = re.split(r"[。！？!?；;\n]+", text)
    return [part.strip(" ，,") for part in parts if part.strip(" ，,")]


def _fallback_text(payload: dict[str, Any]) -> str:
    file_name = payload.get("file_name") or "资料"
    description = payload.get("user_description") or "未填写说明"
    return f"{file_name}：{description}"


def _summarize(text: str) -> str:
    return text[:80]


def _title_for(sentence: str, source_type: str, index: int) -> str:
    if "喜欢" in sentence:
        return "资料中的偏好记忆"
    if "常说" in sentence or "说" in sentence:
        return "资料中的表达习惯"
    return f"{source_type} 资料记忆 {index}"


def _category_for(sentence: str, source_type: str) -> str:
    if "喜欢" in sentence:
        return "preference"
    if "常说" in sentence or "说" in sentence:
        return "expression_style"
    if source_type in {"image", "video"}:
        return "shared_event"
    return "shared_event"


def _memory_module_for(category: object) -> str:
    value = str(category or "").strip()
    if value in MEMORY_EXTRACTION_MODULE_SET:
        return value
    if value in {"story_material", "value", "emotional_pattern"}:
        return "shared_event"
    if value == "unknown":
        return "shared_event"
    return value
