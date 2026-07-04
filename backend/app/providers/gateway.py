from __future__ import annotations

import asyncio
import re
from typing import Any

from app.core.config import Settings, get_settings
from app.providers.dashscope import DashScopeProvider
from app.providers.minimax import MiniMaxProvider


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
}


class ProviderGateway:
    def __init__(
        self,
        provider_name: str | None = None,
        *,
        settings: Settings | None = None,
        dashscope_client: DashScopeProvider | None = None,
        minimax_client: MiniMaxProvider | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.provider_name = provider_name or self.settings.default_llm_provider
        self._dashscope_client = dashscope_client
        self._minimax_client = minimax_client

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
            output = await minimax.run(capability, payload)
            return {
                "provider_type": getattr(minimax, "provider_type", "third_party"),
                "provider_name": getattr(minimax, "provider_name", "minimax"),
                "capability": capability,
                "status": "succeeded",
                "input": payload,
                "output": output,
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
            output = {"memories": _build_memory_candidates(payload)}
        elif capability == "chat_llm":
            output = _chat_llm_output(payload)
        elif capability == "story_generation":
            output = _story_generation_output(payload)
        elif capability == "memory_context_compression":
            output = _memory_context_compression_output(payload)
        elif capability == "persona_profile_analysis":
            output = _persona_profile_analysis_output(payload)
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


def _build_memory_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    text = _clean_text(payload.get("content") or payload.get("text") or _fallback_text(payload))
    source_type = payload.get("source_type") or payload.get("file_type") or "material"
    base_location = payload.get("source_location") or f"{source_type}:body"
    sentences = _sentences(text)

    memories: list[dict[str, Any]] = []
    for index, sentence in enumerate(sentences[:3], start=1):
        quote = sentence[:120]
        memories.append(
            {
                "title": _title_for(sentence, source_type, index),
                "content": sentence,
                "category": _category_for(sentence, source_type),
                "confidence_level": "high" if source_type in {"manual", "text"} else "medium",
                "confidence_score": 85 if source_type in {"manual", "text"} else 70,
                "source_quote": quote,
                "source_location": f"{base_location}#{index}",
            }
        )
    return memories


def _chat_llm_output(payload: dict[str, Any]) -> dict[str, Any]:
    draft_reply = _clean_text(payload.get("draft_reply") or "")
    if not draft_reply:
        nickname = payload.get("user_nickname_by_persona") or "你"
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
        return "story_material"
    return "shared_event"
