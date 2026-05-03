# app/rag/retriever.py

import os
import re

from openai import OpenAI

from app.rag.supabase_client import get_supabase
from app.services.misconduct_service import load_misconduct_reports
from app.services.reference_service import load_reference_notes

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_embedding(text: str):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


def retrieve_worker_evidence(worker_id: str, query: str, top_k: int = 5):
    embedding = get_embedding(query)

    response = get_supabase().rpc(
        "match_worker_documents",
        {
            "query_embedding": embedding,
            "match_worker_id": worker_id,
            "match_count": top_k,
        },
    ).execute()

    results = response.data or []

    return [
        {
            "source": r["source"],
            "content": r["content"],
            "relevance_score": r["similarity"],
        }
        for r in results
    ]


def _query_tokens(q: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9']+", q.lower()) if len(t) > 2}


def _csv_platform_evidence(query: str, top_k: int) -> list[dict]:
    """Keyword overlap over seeded CSVs when Supabase RPC is unavailable."""
    tokens = _query_tokens(query)
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


def retrieve_platform_evidence(query: str, top_k: int = 12) -> list[dict]:
    """
    Evidence across all workers: Supabase ``match_platform_documents`` if present,
    else CSV keyword retrieval (no embeddings).
    """
    q = query.strip()
    if not q:
        return []

    try:
        embedding = get_embedding(q)
    except Exception:
        return _csv_platform_evidence(q, top_k)

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

    if not results:
        return _csv_platform_evidence(q, top_k)

    return [
        {
            "worker_id": str(r.get("worker_id") or ""),
            "source": str(r.get("source") or "Evidence"),
            "content": str(r.get("content") or ""),
            "relevance_score": float(r.get("similarity") or 0),
        }
        for r in results
    ]