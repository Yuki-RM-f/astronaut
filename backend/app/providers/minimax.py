from __future__ import annotations

import mimetypes
import json
import re
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.services.persona_engine_prompt import PERSONA_ENGINE_SYSTEM_PROMPT


class MiniMaxProviderError(RuntimeError):
    pass


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
    ) -> tuple[str, dict[str, Any]]:
        if not self.settings.openai_compatible_model:
            raise MiniMaxProviderError("MiniMax chat model is not configured")
        data = await self._post_json(
            "chat/completions",
            {
                "model": self.settings.openai_compatible_model,
                "messages": messages,
                "stream": False,
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
    if artifact.startswith("minimax://voice/"):
        return artifact.rsplit("/", 1)[-1]
    return default_voice_id


def _clone_voice_id(voice_model_id: str) -> str:
    compact = re.sub(r"[^A-Za-z0-9]+", "", voice_model_id)[:8] or "voice"
    return f"PMV{compact}"


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _chat_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    system = "\n".join(
        [
            f"You are {payload.get('persona_name') or 'the persona'}.",
            "Reply as this persona in first person.",
            "Use the same language as the user message.",
            "Use only the provided profile, memories, and conversation history.",
            "If evidence is insufficient, say you cannot be certain.",
            "Do not claim to be an AI assistant or a resurrected real person.",
        ]
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
            "Generate a warm first-person memory story for the user.",
            "Use only the provided reviewed memories.",
            "Return strict JSON with title, content, source_memory_ids, and source_memories.",
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


def _json_context(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _parse_story_output(content: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        data = json.loads(_strip_json_fence(content))
    except json.JSONDecodeError:
        return _fallback_story_output(content, payload)
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
    return {
        "title": _clean_text(str(data.get("title") or payload.get("story_theme") or "")),
        "content": _clean_text(str(data.get("content") or "")),
        "source_memory_ids": [str(item) for item in source_memory_ids],
        "source_memories": source_memories,
    }


def _fallback_story_output(content: str, payload: dict[str, Any]) -> dict[str, Any]:
    source_memories = _source_memories_from_payload(payload)
    return {
        "title": _clean_text(str(payload.get("story_theme") or "memory story")),
        "content": _clean_text(content),
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
