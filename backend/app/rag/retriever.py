# app/rag/retriever.py

from __future__ import annotations

import os
import re
from typing import Any

from openai import OpenAI, OpenAIError

from app.rag.supabase_client import get_supabase
from app.services.misconduct_service import load_misconduct_reports
from app.services.profile_service import list_workers
from app.services.reference_service import load_reference_notes

def _get_openai_client() -> OpenAI:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Set it in backend/.env or export it in your shell before running retrieval/evals."
        )
    try:
        return OpenAI(api_key=api_key)
    except OpenAIError as exc:
        raise RuntimeError(f"Failed to initialize OpenAI client: {exc}") from exc


def get_embedding(text: str):
    response = _get_openai_client().embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


def _match_worker_documents_rpc(
    worker_id: str,
    embedding: list[float],
    match_count: int,
) -> list[dict]:
    response = get_supabase().rpc(
        "match_worker_documents",
        {
            "query_embedding": embedding,
            "match_worker_id": worker_id,
            "match_count": match_count,
        },
    ).execute()
    results = response.data or []
    return [
        {
            "source": r["source"],
            "content": r["content"],
            "relevance_score": float(r.get("similarity") or 0),
        }
        for r in results
    ]


def retrieve_worker_evidence(worker_id: str, query: str, top_k: int = 5):
    embedding = get_embedding(query)
    return _match_worker_documents_rpc(worker_id, embedding, top_k)


def _query_tokens(q: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9']+", q.lower()) if len(t) > 2}


_TOKEN_ALIASES: dict[str, tuple[str, ...]] = {
    "childcare": ("children", "child", "kids", "infant", "toddler"),
    "babysitting": ("children", "child", "babysit"),
    "nanny": ("children", "child", "care"),
}


def _expand_query_tokens(tokens: set[str]) -> set[str]:
    out = set(tokens)
    for t in tokens:
        if t in _TOKEN_ALIASES:
            out.update(_TOKEN_ALIASES[t])
    return out


def _csv_platform_evidence(query: str, top_k: int) -> list[dict]:
    """Keyword overlap on seeded CSVs when vector paths return nothing."""
    tokens = _expand_query_tokens(_query_tokens(query))
    if not tokens:
        tokens = {"worker", "reference", "report"}

    scored: list[tuple[float, dict]] = []

    ref = load_reference_notes()
    for _, row in ref.iterrows():
        wid = str(row.get("worker_id", "")).strip()
        text = f"{row.get('note', '')} {row.get('source', '')}".lower()
        score = sum(1 for t in tokens if t in text)
        if score > 0:
            scored.append(
                (
                    float(score),
                    {
                        "worker_id": wid,
                        "source": str(row.get("source") or "Reference Note"),
                        "content": str(row.get("note") or ""),
                        "relevance_score": float(score),
                    },
                )
            )

    mis = load_misconduct_reports()
    for _, row in mis.iterrows():
        wid = str(row.get("worker_id", "")).strip()
        text = f"{row.get('report', '')} {row.get('source', '')}".lower()
        score = sum(1 for t in tokens if t in text)
        if score > 0:
            scored.append(
                (
                    float(score),
                    {
                        "worker_id": wid,
                        "source": str(row.get("source") or "Misconduct Report"),
                        "content": str(row.get("report") or ""),
                        "relevance_score": float(score),
                    },
                )
            )

    scored.sort(key=lambda x: x[0], reverse=True)
    out = [item for _, item in scored[:top_k]]
    mx = max((s["relevance_score"] for s in out), default=1.0) or 1.0
    for s in out:
        s["relevance_score"] = round(s["relevance_score"] / mx, 4)
    return out


def _retrieve_platform_per_worker_rag(embedding: list[float], top_k: int) -> list[dict]:
    """One embedding, then match_worker_documents per platform worker; merge by score."""
    workers = list_workers()
    if not workers:
        return []

    n = len(workers)
    per_worker = max(6, min(20, top_k * 3 // max(n, 1) + 4))
    pooled: list[dict] = []
    for row in workers:
        wid = str(row.get("worker_id", "")).strip()
        if not wid:
            continue
        try:
            chunks = _match_worker_documents_rpc(wid, embedding, per_worker)
        except Exception:
            continue
        for c in chunks:
            pooled.append(
                {
                    "worker_id": wid,
                    "source": c["source"],
                    "content": c["content"],
                    "relevance_score": float(c["relevance_score"]),
                }
            )

    if not pooled:
        return []

    pooled.sort(key=lambda x: x["relevance_score"], reverse=True)
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for item in pooled:
        key = (item["worker_id"], item["content"][:120])
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= top_k:
            break
    return out


def retrieve_platform_evidence(query: str, top_k: int = 12) -> list[dict]:
    """
    1) ``match_platform_documents`` if defined and returns rows.
    2) Else per-worker vector RAG (same embedding, one RPC per worker).
    3) Else CSV keyword fallback.
    """
    q = query.strip()
    if not q:
        return []

    try:
        embedding = get_embedding(q)
    except Exception:
        return _csv_platform_evidence(q, top_k)

    results: list = []
    try:
        response = get_supabase().rpc(
            "match_platform_documents",
            {
                "query_embedding": embedding,
                "match_count": top_k,
            },
        ).execute()
        results = response.data or []
    except Exception:
        results = []

    if results:
        return [
            {
                "worker_id": str(r.get("worker_id") or ""),
                "source": str(r.get("source") or "Evidence"),
                "content": str(r.get("content") or ""),
                "relevance_score": float(r.get("similarity") or 0),
            }
            for r in results[:top_k]
        ]

    merged = _retrieve_platform_per_worker_rag(embedding, top_k)
    if merged:
        return merged

    return _csv_platform_evidence(q, top_k)


def structured_fallback_evidence(
    references: list[dict[str, object]],
    reports: list[dict[str, object]],
) -> list[dict[str, Any]]:
    """
    When the vector index returns no rows, surface the same reference/misconduct
    rows the pipeline already loaded from CSV so the UI is not empty.
    """
    chunks: list[dict[str, Any]] = []
    for r in references:
        note = str(r.get("note") or "").strip()
        if not note:
            continue
        chunks.append(
            {
                "source": str(r.get("source") or "Reference"),
                "content": note,
                "relevance_score": 1.0,
                "metadata": {"origin": "structured_reference"},
            }
        )
    for m in reports:
        rep = str(m.get("report") or "").strip()
        if not rep:
            continue
        chunks.append(
            {
                "source": str(m.get("source") or "Misconduct"),
                "content": rep,
                "relevance_score": 1.0,
                "metadata": {"origin": "structured_misconduct"},
            }
        )
    return chunks
