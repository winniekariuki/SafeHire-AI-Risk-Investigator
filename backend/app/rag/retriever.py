"""Semantic retrieval over worker-specific evidence chunks."""

from __future__ import annotations

from typing import Any

from app.rag.vector_store import get_collection


def retrieve_worker_evidence(
    worker_id: str,
    query: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Return ranked worker-specific evidence chunks (excludes ``__global__`` policy rows).

    Output shape per item::

        {
            "worker_id": "...",
            "source": "...",
            "content": "<chunk text>",
            "metadata": {"source_file": "...", "risk_area": "..."},
        }
    """
    collection = get_collection(reset=False)
    q = query.strip()
    if not q:
        return []

    res = collection.query(
        query_texts=[q],
        n_results=top_k,
        where={"worker_id": worker_id},
        include=["documents", "metadatas", "distances"],
    )

    docs = res.get("documents") or []
    metas = res.get("metadatas") or []
    if not docs or not docs[0]:
        return []

    out: list[dict[str, Any]] = []
    for text, meta in zip(docs[0], metas[0], strict=False):
        if meta is None:
            meta = {}
        out.append(
            {
                "worker_id": meta.get("worker_id", worker_id),
                "source": meta.get("source", ""),
                "content": text or "",
                "metadata": {
                    "source_file": meta.get("source_file", ""),
                    "risk_area": meta.get("risk_area", ""),
                },
            }
        )
    return out
