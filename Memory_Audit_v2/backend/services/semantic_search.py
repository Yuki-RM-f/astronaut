from __future__ import annotations

import re
from collections import Counter
from math import sqrt


def _tokenize(text: str) -> list[str]:
    """Extract Chinese bigrams + words for TF-IDF indexing."""
    cleaned = re.sub(r"[^一-鿿\w]", " ", text.lower())
    chars = re.findall(r"[一-鿿]", cleaned)
    bigrams = ["".join(chars[i : i + 2]) for i in range(len(chars) - 1)]
    words = re.findall(r"[a-z0-9]+", cleaned)
    return [t for t in bigrams + words if len(t) >= 2]


def _compute_tfidf(
    documents: list[dict],
) -> tuple[dict[str, list[float]], dict[str, float]]:
    """Compute TF-IDF vectors for a list of {id, text} documents."""
    doc_texts = [d["text"] for d in documents]
    doc_tokens = [_tokenize(t) for t in doc_texts]
    N = len(doc_texts)

    df: Counter = Counter()
    for tokens in doc_tokens:
        df.update(set(tokens))

    idf = {term: sqrt(N / (df[term] + 1)) for term in df}

    vectors: dict[str, list[float]] = {}
    for doc, tokens in zip(documents, doc_tokens):
        tf = Counter(tokens)
        total = len(tokens) or 1
        vectors[doc["id"]] = [tf.get(term, 0) / total * idf.get(term, 0) for term in idf]

    return vectors, {term: idf[term] for term in sorted(idf)}


def _cosine_similarity(query_vec: list[float], doc_vec: list[float]) -> float:
    dot = sum(a * b for a, b in zip(query_vec, doc_vec))
    norm_a = sqrt(sum(a * a for a in query_vec))
    norm_b = sqrt(sum(b * b for b in doc_vec))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_search(
    query: str,
    memories: list[dict],
    top_k: int = 5,
    min_score: float = 0.05,
) -> list[dict]:
    """
    Search memories by semantic relevance to query.

    Args:
        query: user's search phrase
        memories: list of {id, content, title, source_quote, confidence_score, ...}
        top_k: max results to return
        min_score: minimum cosine similarity threshold

    Returns:
        list of memory dicts with added 'relevance_score' field, sorted descending
    """
    if not memories or not query.strip():
        return []

    docs = [
        {
            "id": m["id"],
            "text": f"{m.get('title', '')} {m.get('content', '')} {m.get('source_quote', '')}",
        }
        for m in memories
    ]

    vectors, terms = _compute_tfidf(docs)
    terms_list = list(terms.keys())

    # Build query vector
    query_tokens = _tokenize(query)
    query_tf = Counter(query_tokens)
    total = len(query_tokens) or 1
    query_vec = [
        query_tf.get(t, 0) / total * terms.get(t, 1.0) for t in terms_list
    ]

    scored: list[dict] = []
    for mem in memories:
        doc_vec = vectors.get(mem["id"], [0.0] * len(terms_list))
        score = _cosine_similarity(query_vec, doc_vec)
        if score >= min_score:
            result = dict(mem)
            result["relevance_score"] = round(score, 4)
            scored.append(result)

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored[:top_k]
