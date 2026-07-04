from __future__ import annotations

import asyncio
import re
import shutil
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message
from app.models.memory_card import MemoryCard
from app.models.persona import Persona
from app.providers.gateway import ProviderGateway


MEMORY_CONTEXT_ROOT = Path("storage") / "memory_context"
LONG_TERM_MEMORY_FILE = "long_term_memory.md"
SHORT_TERM_MEMORY_FILE = "short_term_memory.md"
REVIEWED_MEMORY_STATUSES = {"confirmed", "corrected"}
STATUS_PRIORITY = {"corrected": 2, "confirmed": 1}
MAX_LONG_TERM_MEMORY_CHARS = 12000
MAX_SHORT_TERM_MEMORY_CHARS = 6000
MAX_SELECTED_MEMORY_IDS = 8
RECENT_SHORT_TERM_MESSAGE_LIMIT = 24
MEMORY_ID_RE = re.compile(r"memory_card_id:\s*([A-Za-z0-9_-]+)")


@dataclass(frozen=True)
class MemoryMarkdownContext:
    long_term_memory_md: str
    short_term_memory_md: str
    selected_memory_ids: list[str]
    long_term_path: str
    short_term_path: str
    long_term_compressed: bool = False
    short_term_compressed: bool = False
    compression_failed: bool = False
    compression_provider: str | None = None


def memory_context_dir(persona_id: str) -> Path:
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", persona_id).strip("_")
    if not safe_id:
        safe_id = "unknown"
    root = MEMORY_CONTEXT_ROOT.resolve(strict=False)
    path = (MEMORY_CONTEXT_ROOT / safe_id).resolve(strict=False)
    path.relative_to(root)
    return path


def long_term_memory_path(persona_id: str) -> Path:
    return memory_context_dir(persona_id) / LONG_TERM_MEMORY_FILE


def short_term_memory_path(persona_id: str) -> Path:
    return memory_context_dir(persona_id) / SHORT_TERM_MEMORY_FILE


def remove_memory_context_files(persona_id: str) -> None:
    path = memory_context_dir(persona_id)
    if path.exists():
        shutil.rmtree(path)


def refresh_long_term_memory_md(db: Session, persona: Persona) -> str:
    memories = reviewed_memory_cards(db, persona.id)
    body = render_long_term_memory_md(persona, memories)
    return _write_text(long_term_memory_path(persona.id), body)


def refresh_short_term_memory_md(db: Session, persona: Persona) -> str:
    messages = db.scalars(
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.persona_id == persona.id,
            Conversation.deleted_at.is_(None),
            Message.deleted_at.is_(None),
        )
        .order_by(Message.created_at.asc(), Message.id.asc())
    ).all()
    body = render_short_term_memory_md(persona, messages)
    return _write_text(short_term_memory_path(persona.id), body)


def reviewed_memory_cards(db: Session, persona_id: str) -> list[MemoryCard]:
    memories = db.scalars(
        select(MemoryCard).where(
            MemoryCard.persona_id == persona_id,
            MemoryCard.deleted_at.is_(None),
            MemoryCard.status.in_(REVIEWED_MEMORY_STATUSES),
        )
    ).all()
    return sorted(
        memories,
        key=lambda memory: (
            memory.category or "",
            -STATUS_PRIORITY.get(memory.status, 0),
            -(memory.updated_at or memory.created_at or _utcnow()).timestamp(),
            memory.id,
        ),
    )


def build_chat_memory_context(
    db: Session,
    persona: Persona,
    user_message: str,
) -> MemoryMarkdownContext:
    long_md = refresh_long_term_memory_md(db, persona)
    short_md = refresh_short_term_memory_md(db, persona)
    selected_ids = extract_memory_ids(long_md)[:MAX_SELECTED_MEMORY_IDS]
    long_compressed = False
    short_compressed = False
    compression_failed = False
    compression_provider: str | None = None

    if len(long_md) > MAX_LONG_TERM_MEMORY_CHARS or len(short_md) > MAX_SHORT_TERM_MEMORY_CHARS:
        try:
            result = _run_gateway(
                "memory_context_compression",
                {
                    "persona_id": persona.id,
                    "persona_name": persona.name,
                    "user_message": user_message,
                    "long_term_memory_md": long_md,
                    "short_term_memory_md": short_md,
                    "memory_card_ids": selected_ids,
                    "max_long_term_chars": MAX_LONG_TERM_MEMORY_CHARS,
                    "max_short_term_chars": MAX_SHORT_TERM_MEMORY_CHARS,
                    "max_selected_memory_ids": MAX_SELECTED_MEMORY_IDS,
                },
            )
            output = result.get("output") or {}
            compressed_long = str(
                output.get("long_term_memory_md")
                or output.get("compressed_md")
                or long_md
            )
            compressed_short = str(output.get("short_term_memory_md") or short_md)
            allowed_ids = set(extract_memory_ids(long_md))
            compressed_ids = _clean_selected_ids(
                output.get("selected_memory_ids"),
                allowed_ids,
            )
            if compressed_ids:
                selected_ids = compressed_ids[:MAX_SELECTED_MEMORY_IDS]
            long_compressed = compressed_long != long_md
            short_compressed = compressed_short != short_md
            long_md = compressed_long
            short_md = compressed_short
            compression_provider = str(result.get("provider_name") or "")
        except Exception:
            compression_failed = True
            long_md = _trim_text(long_md, MAX_LONG_TERM_MEMORY_CHARS)
            short_md = _trim_text(short_md, MAX_SHORT_TERM_MEMORY_CHARS)
            selected_ids = extract_memory_ids(long_md)[:MAX_SELECTED_MEMORY_IDS] or selected_ids[
                :MAX_SELECTED_MEMORY_IDS
            ]
            long_compressed = True
            short_compressed = True

    return MemoryMarkdownContext(
        long_term_memory_md=long_md,
        short_term_memory_md=short_md,
        selected_memory_ids=selected_ids[:MAX_SELECTED_MEMORY_IDS],
        long_term_path=long_term_memory_path(persona.id).as_posix(),
        short_term_path=short_term_memory_path(persona.id).as_posix(),
        long_term_compressed=long_compressed,
        short_term_compressed=short_compressed,
        compression_failed=compression_failed,
        compression_provider=compression_provider or None,
    )


def render_long_term_memory_md(persona: Persona, memories: list[MemoryCard]) -> str:
    lines = [
        "# 长期记忆",
        "",
        f"- persona_id: {persona.id}",
        f"- persona_name: {_clean_line(persona.name)}",
        f"- generated_at: {_utcnow().isoformat()}",
        "",
    ]
    if not memories:
        lines.extend(["当前没有已确认或已修正的长期记忆。", ""])
        return "\n".join(lines)

    current_category: str | None = None
    for memory in memories:
        if memory.category != current_category:
            current_category = memory.category
            lines.extend([f"## {current_category}", ""])
        content = memory.user_correction or memory.content
        lines.extend(
            [
                f"### {_clean_line(memory.title)}",
                f"- memory_card_id: {memory.id}",
                f"- status: {memory.status}",
                f"- confidence: {memory.confidence_level} {memory.confidence_score}",
                f"- content: {_clean_line(content)}",
                f"- source_quote: {_clean_line(memory.source_quote or content)}",
                f"- source_location: {_clean_line(memory.source_location or '')}",
                "",
            ]
        )
    return "\n".join(lines)


def render_short_term_memory_md(persona: Persona, messages: list[Message]) -> str:
    older_messages = messages[:-RECENT_SHORT_TERM_MESSAGE_LIMIT]
    recent_messages = messages[-RECENT_SHORT_TERM_MESSAGE_LIMIT:]
    lines = [
        "# 短期记忆",
        "",
        f"- persona_id: {persona.id}",
        f"- persona_name: {_clean_line(persona.name)}",
        f"- generated_at: {_utcnow().isoformat()}",
        "",
        "## 压缩摘要",
        "",
    ]
    if older_messages:
        lines.extend(_short_summary_lines(older_messages))
    else:
        lines.append("暂无需要压缩的较早对话。")
    lines.extend(["", "## 最近消息", ""])
    if not recent_messages:
        lines.append("暂无近期对话。")
    for message in recent_messages:
        role = "用户" if message.role == "user" else "TA"
        created_at = message.created_at.isoformat() if message.created_at else ""
        lines.append(f"- [{created_at}] {role}: {_clean_line(message.content)}")
    lines.append("")
    return _trim_text("\n".join(lines), MAX_SHORT_TERM_MEMORY_CHARS * 2)


def extract_memory_ids(markdown: str) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for memory_id in MEMORY_ID_RE.findall(markdown):
        if memory_id not in seen:
            ids.append(memory_id)
            seen.add(memory_id)
    return ids


def _short_summary_lines(messages: list[Message]) -> list[str]:
    counts = {"user": 0, "persona": 0}
    for message in messages:
        counts[message.role] = counts.get(message.role, 0) + 1
    first = messages[0]
    last = messages[-1]
    return [
        f"- 已压缩较早消息 {len(messages)} 条；用户消息 {counts.get('user', 0)} 条，TA 回复 {counts.get('persona', 0)} 条。",
        f"- 时间范围: {first.created_at.isoformat() if first.created_at else ''} -> {last.created_at.isoformat() if last.created_at else ''}",
        f"- 最近一条较早消息摘要: {_clean_line(last.content)[:160]}",
    ]


def _clean_selected_ids(value: Any, allowed_ids: set[str]) -> list[str]:
    if not isinstance(value, list):
        return []
    selected: list[str] = []
    seen: set[str] = set()
    for item in value:
        memory_id = str(item)
        if memory_id in allowed_ids and memory_id not in seen:
            selected.append(memory_id)
            seen.add(memory_id)
    return selected


def _write_text(path: Path, body: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return body


def _trim_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= 80:
        return text[:max_chars]
    head = max_chars // 3
    tail = max_chars - head - 48
    return f"{text[:head]}\n\n... 已压缩省略 ...\n\n{text[-tail:]}"


def _clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _run_gateway(capability: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(ProviderGateway().run(capability, payload))

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def run_in_thread() -> None:
        try:
            result["value"] = asyncio.run(ProviderGateway().run(capability, payload))
        except BaseException as exc:  # pragma: no cover - re-raised in caller
            error["value"] = exc

    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()
    if error:
        raise error["value"]
    return result["value"]
