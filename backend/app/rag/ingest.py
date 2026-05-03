"""
Ingest CSV rows and policy documents into Chroma: chunk → embed → store.

Logical rows match::

    {
      "worker_id": "W002",
      "source": "Reference Note",
      "content": "...",
      "metadata": {"source_file": "reference_notes.csv", "risk_area": "attendance"},
    }

Chroma stores flat metadatas; :func:`~app.rag.retriever.retrieve_worker_evidence`
rebuilds the nested ``metadata`` dict. Policy chunks use ``worker_id="__global__"``
and are omitted from worker-only retrieval.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from app.rag.vector_store import get_client, get_collection
from app.services._records import DATA_DIR, read_csv

POLICY_DIR = DATA_DIR / "policy_docs"

CHUNK_SIZE = 400
CHUNK_OVERLAP = 80


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    step = max(1, chunk_size - overlap)
    chunks: list[str] = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + chunk_size])
        i += step
    return chunks


def infer_risk_area(source_label: str, content: str) -> str:
    sl = source_label.lower()
    s = content.lower()
    if sl == "policy":
        return "policy_compliance"
    if any(k in s for k in ("child", "children", "safeguarding", "shouting", "aggressive")):
        return "child_safety"
    if any(k in s for k in ("late", "absent", "disappeared", "punctual", "attendance", "absence")):
        return "attendance"
    if "verification" in sl or "verified" in s or "phone" in s and "id" in s:
        return "verification"
    if "misconduct" in sl:
        return "conduct"
    return "general"


def _logical_doc(
    *,
    worker_id: str,
    source: str,
    content: str,
    source_file: str,
    risk_area: str | None = None,
) -> dict[str, Any]:
    ra = risk_area or infer_risk_area(source, content)
    return {
        "worker_id": worker_id,
        "source": source,
        "content": content,
        "metadata": {"source_file": source_file, "risk_area": ra},
    }


def documents_from_reference_notes() -> list[dict[str, Any]]:
    df = read_csv("reference_notes")
    out: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        wid = str(row["worker_id"])
        src = str(row["source"])
        note = str(row["note"])
        out.append(
            _logical_doc(
                worker_id=wid,
                source=src,
                content=note,
                source_file="reference_notes.csv",
            )
        )
    return out


def documents_from_misconduct_reports() -> list[dict[str, Any]]:
    df = read_csv("misconduct_reports")
    out: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        wid = str(row["worker_id"])
        src = str(row["source"])
        report = str(row["report"])
        sev = str(row.get("severity", ""))
        ver = row.get("verified", "")
        content = f"{report}\nSeverity: {sev}. Verified: {ver}."
        out.append(
            _logical_doc(
                worker_id=wid,
                source=src,
                content=content,
                source_file="misconduct_reports.csv",
            )
        )
    return out


def documents_from_verification_notes() -> list[dict[str, Any]]:
    df = read_csv("verification_notes")
    out: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        wid = str(row["worker_id"])
        id_v = row.get("id_verified", "")
        phone_v = row.get("phone_verified", "")
        content = (
            f"Verification status for worker {wid}: "
            f"government ID verified={id_v}; phone verified={phone_v}."
        )
        out.append(
            _logical_doc(
                worker_id=wid,
                source="Verification Note",
                content=content,
                source_file="verification_notes.csv",
                risk_area="verification",
            )
        )
    return out


def documents_from_policy_docs() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not POLICY_DIR.is_dir():
        return out
    for path in sorted(POLICY_DIR.glob("**/*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(DATA_DIR).as_posix()
        out.append(
            _logical_doc(
                worker_id="__global__",
                source="Policy",
                content=text,
                source_file=rel,
                risk_area="policy_compliance",
            )
        )
    return out


def _stable_chunk_id(worker_id: str, source: str, chunk_index: int, text: str) -> str:
    h = hashlib.sha256(f"{worker_id}|{source}|{chunk_index}|{text}".encode()).hexdigest()[:16]
    return f"{worker_id}_{chunk_index}_{h}"


def ingest_all(*, reset: bool = True, persist_path: Path | None = None) -> int:
    """
    Load all sources, chunk, embed, and upsert into Chroma.

    Returns the number of chunks written.
    """
    client = get_client(persist_path) if persist_path else get_client()
    collection = get_collection(client=client, reset=reset)

    logical_docs: list[dict[str, Any]] = []
    logical_docs.extend(documents_from_reference_notes())
    logical_docs.extend(documents_from_misconduct_reports())
    logical_docs.extend(documents_from_verification_notes())
    logical_docs.extend(documents_from_policy_docs())

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []

    chunk_index_global = 0
    for doc in logical_docs:
        wid = doc["worker_id"]
        src = doc["source"]
        meta = doc["metadata"]
        source_file = meta["source_file"]
        risk_area = meta["risk_area"]

        for piece in chunk_text(doc["content"]):
            cid = _stable_chunk_id(wid, src, chunk_index_global, piece)
            chunk_index_global += 1
            ids.append(cid)
            documents.append(piece)
            metadatas.append(
                {
                    "worker_id": wid,
                    "source": src,
                    "source_file": source_file,
                    "risk_area": risk_area,
                }
            )

    if ids:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    return len(ids)


if __name__ == "__main__":
    n = ingest_all(reset=True)
    print(f"Ingested {n} chunks into Chroma.")
