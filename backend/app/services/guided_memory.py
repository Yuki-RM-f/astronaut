from __future__ import annotations

import asyncio
import re
import threading
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.memory_card import MemoryCard
from app.models.persona import Persona
from app.providers.gateway import ProviderGateway
from app.schemas.guided_memory import (
    GuidedMemoryCandidate,
    GuidedMemoryCandidateResponse,
    GuidedMemoryKind,
)


REVIEWED_MEMORY_STATUSES = {"confirmed", "corrected"}
MAX_GUIDED_CANDIDATES = 3
GUIDED_KEYWORDS = {
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


def extract_guided_memory_candidates(
    db: Session,
    persona: Persona,
    kind: GuidedMemoryKind,
) -> GuidedMemoryCandidateResponse:
    memories = _reviewed_memories(db, persona)
    payload = {
        "kind": kind,
        "persona_card": {
            "id": persona.id,
            "name": persona.name,
            "relationship_to_user": persona.relationship_to_user,
            "user_nickname_by_persona": persona.user_nickname_by_persona,
        },
        "active_memory_cards": [_memory_payload(memory) for memory in memories],
        "max_candidates": MAX_GUIDED_CANDIDATES,
    }
    try:
        output = _run_gateway("guided_memory_extraction", payload).get("output") or {}
    except Exception:
        output = _deterministic_guided_candidates(payload)
    return _normalize_candidate_response(kind, memories, output)


def _reviewed_memories(db: Session, persona: Persona) -> list[MemoryCard]:
    memories = db.scalars(
        select(MemoryCard).where(
            MemoryCard.persona_id == persona.id,
            MemoryCard.deleted_at.is_(None),
            MemoryCard.status.in_(REVIEWED_MEMORY_STATUSES),
        )
    ).all()
    return sorted(
        memories,
        key=lambda memory: (
            0 if memory.is_important else 1,
            memory.category or "",
            -(memory.updated_at or memory.created_at or _utcnow()).timestamp(),
            memory.id,
        ),
    )


def _memory_payload(memory: MemoryCard) -> dict[str, Any]:
    content = memory.user_correction or memory.content
    return {
        "id": memory.id,
        "title": memory.title,
        "content": content,
        "category": memory.category,
        "status": memory.status,
        "is_important": memory.is_important,
        "confidence_level": memory.confidence_level,
        "confidence_score": memory.confidence_score,
        "source_quote": memory.source_quote or content,
        "source_location": memory.source_location,
    }


def _normalize_candidate_response(
    kind: GuidedMemoryKind,
    memories: list[MemoryCard],
    output: Any,
) -> GuidedMemoryCandidateResponse:
    if not isinstance(output, dict):
        output = {}
    by_id = {memory.id: memory for memory in memories}
    seen: set[str] = set()
    items: list[GuidedMemoryCandidate] = []
    for raw_item in output.get("items") or []:
        if not isinstance(raw_item, dict):
            continue
        memory_id = str(raw_item.get("memory_card_id") or raw_item.get("source_memory_id") or "").strip()
        if not memory_id or memory_id in seen or memory_id not in by_id:
            continue
        memory = by_id[memory_id]
        content = memory.user_correction or memory.content
        summary = _clean_text(str(raw_item.get("summary") or content))[:160]
        title = _clean_text(str(raw_item.get("title") or memory.title))[:80]
        suggested = _clean_text(
            str(raw_item.get("suggested_user_message") or _suggested_user_message(kind, summary))
        )[:220]
        if not summary or not suggested:
            continue
        items.append(
            GuidedMemoryCandidate(
                memory_card_id=memory_id,
                title=title or memory.title,
                summary=summary,
                suggested_user_message=suggested,
                source_quote=memory.source_quote or content,
                source_location=memory.source_location,
            )
        )
        seen.add(memory_id)
        if len(items) >= MAX_GUIDED_CANDIDATES:
            break
    empty_reason = None if items else _empty_reason(kind)
    if not items and output.get("empty_reason"):
        empty_reason = str(output["empty_reason"])
    return GuidedMemoryCandidateResponse(kind=kind, items=items, empty_reason=empty_reason)


def _deterministic_guided_candidates(payload: dict[str, Any]) -> dict[str, Any]:
    kind = str(payload.get("kind") or "regrets")
    keywords = GUIDED_KEYWORDS["wishes" if kind == "wishes" else "regrets"]
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
    items = []
    for _, memory in scored[:MAX_GUIDED_CANDIDATES]:
        summary = _clean_text(str(memory.get("content") or memory.get("source_quote") or ""))[:160]
        if not summary:
            continue
        items.append(
            {
                "memory_card_id": str(memory.get("id") or ""),
                "title": _clean_text(str(memory.get("title") or _candidate_title(kind))),
                "summary": summary,
                "suggested_user_message": _suggested_user_message(kind, summary),
                "source_quote": memory.get("source_quote"),
                "source_location": memory.get("source_location"),
            }
        )
    return {"items": items, "empty_reason": None if items else _empty_reason(kind)}


def _suggested_user_message(kind: str, summary: str) -> str:
    if kind == "wishes":
        return f"我想继续完成这件事：{summary}"
    return f"我想慢慢说说这段记忆：{summary}"


def _candidate_title(kind: str) -> str:
    return "记忆里的心愿" if kind == "wishes" else "记忆里的遗憾"


def _empty_reason(kind: str) -> str:
    label = "心愿" if kind == "wishes" else "遗憾"
    return f"没有在已审核记忆中找到可直接提取的{label}线索。"


def _clean_text(value: str) -> str:
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
        except BaseException as exc:  # pragma: no cover
            error["value"] = exc

    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()
    if error:
        raise error["value"]
    return result["value"]
