from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.memory_card import MemoryCard
from app.models.persona import Persona
from app.services.memory_markdown import refresh_long_term_memory_md, refresh_short_term_memory_md


INACTIVE_STATUSES = {"rejected", "disabled"}


@dataclass(frozen=True)
class SearchResult:
    memory: MemoryCard
    relevance_score: float
    matched_terms: list[str]
    source_excerpt: str | None


def semantic_search(
    db: Session,
    *,
    persona: Persona,
    query: str,
    top_k: int = 5,
) -> list[SearchResult]:
    memories = db.scalars(
        select(MemoryCard).where(
            MemoryCard.persona_id == persona.id,
            MemoryCard.deleted_at.is_(None),
            MemoryCard.status.not_in(INACTIVE_STATUSES),
        )
    ).all()
    query_terms = _tokens(query)
    if not query_terms:
        return []

    long_term_memory_md = refresh_long_term_memory_md(db, persona)
    short_term_memory_md = refresh_short_term_memory_md(db, persona)
    documents = [
        _document(memory, long_term_memory_md, short_term_memory_md) for memory in memories
    ]
    document_tokens = [_tokens(document) for document in documents]
    idf = _idf(document_tokens)
    query_vector = _vector(query_terms, idf)
    results: list[SearchResult] = []
    for memory, document, terms in zip(memories, documents, document_tokens, strict=True):
        score = _cosine(query_vector, _vector(terms, idf))
        if _normalize(query) in _normalize(document):
            score = max(score, 0.95)
        if score <= 0:
            continue
        matched_terms = sorted(set(query_terms) & set(terms))
        results.append(
            SearchResult(
                memory=memory,
                relevance_score=round(score, 4),
                matched_terms=matched_terms or [query.strip()],
                source_excerpt=_excerpt(
                    memory,
                    query,
                    _memory_context_excerpt(long_term_memory_md, memory.id),
                ),
            )
        )
    return sorted(results, key=lambda item: item.relevance_score, reverse=True)[:top_k]


def _document(
    memory: MemoryCard,
    long_term_memory_md: str,
    short_term_memory_md: str,
) -> str:
    return "\n".join(
        item
        for item in [
            memory.title,
            memory.content,
            memory.source_quote,
            memory.user_correction,
            memory.source_location,
            _memory_context_excerpt(long_term_memory_md, memory.id),
            _memory_context_excerpt(short_term_memory_md, memory.id),
        ]
        if item
    )


def _tokens(text: str) -> list[str]:
    normalized = _normalize(text)
    ascii_words = re.findall(r"[a-z0-9_]+", normalized)
    chinese = re.findall(r"[\u4e00-\u9fff]+", normalized)
    grams: list[str] = ascii_words[:]
    for chunk in chinese:
        grams.append(chunk)
        if len(chunk) > 1:
            grams.extend(chunk[index : index + 2] for index in range(len(chunk) - 1))
    return grams


def _idf(documents: list[list[str]]) -> dict[str, float]:
    total = max(1, len(documents))
    counts: Counter[str] = Counter()
    for terms in documents:
        counts.update(set(terms))
    return {term: math.log((total + 1) / (count + 1)) + 1 for term, count in counts.items()}


def _vector(terms: list[str], idf: dict[str, float]) -> dict[str, float]:
    counts = Counter(terms)
    return {term: count * idf.get(term, 1.0) for term, count in counts.items()}


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    numerator = sum(left[term] * right[term] for term in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def _excerpt(memory: MemoryCard, query: str, context_excerpt: str = "") -> str | None:
    source = memory.source_quote or memory.content or memory.source_location or context_excerpt
    if not source:
        return None
    normalized_query = _normalize(query)
    normalized_source = _normalize(source)
    index = normalized_source.find(normalized_query)
    if index < 0 and context_excerpt:
        normalized_context = _normalize(context_excerpt)
        context_index = normalized_context.find(normalized_query)
        if context_index >= 0:
            return context_excerpt[:160]
    if index < 0:
        return source[:80]
    start = max(0, index - 20)
    end = min(len(source), index + len(query) + 40)
    return source[start:end]


def _normalize(text: Any) -> str:
    return re.sub(r"\s+", "", str(text or "").lower())


def _memory_context_excerpt(markdown: str, memory_id: str) -> str:
    if not markdown or memory_id not in markdown:
        return ""
    index = markdown.find(memory_id)
    start = max(0, markdown.rfind("\n### ", 0, index))
    end = markdown.find("\n### ", index + len(memory_id))
    if end < 0:
        end = min(len(markdown), index + 1000)
    return markdown[start:end]
