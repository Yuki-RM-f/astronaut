from __future__ import annotations

import base64
import json
import mimetypes
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings, get_settings


class ProviderConfigurationError(RuntimeError):
    pass


class ProviderRequestError(RuntimeError):
    pass


ALLOWED_MEMORY_CATEGORIES = {
    "basic_fact",
    "relationship",
    "preference",
    "habit",
    "expression_style",
    "shared_event",
    "value",
    "emotional_pattern",
    "story_material",
    "unknown",
}

CATEGORY_ALIASES = {
    "基本事实": "basic_fact",
    "事实": "basic_fact",
    "人物关系": "relationship",
    "关系": "relationship",
    "偏好": "preference",
    "喜好": "preference",
    "习惯": "habit",
    "表达习惯": "expression_style",
    "言语习惯": "expression_style",
    "说话风格": "expression_style",
    "口头禅": "expression_style",
    "共同经历": "shared_event",
    "共同事件": "shared_event",
    "价值观": "value",
    "价值": "value",
    "情绪模式": "emotional_pattern",
    "情感模式": "emotional_pattern",
    "故事素材": "story_material",
    "回忆素材": "story_material",
}


class DashScopeProvider:
    provider_name = "dashscope"
    provider_type = "third_party"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.dashscope_api_key)

    async def run(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured:
            raise ProviderConfigurationError("DASHSCOPE_API_KEY is not configured")
        if capability == "text_parser":
            return await self._text_parser(payload)
        if capability == "ocr":
            return await self._ocr(payload)
        if capability == "image_understanding":
            return await self._image_understanding(payload)
        if capability == "asr":
            return await self._asr(payload)
        if capability == "video_understanding":
            return await self._video_understanding(payload)
        if capability == "memory_extraction":
            return await self._memory_extraction(payload)
        raise ProviderRequestError(f"DashScope does not support capability: {capability}")

    async def _text_parser(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = _clean_text(str(payload.get("text") or payload.get("manual_text") or ""))
        if not text:
            text = _fallback_text(payload)
        prompt = (
            "请清洗并分段以下人物记忆资料，只输出 JSON："
            '{"cleaned_text":"...","chunks":[{"chunk_type":"text","content":"...",'
            '"summary":"...","source_location":"..."}]}。'
            "不要编造资料里没有的事实。\n\n"
            f"来源：{payload.get('source_location') or 'text:body'}\n资料：\n{text}"
        )
        content = await self._chat_completion(
            self.settings.qwen_text_model,
            [{"role": "user", "content": prompt}],
        )
        parsed = _json_object(content)
        chunks = parsed.get("chunks") if isinstance(parsed.get("chunks"), list) else []
        normalized_chunks: list[dict[str, str]] = []
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            content_text = _clean_text(str(chunk.get("content") or ""))
            if not content_text:
                continue
            normalized_chunks.append(
                {
                    "chunk_type": str(chunk.get("chunk_type") or "text"),
                    "content": content_text,
                    "summary": _clean_text(str(chunk.get("summary") or content_text[:80])),
                    "source_location": str(
                        chunk.get("source_location")
                        or payload.get("source_location")
                        or "text:body"
                    ),
                }
            )
        if not normalized_chunks:
            normalized_chunks = [
                {
                    "chunk_type": "text",
                    "content": text,
                    "summary": text[:80],
                    "source_location": str(payload.get("source_location") or "text:body"),
                }
            ]
        return {
            "cleaned_text": _clean_text(str(parsed.get("cleaned_text") or text)),
            "chunks": normalized_chunks,
        }

    async def _ocr(self, payload: dict[str, Any]) -> dict[str, Any]:
        image_url = _payload_file_data_url(payload)
        if not image_url:
            raise ProviderRequestError("OCR requires a readable image storage_url")
        content = await self._chat_completion(
            self.settings.qwen_ocr_model,
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请只提取图片中的可见文字；没有文字则返回空字符串。",
                        },
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
        )
        return {
            "ocr_text": _clean_text(content),
            "source_location": f"image:{payload.get('file_name') or 'image'}:ocr",
        }

    async def _image_understanding(self, payload: dict[str, Any]) -> dict[str, Any]:
        image_url = _payload_file_data_url(payload)
        if not image_url:
            raise ProviderRequestError("image understanding requires a readable storage_url")
        prompt = (
            "请分析这张图片，输出 JSON："
            '{"caption":"...","scene_metadata":{"scene_type":"...",'
            '"detected_people_count":0,"emotion_tone":"..."},'
            '"memory_candidate_text":"..."}。'
            "不要自动认定人物身份，除非用户说明已经标记。"
            f"\n用户说明：{payload.get('user_description') or '未填写'}"
            f"\nOCR 文本：{payload.get('ocr_text') or ''}"
        )
        content = await self._chat_completion(
            self.settings.qwen_vision_model,
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
        )
        parsed = _json_object(content)
        caption = _clean_text(str(parsed.get("caption") or content))
        scene_metadata = parsed.get("scene_metadata")
        if not isinstance(scene_metadata, dict):
            scene_metadata = {
                "scene_type": "unknown",
                "detected_people_count": 0,
                "emotion_tone": "unknown",
            }
        return {
            "caption": caption,
            "scene_metadata": scene_metadata,
            "memory_candidate_text": _clean_text(
                str(parsed.get("memory_candidate_text") or caption)
            ),
            "source_location": f"image:{payload.get('file_name') or 'image'}",
        }

    async def _asr(self, payload: dict[str, Any]) -> dict[str, Any]:
        audio_url = _payload_file_data_url(payload)
        if not audio_url:
            raise ProviderRequestError("ASR requires a readable audio storage_url")
        transcript = await self._chat_completion(
            self.settings.qwen_asr_model,
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_url,
                            },
                        },
                    ],
                }
            ],
            asr_options={"enable_itn": False},
        )
        return {
            "transcript": _clean_text(transcript),
            "sample_metadata": {
                "start_time": "00:00",
                "end_time": None,
                "speaker": "unknown",
                "language": "zh",
            },
            "source_location": f"audio:{payload.get('file_name') or 'audio'}#00:00",
        }

    async def _video_understanding(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = _payload_path(payload)
        if path is None:
            raise ProviderRequestError("video understanding requires a readable storage_url")

        transcript = ""
        frame_urls: list[str] = []
        extraction_metadata: dict[str, object] = {"ffmpeg_available": bool(shutil.which("ffmpeg"))}
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            if shutil.which("ffmpeg"):
                audio_path = tmp_path / "audio.wav"
                audio_result = subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(path),
                        "-vn",
                        "-ac",
                        "1",
                        "-ar",
                        "16000",
                        str(audio_path),
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                )
                extraction_metadata["audio_extract_returncode"] = audio_result.returncode
                if audio_result.returncode == 0 and audio_path.exists():
                    audio_payload = {
                        **payload,
                        "storage_url": audio_path.as_posix(),
                        "file_name": f"{payload.get('file_name') or 'video'}#audio.wav",
                    }
                    transcript = (await self._asr(audio_payload))["transcript"]

                frames_dir = tmp_path / "frames"
                frames_dir.mkdir(parents=True, exist_ok=True)
                frame_result = subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(path),
                        "-vf",
                        "fps=0.5",
                        "-frames:v",
                        "8",
                        str(frames_dir / "frame-%03d.jpg"),
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                )
                extraction_metadata["frame_extract_returncode"] = frame_result.returncode
                frame_urls = [_file_data_url(frame) for frame in sorted(frames_dir.glob("*.jpg"))]

            if len(frame_urls) >= 4:
                scene_summary = await self._describe_video_frames(payload, frame_urls, transcript)
            else:
                video_url = _file_data_url(path)
                scene_summary = await self._describe_video_blob(payload, video_url, transcript)

        summary = _clean_text(scene_summary)
        file_name = payload.get("file_name") or "video"
        return {
            "transcript": transcript,
            "scene_summary": summary,
            "timestamps": [{"start": "00:00", "end": None, "label": "dashscope_scene"}],
            "memory_candidate_text": _clean_text("。".join(part for part in [transcript, summary] if part)),
            "source_location": f"video:{file_name}#00:00",
            "extraction_metadata": extraction_metadata,
        }

    async def _memory_extraction(self, payload: dict[str, Any]) -> dict[str, Any]:
        content = _clean_text(str(payload.get("content") or ""))
        if not content:
            return {"memories": []}
        prompt = (
            "你是记忆抽取器。请从输入资料中抽取关于人物的结构化记忆。"
            "只输出 JSON 数组，不要输出 Markdown。每条包含 title、content、category、"
            "confidence_level、confidence_score、source_quote、source_location。"
            "不要把推测当事实。\n\n"
            f"来源位置：{payload.get('source_location') or ''}\n资料：\n{content}"
        )
        response = await self._chat_completion(
            self.settings.qwen_text_model,
            [{"role": "user", "content": prompt}],
        )
        candidates = _json_list(response)
        return {"memories": _normalize_memory_candidates(candidates, payload)}

    async def _describe_video_frames(
        self,
        payload: dict[str, Any],
        frame_urls: list[str],
        transcript: str,
    ) -> str:
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "请根据这些按时间顺序抽取的视频关键帧和音频转写，输出视频场景摘要。"
                    "说明人物、地点、事件、情绪和可作为记忆的片段。"
                    f"\n用户说明：{payload.get('user_description') or '未填写'}"
                    f"\n音频转写：{transcript}"
                ),
            },
            {"type": "video", "video": frame_urls, "fps": 0.5},
        ]
        return await self._chat_completion(
            self.settings.qwen_vision_model,
            [{"role": "user", "content": content}],
        )

    async def _describe_video_blob(
        self,
        payload: dict[str, Any],
        video_url: str,
        transcript: str,
    ) -> str:
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "请分析这段视频并输出场景摘要，包含人物、地点、事件、情绪和可引用记忆。"
                    f"\n用户说明：{payload.get('user_description') or '未填写'}"
                    f"\n音频转写：{transcript}"
                ),
            },
            {"type": "video_url", "video_url": {"url": video_url, "fps": 1}},
        ]
        return await self._chat_completion(
            self.settings.qwen_vision_model,
            [{"role": "user", "content": content}],
        )

    async def _chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        **request_options: Any,
    ) -> str:
        url = f"{self.settings.dashscope_compat_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.dashscope_api_key}",
            "Content-Type": "application/json",
        }
        request_json = {
            "model": model,
            "messages": messages,
            **request_options,
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.dashscope_request_timeout_seconds
            ) as client:
                response = await client.post(url, headers=headers, json=request_json)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            raise ProviderRequestError(
                f"DashScope request failed with HTTP {exc.response.status_code}: {body}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderRequestError(f"DashScope request failed: {exc}") from exc

        data = response.json()
        return _message_content(data)


def _payload_path(payload: dict[str, Any]) -> Path | None:
    storage_url = payload.get("storage_url")
    if not storage_url:
        return None
    path = Path(str(storage_url))
    if not path.exists() or not path.is_file():
        return None
    return path


def _payload_file_data_url(payload: dict[str, Any]) -> str | None:
    path = _payload_path(payload)
    if path is None:
        return None
    return _file_data_url(path)


def _file_data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _message_content(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderRequestError("DashScope response did not include choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise ProviderRequestError("DashScope response did not include a message")
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                value = item.get("text") or item.get("content")
                if value:
                    parts.append(str(value))
        return "\n".join(parts).strip()
    return str(content or "").strip()


def _json_object(content: str) -> dict[str, Any]:
    value = _json_value(content, default={})
    return value if isinstance(value, dict) else {}


def _json_list(content: str) -> list[Any]:
    value = _json_value(content, default=[])
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("memories", "items", "data"):
            nested = value.get(key)
            if isinstance(nested, list):
                return nested
    return []


def _json_value(content: str, *, default: Any) -> Any:
    text = content.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                return default
        start_candidates = [index for index in [text.find("{"), text.find("[")] if index >= 0]
        if not start_candidates:
            return default
        start = min(start_candidates)
        end = max(text.rfind("}"), text.rfind("]"))
        if end <= start:
            return default
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return default


def _normalize_memory_candidates(
    candidates: list[Any],
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    source_location = str(payload.get("source_location") or "material:body")
    normalized: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates[:6], start=1):
        if not isinstance(candidate, dict):
            continue
        content = _clean_text(str(candidate.get("content") or ""))
        if not content:
            continue
        confidence_score = candidate.get("confidence_score", 70)
        try:
            confidence_score = int(confidence_score)
        except (TypeError, ValueError):
            confidence_score = 70
        normalized.append(
            {
                "title": _clean_text(str(candidate.get("title") or f"资料记忆 {index}")),
                "content": content,
                "category": _memory_category(candidate.get("category")),
                "confidence_level": _confidence_level(
                    str(candidate.get("confidence_level") or ""),
                    confidence_score,
                ),
                "confidence_score": max(0, min(confidence_score, 100)),
                "source_quote": _clean_text(
                    str(candidate.get("source_quote") or content[:120])
                ),
                "source_location": str(candidate.get("source_location") or source_location),
            }
        )
    return normalized


def _memory_category(value: Any) -> str:
    category = _clean_text(str(value or ""))
    if category in ALLOWED_MEMORY_CATEGORIES:
        return category
    lowered = category.lower()
    if lowered in ALLOWED_MEMORY_CATEGORIES:
        return lowered
    return CATEGORY_ALIASES.get(category, "unknown")


def _confidence_level(value: str, score: int) -> str:
    if value in {"high", "medium", "low"}:
        return value
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _fallback_text(payload: dict[str, Any]) -> str:
    file_name = payload.get("file_name") or "资料"
    description = payload.get("user_description") or "未填写说明"
    return f"{file_name}：{description}"
