"""
Ingest demo CSV rows into Supabase ``worker_documents`` with embeddings.

Requires ``OPENAI_API_KEY``, ``SUPABASE_URL``, and a key with insert (and delete if
using replace) permission on ``worker_documents``.

Run from ``backend/``:

    python -m app.rag.ingest

Or with replacement (delete existing rows per worker, then insert):

    INGEST_REPLACE=1 python -m app.rag.ingest
"""

from __future__ import annotations

import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from app.rag.retriever import get_embedding
from app.rag.supabase_client import get_supabase
from app.services.misconduct_service import get_misconduct_reports
from app.services.profile_service import list_workers
from app.services.reference_service import get_reference_notes


def collect_chunks_for_worker(worker_id: str, profile: dict[str, object]) -> list[dict[str, str]]:
    """Text chunks to embed: profile summary, reference notes, misconduct reports."""
    wid = worker_id.strip()
    chunks: list[dict[str, str]] = []

    name = str(profile.get("name") or "").strip()
    county = str(profile.get("county") or "").strip()
    years = profile.get("years_experience", "")
    years_str = "" if years is None or (isinstance(years, float) and str(years) == "nan") else str(years).strip()
    if name or county or years_str:
        parts = []
        if name:
            parts.append(name)
        if county:
            parts.append(f"Region / county: {county}")
        if years_str:
            parts.append(f"Years of experience: {years_str}")
        body = ". ".join(parts)
        if body:
            chunks.append(
                {
                    "worker_id": wid,
                    "source": "Worker profile",
                    "content": body,
                }
            )

    for r in get_reference_notes(wid):
        note = str(r.get("note") or "").strip()
        if not note:
            continue
        chunks.append(
            {
                "worker_id": wid,
                "source": str(r.get("source") or "Reference Note"),
                "content": note,
            }
        )

    for m in get_misconduct_reports(wid):
        rep = str(m.get("report") or "").strip()
        if not rep:
            continue
        chunks.append(
            {
                "worker_id": wid,
                "source": str(m.get("source") or "Misconduct Report"),
                "content": rep,
            }
        )

    return chunks


def _delete_worker_rows(worker_id: str) -> None:
    """Best-effort delete before re-ingest; may fail under strict RLS with anon key."""
    get_supabase().table("worker_documents").delete().eq("worker_id", worker_id).execute()


def ingest_all(*, replace_per_worker: bool | None = None) -> int:
    """
    Embed and insert every chunk for every worker in ``workers.csv``.

    Returns the number of rows successfully inserted (best-effort).
    """
    replace = replace_per_worker
    if replace is None:
        replace = os.getenv("INGEST_REPLACE", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )

    workers = list_workers()
    inserted = 0
    delay_s = float(os.getenv("INGEST_DELAY_SEC", "0.05"))

    for row in workers:
        wid = str(row.get("worker_id") or "").strip()
        if not wid:
            continue

        chunks = collect_chunks_for_worker(wid, row)
        if not chunks:
            print(f"  {wid}: no text chunks (skipping)")
            continue

        if replace:
            try:
                _delete_worker_rows(wid)
            except Exception as exc:
                print(
                    f"  {wid}: could not delete old rows ({exc}); "
                    "continuing — you may get duplicates if RLS blocks DELETE.",
                    file=sys.stderr,
                )

        worker_inserted = 0
        for doc in chunks:
            try:
                embedding = get_embedding(doc["content"])
                get_supabase().table("worker_documents").insert(
                    {
                        "worker_id": doc["worker_id"],
                        "source": doc["source"],
                        "content": doc["content"],
                        "embedding": embedding,
                    }
                ).execute()
                inserted += 1
                worker_inserted += 1
                if delay_s > 0:
                    time.sleep(delay_s)
            except Exception as exc:
                print(
                    f"  ERROR inserting {doc['worker_id']} / {doc['source']}: {exc}",
                    file=sys.stderr,
                )

        print(f"  {wid}: {worker_inserted}/{len(chunks)} chunk(s) inserted")

    return inserted


def main() -> None:
    print("Ingesting embeddings for all workers into Supabase worker_documents…")
    n = ingest_all()
    print(f"Done. Inserted {n} row(s) total.")


if __name__ == "__main__":
    main()
