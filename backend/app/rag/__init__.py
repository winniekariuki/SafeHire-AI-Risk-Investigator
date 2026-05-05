from __future__ import annotations

from typing import Any

__all__ = [
    "ingest_all",
    "retrieve_worker_evidence",
]


def ingest_all(*args: Any, **kwargs: Any) -> int:
    from app.rag.ingest import ingest_all as _ingest_all

    return _ingest_all(*args, **kwargs)


def retrieve_worker_evidence(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    from app.rag.retriever import retrieve_worker_evidence as _retrieve_worker_evidence

    return _retrieve_worker_evidence(*args, **kwargs)
