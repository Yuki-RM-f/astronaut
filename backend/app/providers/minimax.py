from __future__ import annotations

import mimetypes
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import httpx

from app.core.config import Settings, get_settings
from app.services.persona_engine_prompt import PERSONA_ENGINE_SYSTEM_PROMPT


class MiniMaxProviderError(RuntimeError):
    pass


MEMORY_DOCUMENT_REPAIR_ATTEMPTS = 3
MEMORY_DOCUMENT_REQUIRED_FIELDS = (
    "profile_summary",
    "trust_score",
    "trust_level",
    "trust_rationale",
    "suggestions",
)
MEMORY_DOCUMENT_TRUST_LEVELS = {"initial", "usable", "trusted", "high_trust"}
MEMORY_DOCUMENT_MODULES = (
    "basic_fact",
    "relationship",
    "preference",
    "habit",
    "expression_style",
    "shared_event",
)
MEMORY_DOCUMENT_MODULE_SET = set(MEMORY_DOCUMENT_MODULES)
THINK_BLOCK_RE = re.compile(r"<think\b[^>]*>.*?</think>", re.IGNORECASE | re.DOTALL)
THINK_OPEN_RE = re.compile(r"<think\b[^>]*>.*", re.IGNORECASE | re.DOTALL)
THINK_CLOSE_RE = re.compile(r"</think>", re.IGNORECASE)


class MiniMaxProvider:
    provider_name = "minimax"
    provider_type = "third_party"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.AsyncBaseTransport | httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.transport = transport

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.minimax_api_key and self.settings.minimax_base_url)

    @property
    def is_text_configured(self) -> bool:
        return bool(self.is_configured and self.settings.openai_compatible_model)

    async def run(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured:
            raise MiniMaxProviderError("MiniMax API key is not configured")
        if capability == "tts":
            return await self._tts(payload)
        if capability == "voice_clone":
            return await self._voice_clone(payload)
        if capability == "chat_llm":
            return await self._chat_llm(payload)
        if capability == "story_generation":
            return await self._story_generation(payload)
        if capability == "memory_context_compression":
            return await self._memory_context_compression(payload)
        if capability == "persona_profile_analysis":
            return await self._persona_profile_analysis(payload)
        if capability == "memory_document_generation":
            return await self._memory_document_generation(payload)
        if capability == "guided_memory_extraction":
            return await self._guided_memory_extraction(payload)
        raise MiniMaxProviderError(f"MiniMax does not support capability: {capability}")

    async def _chat_llm(self, payload: dict[str, Any]) -> dict[str, Any]:
        content, raw = await self._chat_completion(_chat_messages(payload))
        reply_text = _clean_text(content) or _clean_text(str(payload.get("draft_reply") or ""))
        if not reply_text:
            raise MiniMaxProviderError("MiniMax chat response did not include reply text")
        return {
            "reply_text": reply_text,
            "used_memory_ids": payload.get("used_memory_ids") or [],
            "prompt_variables": {
                "persona_name": payload.get("persona_name"),
                "persona_type": payload.get("persona_type"),
                "relationship_to_user": payload.get("relationship_to_user"),
                "user_nickname_by_persona": payload.get("user_nickname_by_persona"),
                "speaking_style": payload.get("speaking_style"),
                "emotional_style": payload.get("emotional_style"),
                "conversation_kind": payload.get("conversation_kind"),
                "confidence_score": payload.get("confidence_score"),
            },
            "trace_id": raw.get("id"),
        }

    async def _story_generation(self, payload: dict[str, Any]) -> dict[str, Any]:
        content, raw = await self._chat_completion(_story_messages(payload))
        story = _parse_story_output(content, payload)
        story["trace_id"] = raw.get("id")
        return story

    async def _memory_context_compression(self, payload: dict[str, Any]) -> dict[str, Any]:
        content, raw = await self._chat_completion(_memory_context_compression_messages(payload))
        try:
            data = json.loads(_strip_json_fence(content))
        except json.JSONDecodeError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        long_md = str(
            data.get("long_term_memory_md")
            or data.get("compressed_md")
            or payload.get("long_term_memory_md")
            or ""
        )
        short_md = str(data.get("short_term_memory_md") or payload.get("short_term_memory_md") or "")
        raw_ids = data.get("selected_memory_ids")
        selected_ids = [str(item) for item in raw_ids] if isinstance(raw_ids, list) else []
        return {
            "long_term_memory_md": long_md,
            "short_term_memory_md": short_md,
            "selected_memory_ids": selected_ids,
            "trace_id": raw.get("id"),
        }

    async def _persona_profile_analysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        content, raw = await self._chat_completion(_persona_profile_analysis_messages(payload))
        try:
            data = json.loads(_strip_json_fence(content))
        except json.JSONDecodeError as exc:
            raise MiniMaxProviderError("MiniMax Persona Engine response must be JSON") from exc
        if not isinstance(data, dict):
            raise MiniMaxProviderError("MiniMax Persona Engine response must be a JSON object")
        data["trace_id"] = raw.get("id")
        return data

    async def _memory_document_generation(self, payload: dict[str, Any]) -> dict[str, Any]:
        messages = _memory_document_generation_messages(payload)
        last_error = ""
        for attempt in range(MEMORY_DOCUMENT_REPAIR_ATTEMPTS + 1):
            content, raw = await self._chat_completion(
                messages,
                response_format={"type": "json_object"},
            )
            try:
                data = _parse_memory_document_json(content)
            except MiniMaxProviderError as exc:
                last_error = str(exc)
                if attempt >= MEMORY_DOCUMENT_REPAIR_ATTEMPTS:
                    raise MiniMaxProviderError(
                        "MiniMax memory document response must be strict JSON after "
                        f"{MEMORY_DOCUMENT_REPAIR_ATTEMPTS} repair attempts: {last_error}"
                    ) from exc
                messages = _memory_document_repair_messages(payload, content, last_error)
                continue
            data["trace_id"] = raw.get("id")
            return data
        raise MiniMaxProviderError(
            "MiniMax memory document response must be strict JSON after "
            f"{MEMORY_DOCUMENT_REPAIR_ATTEMPTS} repair attempts: {last_error}"
        )

    async def _guided_memory_extraction(self, payload: dict[str, Any]) -> dict[str, Any]:
        content, raw = await self._chat_completion(
            _guided_memory_extraction_messages(payload),
            response_format={"type": "json_object"},
        )
        output = _parse_guided_memory_output(content, payload)
        output["trace_id"] = raw.get("id")
        return output

    async def _tts(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = _clean_text(str(payload.get("text") or ""))
        if not text:
            raise MiniMaxProviderError("MiniMax TTS requires text")
        request_json = {
            "model": self.settings.minimax_tts_model,
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": _voice_id_from_payload(
                    payload,
                    self.settings.minimax_default_voice_id,
                ),
                "speed": 1,
                "vol": 1,
                "pitch": 0,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
            },
            "subtitle_enable": False,
            "output_format": "url",
            "aigc_watermark": False,
        }
        data = await self._post_json("t2a_v2", request_json)
        audio_url = ((data.get("data") or {}).get("audio") or "").strip()
        if not audio_url:
            raise MiniMaxProviderError("MiniMax TTS response did not include audio")
        extra_info = data.get("extra_info") if isinstance(data.get("extra_info"), dict) else {}
        return {
            "audio_url": audio_url,
            "duration_ms": extra_info.get("audio_length"),
            "voice_status": payload.get("voice_status") or "default_tts",
            "voice_model_id": payload.get("voice_model_id"),
            "default_tts_notice": payload.get("default_tts_notice"),
            "trace_id": data.get("trace_id"),
            "extra_info": extra_info,
        }

    async def _voice_clone(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("simulate_failure"):
            return {
                "clone_status": "failed",
                "error_message": "simulated MiniMax voice clone failure; fallback to default TTS",
            }
        storage_url = payload.get("storage_url")
        if not storage_url:
            raise MiniMaxProviderError("MiniMax voice clone requires storage_url")
        audio_path = Path(str(storage_url))
        if not audio_path.exists() or not audio_path.is_file():
            raise MiniMaxProviderError(f"MiniMax voice clone audio not found: {storage_url}")

        file_id = await self._upload_voice_clone_audio(audio_path, payload)
        voice_id = _clone_voice_id(str(payload.get("voice_model_id") or "voice-model"))
        preview_text = _clean_text(str(payload.get("sample_text") or ""))[:1000]
        if not preview_text:
            preview_text = "你好，这是一段音色复刻试听。"
        request_json = {
            "file_id": file_id,
            "voice_id": voice_id,
            "text": preview_text,
            "model": self.settings.minimax_clone_model,
            "need_noise_reduction": False,
            "need_volume_normalization": False,
            "aigc_watermark": False,
        }
        data = await self._post_json("voice_clone", request_json)
        return {
            "clone_status": "succeeded",
            "model_artifact_url": f"minimax://voice/{voice_id}",
            "preview_audio_url": data.get("demo_audio") or payload.get("sample_audio_url"),
            "quality_score": 82,
            "extra_info": data.get("extra_info") or {},
        }

    async def _upload_voice_clone_audio(
        self,
        path: Path,
        payload: dict[str, Any],
    ) -> int | str:
        url = self._url("files/upload")
        mime_type = payload.get("mime_type") or mimetypes.guess_type(path.name)[0]
        with path.open("rb") as file_handle:
            async with self._client() as client:
                response = await client.post(
                    url,
                    headers=self._auth_headers(),
                    data={"purpose": "voice_clone"},
                    files={
                        "file": (
                            payload.get("file_name") or path.name,
                            file_handle,
                            mime_type or "application/octet-stream",
                        )
                    },
                )
        data = self._response_json(response)
        file_data = data.get("file") if isinstance(data.get("file"), dict) else {}
        file_id = file_data.get("file_id")
        if file_id is None:
            raise MiniMaxProviderError("MiniMax upload response did not include file_id")
        return file_id

    async def _post_json(self, path: str, request_json: dict[str, Any]) -> dict[str, Any]:
        async with self._client() as client:
            response = await client.post(
                self._url(path),
                headers={**self._auth_headers(), "Content-Type": "application/json"},
                json=request_json,
            )
        return self._response_json(response)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self.settings.minimax_request_timeout_seconds,
            transport=self.transport,
        )

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.minimax_api_key}"}

    def _url(self, path: str) -> str:
        return f"{self.settings.minimax_base_url.rstrip('/')}/{path.lstrip('/')}"

    def _response_json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            raise MiniMaxProviderError(
                f"MiniMax request failed with HTTP {exc.response.status_code}: {body}"
            ) from exc
        data = response.json()
        base_resp = data.get("base_resp")
        if isinstance(base_resp, dict) and base_resp.get("status_code") not in {None, 0}:
            raise MiniMaxProviderError(
                f"MiniMax request failed: {base_resp.get('status_msg') or base_resp}"
            )
        return data

    async def _chat_completion(
        self,
        messages: list[dict[str, str]],
        **request_options: Any,
    ) -> tuple[str, dict[str, Any]]:
        if not self.settings.openai_compatible_model:
            raise MiniMaxProviderError("MiniMax chat model is not configured")
        data = await self._post_json(
            "chat/completions",
            {
                "model": self.settings.openai_compatible_model,
                "messages": messages,
                "stream": False,
                **request_options,
            },
        )
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise MiniMaxProviderError("MiniMax chat response did not include choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else {}
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise MiniMaxProviderError("MiniMax chat response did not include content")
        return content, data


def _voice_id_from_payload(payload: dict[str, Any], default_voice_id: str) -> str:
    voice_id = str(payload.get("voice_id") or "").strip()
    if voice_id:
        return voice_id
    artifact = str(payload.get("model_artifact_url") or "").strip()
    if artifact.startswith("minimax://system-voice/"):
        return unquote(artifact.removeprefix("minimax://system-voice/"))
    if artifact.startswith("minimax://voice/"):
        return artifact.rsplit("/", 1)[-1]
    return default_voice_id


def _clone_voice_id(voice_model_id: str) -> str:
    compact = re.sub(r"[^A-Za-z0-9]+", "", voice_model_id)[:8] or "voice"
    return f"PMV{compact}"


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _chat_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    guided_system_prompt = _clean_text(str(payload.get("guided_system_prompt") or ""))
    system = "\n".join(
        [
            f"You are {payload.get('persona_name') or 'the persona'}.",
            "Reply as this persona in first person.",
            "Use the same language as the user message.",
            "Use only the provided profile, memories, and conversation history.",
            "If evidence is insufficient, say you cannot be certain.",
            "Do not claim to be an AI assistant or a resurrected real person.",
        ]
        + ([guided_system_prompt] if guided_system_prompt else [])
    )
    messages = [{"role": "system", "content": system}]
    for item in payload.get("conversation_history") or []:
        role = "assistant" if item.get("role") == "persona" else "user"
        content = _clean_text(str(item.get("content") or ""))
        if content:
            messages.append({"role": role, "content": content})
    messages.append(
        {
            "role": "user",
            "content": _json_context(
                {
                    "user_message": payload.get("user_message"),
                    "user_nickname_by_persona": payload.get("user_nickname_by_persona"),
                    "relationship_to_user": payload.get("relationship_to_user"),
                    "speaking_style": payload.get("speaking_style"),
                    "emotional_style": payload.get("emotional_style"),
                    "forbidden_expressions": payload.get("forbidden_expressions"),
                    "context_kind": payload.get("context_kind") or "general",
                    "conversation_kind": payload.get("conversation_kind") or "chat",
                    "system_prompt_kind": payload.get("system_prompt_kind") or "general",
                    "guided_system_prompt": guided_system_prompt,
                    "profile_summary": payload.get("profile_summary"),
                    "long_term_memory_md": payload.get("long_term_memory_md") or "",
                    "short_term_memory_md": payload.get("short_term_memory_md") or "",
                    "selected_memory_ids": payload.get("selected_memory_ids") or [],
                    "draft_reply": payload.get("draft_reply"),
                }
            ),
        }
    )
    return messages


def _story_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    system = "\n".join(
        [
            f"You are {payload.get('persona_name') or 'the persona'}.",
            "用中文第一人称给用户讲一段温暖的回忆故事。",
            "只使用用户消息提供的长期记忆 Markdown、短期记忆 Markdown 和 retrieved_memories，不要补造事实。",
            "source_memory_ids 只能从提供的 source_memory_ids 或 retrieved_memories.id 中复制。",
            "只返回一个 strict JSON object，字段为 title、content、source_memory_ids、source_memories。",
            "不要输出 Markdown 代码块、解释、思考过程或 <think> 标签。",
        ]
    )
    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": _json_context(
                {
                    "story_theme": payload.get("story_theme"),
                    "user_nickname_by_persona": payload.get("user_nickname_by_persona"),
                    "long_term_memory_md": payload.get("long_term_memory_md") or "",
                    "short_term_memory_md": payload.get("short_term_memory_md") or "",
                    "source_memory_ids": payload.get("source_memory_ids") or [],
                    "retrieved_memories": payload.get("retrieved_memories") or [],
                }
            ),
        },
    ]


def _memory_context_compression_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    system = "\n".join(
        [
            "Compress persona memory Markdown for a chat turn.",
            "Keep only evidence useful for the current user message.",
            "Return strict JSON with long_term_memory_md, short_term_memory_md, and selected_memory_ids.",
            "selected_memory_ids must be copied from memory_card_id values present in the input.",
        ]
    )
    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": _json_context(
                {
                    "user_message": payload.get("user_message"),
                    "long_term_memory_md": payload.get("long_term_memory_md") or "",
                    "short_term_memory_md": payload.get("short_term_memory_md") or "",
                    "memory_card_ids": payload.get("memory_card_ids") or [],
                    "max_long_term_chars": payload.get("max_long_term_chars"),
                    "max_short_term_chars": payload.get("max_short_term_chars"),
                    "max_selected_memory_ids": payload.get("max_selected_memory_ids"),
                }
            ),
        },
    ]


def _guided_memory_extraction_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    system = "\n".join(
        [
            "Extract guided regrets or wishes from reviewed persona memories.",
            "Use only active_memory_cards provided by the user message.",
            "Return one strict JSON object with items and empty_reason.",
            "Each item must copy memory_card_id from an input memory id.",
            "Each item must include title, summary, and suggested_user_message.",
            "Return at most max_candidates items.",
        ]
    )
    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": _json_context(
                {
                    "kind": payload.get("kind"),
                    "persona_card": payload.get("persona_card") or {},
                    "active_memory_cards": payload.get("active_memory_cards") or [],
                    "max_candidates": payload.get("max_candidates") or 3,
                }
            ),
        },
    ]


def _persona_profile_analysis_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": PERSONA_ENGINE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _json_context(
                {
                    "persona_card": payload.get("persona_card") or {},
                    "parsed_chunks": payload.get("parsed_chunks") or [],
                    "active_memory_cards": payload.get("active_memory_cards") or [],
                    "source_metadata": payload.get("source_metadata") or [],
                    "current_profile": payload.get("current_profile") or {},
                }
            ),
        },
    ]


def _parse_memory_document_json(content: str) -> dict[str, Any]:
    raw_content = _first_json_object(_strip_json_fence(_strip_model_thinking(content)))
    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise MiniMaxProviderError(
            "MiniMax memory document response must be strict JSON"
        ) from exc
    if not isinstance(data, dict):
        raise MiniMaxProviderError("MiniMax memory document response must be a JSON object")
    for field in MEMORY_DOCUMENT_REQUIRED_FIELDS:
        if field not in data:
            raise MiniMaxProviderError(f"MiniMax memory document missing field: {field}")

    profile_summary = _required_string(data.get("profile_summary"), "profile_summary")
    trust_score = data.get("trust_score")
    if not isinstance(trust_score, int) or isinstance(trust_score, bool):
        raise MiniMaxProviderError("MiniMax memory document trust_score must be an integer")
    if trust_score < 0 or trust_score > 100:
        raise MiniMaxProviderError("MiniMax memory document trust_score must be between 0 and 100")
    trust_level = _required_string(data.get("trust_level"), "trust_level")
    if trust_level not in MEMORY_DOCUMENT_TRUST_LEVELS:
        raise MiniMaxProviderError(
            "MiniMax memory document trust_level must be one of: "
            + ", ".join(sorted(MEMORY_DOCUMENT_TRUST_LEVELS))
        )
    trust_rationale = _required_string(data.get("trust_rationale"), "trust_rationale")
    suggestions = data.get("suggestions")
    if not isinstance(suggestions, list) or not suggestions:
        raise MiniMaxProviderError("MiniMax memory document suggestions must be a non-empty array")
    normalized_suggestions = [
        str(item).strip() for item in suggestions if str(item).strip()
    ]
    if not normalized_suggestions:
        raise MiniMaxProviderError("MiniMax memory document suggestions must include text")

    return {
        "profile_summary": profile_summary,
        "trust_score": trust_score,
        "trust_level": trust_level,
        "trust_rationale": trust_rationale,
        "suggestions": normalized_suggestions,
    }


def _parse_guided_memory_output(content: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        data = json.loads(_first_json_object(_strip_json_fence(_strip_model_thinking(content))))
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    items: list[dict[str, Any]] = []
    for raw_item in data.get("items") or []:
        if not isinstance(raw_item, dict):
            continue
        memory_id = _clean_text(
            str(raw_item.get("memory_card_id") or raw_item.get("source_memory_id") or "")
        )
        summary = _clean_text(str(raw_item.get("summary") or ""))
        suggested = _clean_text(str(raw_item.get("suggested_user_message") or ""))
        if not memory_id or not summary or not suggested:
            continue
        items.append(
            {
                "memory_card_id": memory_id,
                "title": _clean_text(str(raw_item.get("title") or "记忆线索")),
                "summary": summary,
                "suggested_user_message": suggested,
                "source_quote": raw_item.get("source_quote"),
                "source_location": raw_item.get("source_location"),
            }
        )
        if len(items) >= int(payload.get("max_candidates") or 3):
            break
    empty_reason = None if items else str(data.get("empty_reason") or _guided_empty_reason(payload))
    return {"items": items, "empty_reason": empty_reason}


def _guided_empty_reason(payload: dict[str, Any]) -> str:
    label = "心愿" if payload.get("kind") == "wishes" else "遗憾"
    return f"没有在已审核记忆中找到可直接提取的{label}线索。"


def _normalize_memory_document_json(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MiniMaxProviderError(
            "MiniMax memory document structured_memory_document_json must be a JSON object"
        )
    raw_modules = value.get("modules")
    if not isinstance(raw_modules, dict):
        raise MiniMaxProviderError(
            "MiniMax memory document structured_memory_document_json.modules must be an object"
        )
    unknown_modules = sorted(set(raw_modules) - MEMORY_DOCUMENT_MODULE_SET)
    if unknown_modules:
        raise MiniMaxProviderError(
            "MiniMax memory document modules contains unknown module: "
            + ", ".join(unknown_modules)
        )

    modules: dict[str, list[dict[str, Any]]] = {}
    for module in MEMORY_DOCUMENT_MODULES:
        raw_items = raw_modules.get(module, [])
        if not isinstance(raw_items, list):
            raise MiniMaxProviderError(
                f"MiniMax memory document module {module} must be an array"
            )
        modules[module] = [
            _normalize_memory_document_item(item, module, index)
            for index, item in enumerate(raw_items, start=1)
        ]

    sources = value.get("sources")
    normalized_sources = [
        source for source in sources if isinstance(source, dict)
    ] if isinstance(sources, list) else []
    unclassified = value.get("unclassified")
    warnings = value.get("warnings")
    return {
        "sources": normalized_sources,
        "modules": modules,
        "unclassified": unclassified if isinstance(unclassified, list) else [],
        "warnings": [str(item) for item in warnings or [] if str(item).strip()]
        if isinstance(warnings, list)
        else [],
    }


def _normalize_memory_document_item(
    value: object,
    module: str,
    index: int,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MiniMaxProviderError(
            f"MiniMax memory document module {module} item {index} must be an object"
        )
    title = _required_string(value.get("title"), f"{module}[{index}].title")
    content = _required_string(value.get("content"), f"{module}[{index}].content")
    category = str(value.get("category") or "").strip()
    if category != module:
        raise MiniMaxProviderError(
            f"MiniMax memory document module {module} item {index} category must equal {module}"
        )
    confidence_level = str(value.get("confidence_level") or "").strip()
    if confidence_level not in {"high", "medium", "low"}:
        raise MiniMaxProviderError(
            f"MiniMax memory document module {module} item {index} confidence_level is invalid"
        )
    confidence_score = value.get("confidence_score")
    if not isinstance(confidence_score, int) or isinstance(confidence_score, bool):
        raise MiniMaxProviderError(
            f"MiniMax memory document module {module} item {index} confidence_score must be an integer"
        )
    if confidence_score < 0 or confidence_score > 100:
        raise MiniMaxProviderError(
            f"MiniMax memory document module {module} item {index} confidence_score must be between 0 and 100"
        )
    source_quote = _required_string(
        value.get("source_quote"),
        f"{module}[{index}].source_quote",
    )
    source_location = _required_string(
        value.get("source_location"),
        f"{module}[{index}].source_location",
    )
    normalized = {
        **value,
        "title": title,
        "content": content,
        "category": module,
        "confidence_level": confidence_level,
        "confidence_score": confidence_score,
        "source_quote": source_quote,
        "source_location": source_location,
    }
    if "is_important" in value:
        normalized["is_important"] = bool(value.get("is_important"))
    if value.get("id"):
        normalized["id"] = str(value.get("id"))
    if value.get("status"):
        normalized["status"] = str(value.get("status"))
    return normalized


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MiniMaxProviderError(f"MiniMax memory document {field} must be a non-empty string")
    return value.strip()


def _memory_document_generation_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    system = "\n".join(
        [
            "You evaluate the current persona memory evidence and produce profile summary and trust metadata.",
            "Use only provided persona, material, parsed chunk, and active memory card evidence.",
            "ONLY return one strict JSON object. Do not wrap it in Markdown fences. Do not add prose before or after JSON.",
            "The JSON object must exactly use these required top-level fields: profile_summary, trust_score, trust_level, trust_rationale, suggestions.",
            "profile_summary must be a non-empty Chinese string grounded in uploaded evidence and reviewed memory cards.",
            "Do not output Markdown or structured_memory_document_json. The backend will render structured document JSON and Markdown deterministically from active MemoryCard records.",
            "trust_score must be an integer from 0 to 100.",
            "trust_level must be one of: initial, usable, trusted, high_trust.",
            "trust_rationale must be a non-empty Chinese string.",
            "suggestions must be a non-empty array of Chinese strings.",
            "Memory cards marked is_important=true must be prioritized in profile_summary and trust rationale.",
        ]
    )
    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": _json_context(
                {
                    "persona_card": payload.get("persona_card") or {},
                    "parsed_chunks": payload.get("parsed_chunks") or [],
                    "active_memory_cards": payload.get("active_memory_cards") or [],
                    "source_metadata": payload.get("source_metadata") or [],
                    "current_profile": payload.get("current_profile") or {},
                }
            ),
        },
    ]


def _memory_document_repair_messages(
    payload: dict[str, Any],
    invalid_output: str,
    validation_error: str,
) -> list[dict[str, str]]:
    return _memory_document_generation_messages(payload) + [
        {
            "role": "user",
            "content": "\n".join(
                [
                    "JSON validation error:",
                    validation_error,
                    "Previous invalid output:",
                    invalid_output[:4000],
                    "Return the corrected strict JSON object only. Do not include Markdown, Markdown fences, explanation, or <think>.",
                    "Remember: do not include structured_memory_document_json or structured_memory_md.",
                ]
            ),
        }
    ]


def _json_context(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _parse_story_output(content: str, payload: dict[str, Any]) -> dict[str, Any]:
    cleaned_content = _strip_model_thinking(content)
    try:
        data = json.loads(_first_json_object(_strip_json_fence(cleaned_content)))
    except json.JSONDecodeError:
        return _fallback_story_output(cleaned_content, payload)
    if not isinstance(data, dict):
        raise MiniMaxProviderError("MiniMax story response must be a JSON object")
    memories = payload.get("retrieved_memories") or []
    fallback_ids = [str(item.get("id")) for item in memories if item.get("id")]
    source_memory_ids = data.get("source_memory_ids")
    if not isinstance(source_memory_ids, list):
        source_memory_ids = fallback_ids
    source_memories = data.get("source_memories")
    if not isinstance(source_memories, list):
        source_memories = []
    story_content = _clean_text(_strip_model_thinking(str(data.get("content") or "")))
    if not story_content:
        story_content = _deterministic_story_content(payload)
    return {
        "title": _clean_text(
            _strip_model_thinking(str(data.get("title") or payload.get("story_theme") or ""))
        ),
        "content": story_content,
        "source_memory_ids": [str(item) for item in source_memory_ids],
        "source_memories": source_memories,
    }


def _fallback_story_output(content: str, payload: dict[str, Any]) -> dict[str, Any]:
    source_memories = _source_memories_from_payload(payload)
    story_content = _clean_text(_strip_model_thinking(content))
    if not story_content:
        story_content = _deterministic_story_content(payload)
    return {
        "title": _clean_text(str(payload.get("story_theme") or "memory story")),
        "content": story_content,
        "source_memory_ids": [item["memory_card_id"] for item in source_memories],
        "source_memories": source_memories,
    }


def _source_memories_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for memory in payload.get("retrieved_memories") or []:
        memory_id = memory.get("id") or memory.get("memory_card_id")
        if not memory_id:
            continue
        content = str(memory.get("content") or "")
        sources.append(
            {
                "memory_card_id": str(memory_id),
                "title": str(memory.get("title") or "source memory"),
                "quote": str(memory.get("quote") or memory.get("source_quote") or content),
                "source_location": memory.get("source_location"),
            }
        )
    return sources


def _strip_json_fence(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped


def _strip_model_thinking(text: str) -> str:
    stripped = THINK_BLOCK_RE.sub("", text)
    stripped = THINK_CLOSE_RE.sub("", stripped)
    if re.search(r"<think\b", stripped, re.IGNORECASE):
        stripped = THINK_OPEN_RE.sub("", stripped)
    return stripped.strip()


def _first_json_object(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("{"):
        candidate = _json_object_slice(stripped, 0)
        if candidate:
            return candidate
    start = stripped.find("{")
    while start >= 0:
        candidate = _json_object_slice(stripped, start)
        if candidate:
            return candidate
        start = stripped.find("{", start + 1)
    return stripped


def _json_object_slice(text: str, start: int) -> str | None:
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _deterministic_story_content(payload: dict[str, Any]) -> str:
    nickname = _clean_text(str(payload.get("user_nickname_by_persona") or "你"))
    theme = _clean_text(str(payload.get("story_theme") or "共同回忆"))
    lines = []
    for memory in payload.get("retrieved_memories") or []:
        text = _clean_text(
            str(memory.get("content") or memory.get("quote") or memory.get("title") or "")
        )
        if text:
            lines.append(text)
    if not lines:
        return f"{nickname}，这段关于{theme}的回忆，我还需要更多已确认的资料，不能硬说成真的。"
    return (
        f"{nickname}，我想给你讲一段关于{theme}的回忆。我记得"
        f"{'；'.join(lines[:3])}。这些话只来自已经整理好的记忆来源。"
    )
