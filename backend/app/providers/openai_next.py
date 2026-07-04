from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.providers.minimax import (
    MEMORY_DOCUMENT_REPAIR_ATTEMPTS,
    _chat_messages,
    _clean_text,
    _memory_context_compression_messages,
    _memory_document_generation_messages,
    _memory_document_repair_messages,
    _parse_memory_document_json,
    _parse_story_output,
    _persona_profile_analysis_messages,
    _story_messages,
    _strip_json_fence,
)


class OpenAINextTextProviderError(RuntimeError):
    pass


TEXT_CAPABILITIES = {
    "chat_llm",
    "story_generation",
    "memory_context_compression",
    "persona_profile_analysis",
    "memory_document_generation",
}


class OpenAINextTextProvider:
    provider_name = "openai_next"
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
        return bool(
            self.settings.openai_next_api_key
            and self.settings.openai_next_base_url
            and self.settings.openai_next_model
        )

    async def run(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        if capability not in TEXT_CAPABILITIES:
            raise OpenAINextTextProviderError(
                f"OpenAI-Next text fallback does not support capability: {capability}"
            )
        if not self.is_configured:
            raise OpenAINextTextProviderError("OpenAI-Next text fallback is not configured")
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
        raise OpenAINextTextProviderError(f"Unsupported capability: {capability}")

    async def _chat_llm(self, payload: dict[str, Any]) -> dict[str, Any]:
        content, raw = await self._chat_completion(_chat_messages(payload))
        reply_text = _clean_text(content) or _clean_text(str(payload.get("draft_reply") or ""))
        if not reply_text:
            raise OpenAINextTextProviderError("OpenAI-Next chat response did not include reply text")
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
            raise OpenAINextTextProviderError(
                "OpenAI-Next Persona Engine response must be JSON"
            ) from exc
        if not isinstance(data, dict):
            raise OpenAINextTextProviderError(
                "OpenAI-Next Persona Engine response must be a JSON object"
            )
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
            except Exception as exc:
                last_error = str(exc)
                if attempt >= MEMORY_DOCUMENT_REPAIR_ATTEMPTS:
                    raise OpenAINextTextProviderError(
                        "OpenAI-Next memory document response must be strict JSON after "
                        f"{MEMORY_DOCUMENT_REPAIR_ATTEMPTS} repair attempts: {last_error}"
                    ) from exc
                messages = _memory_document_repair_messages(payload, content, last_error)
                continue
            data["trace_id"] = raw.get("id")
            return data
        raise OpenAINextTextProviderError(
            "OpenAI-Next memory document response must be strict JSON after "
            f"{MEMORY_DOCUMENT_REPAIR_ATTEMPTS} repair attempts: {last_error}"
        )

    async def _chat_completion(
        self,
        messages: list[dict[str, str]],
        **request_options: Any,
    ) -> tuple[str, dict[str, Any]]:
        data = await self._post_json(
            "chat/completions",
            {
                "model": self.settings.openai_next_model,
                "messages": messages,
                "stream": False,
                **request_options,
            },
        )
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise OpenAINextTextProviderError(
                "OpenAI-Next chat response did not include choices"
            )
        message = choices[0].get("message") if isinstance(choices[0], dict) else {}
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise OpenAINextTextProviderError(
                "OpenAI-Next chat response did not include content"
            )
        return content, data

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
            timeout=self.settings.openai_next_request_timeout_seconds,
            transport=self.transport,
        )

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.openai_next_api_key}"}

    def _url(self, path: str) -> str:
        return f"{self.settings.openai_next_base_url.rstrip('/')}/{path.lstrip('/')}"

    def _response_json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            raise OpenAINextTextProviderError(
                f"OpenAI-Next request failed with HTTP {exc.response.status_code}: {body}"
            ) from exc
        data = response.json()
        if not isinstance(data, dict):
            raise OpenAINextTextProviderError("OpenAI-Next response must be a JSON object")
        return data
