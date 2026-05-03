"""
Platform-wide Q&A: retrieve evidence across all workers, answer with citations only.
"""

from __future__ import annotations

import json
import os
from typing import Any

from app.core.telemetry import emit_pipeline_event, pipeline_trace
from app.rag.retriever import retrieve_platform_evidence
from app.services.profile_service import get_worker

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[misc, assignment]

_MAX_SNIPPET = 520


def _truncate(text: str, max_len: int = _MAX_SNIPPET) -> str:
    t = text.strip().replace("\n", " ")
    if len(t) <= max_len:
        return t
    return t[: max_len - 3].rstrip() + "..."


def _normalize_evidence(raw: list[dict]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in raw:
        wid = str(row.get("worker_id") or "").strip()
        src = str(row.get("source") or "Evidence").strip()
        body = _truncate(str(row.get("content") or ""))
        if not body:
            continue
        key = f"{wid}|{src}|{body}"
        if key in seen:
            continue
        seen.add(key)
        out.append({"worker_id": wid, "source": src, "content": body})
    return out[:16]


def _format_evidence_for_prompt(evidence: list[dict[str, str]]) -> str:
    lines = []
    for i, e in enumerate(evidence, 1):
        wid = e.get("worker_id") or "unknown"
        lines.append(f'{i}. [worker {wid} · {e["source"]}] {e["content"]}')
    return "\n".join(lines)


_SYSTEM = """You are a SafeHire hiring-risk assistant for a domestic-worker platform.

Answer using ONLY the numbered evidence excerpts (each tagged with a worker id like W001).
Rules:
- Do not invent incidents, employers, or behaviors not in the excerpts.
- Do not give legal or definitive employment conclusions.
- For questions like "who is good with children?", name only workers whose excerpts support the claim;
  mention conflicting excerpts if relevant.
- If excerpts are insufficient, say what is missing.

Return ONLY valid JSON: {"answer": "<your reply>"}"""


def _llm_answer(question: str, evidence: list[dict[str, str]]) -> str | None:
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        client = OpenAI()
        model = os.getenv("OPENAI_ASK_MODEL", "gpt-4o-mini")
        user_msg = (
            f"Question: {question}\n\n"
            f"Evidence excerpts:\n{_format_evidence_for_prompt(evidence)}"
        )
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        ans = str(data.get("answer", "")).strip()
        return ans or None
    except Exception:
        return None


def _worker_display_name(worker_id: str) -> str:
    try:
        w = get_worker(worker_id)
        return str(w.get("name") or worker_id)
    except ValueError:
        return worker_id


def _deterministic_answer(question: str, evidence: list[dict[str, str]]) -> str:
    qlow = question.lower()
    by_worker: dict[str, list[dict[str, str]]] = {}
    for e in evidence:
        wid = e.get("worker_id") or ""
        by_worker.setdefault(wid, []).append(e)

    # Prefer workers with positive cues when question asks about "good" traits
    positive_words = (
        "good",
        "great",
        "excellent",
        "reliable",
        "punctual",
        "children",
        "care",
        "trust",
    )
    concern_words = ("complaint", "absent", "late", "shouting", "safety", "aggressive", "misconduct")

    ranked: list[tuple[int, str, str]] = []
    for wid, rows in by_worker.items():
        if not wid:
            continue
        blob = " ".join(r["content"].lower() for r in rows)
        pos = sum(1 for w in positive_words if w in qlow and w in blob)
        neg = sum(1 for w in concern_words if w in blob)
        ranked.append((pos - neg, wid, blob))

    ranked.sort(key=lambda x: x[0], reverse=True)

    if not ranked:
        return (
            "No platform-wide evidence matched this question in the current index. "
            "Try rephrasing or run per-worker assessments once documents are ingested."
        )

    parts: list[str] = []
    if "who" in qlow or "which" in qlow:
        top = [r for r in ranked if r[0] > 0][:3]
        if top:
            for score, wid, _ in top:
                name = _worker_display_name(wid)
                bits = [e["content"] for e in by_worker[wid][:2]]
                parts.append(
                    f"**{name}** ({wid}): " + " ".join(f"“{_truncate(b, 180)}”" for b in bits)
                )
        else:
            wid = ranked[0][1]
            name = _worker_display_name(wid)
            parts.append(
                f"Closest textual matches point to **{name}** ({wid}); review citations below — "
                "evidence may be mixed."
            )

    if not parts:
        parts.append("Review the cited excerpts below; the question did not match a simple ranking rule.")

    parts.append("This is decision support only—not a final suitability determination.")
    return " ".join(parts)


def answer_platform_question(question: str) -> dict[str, Any]:
    """
    Retrieve evidence across workers, return answer + snippets (with ``worker_id``).
    """
    q = question.strip()
    if not q:
        return {"answer": "Please enter a question.", "evidence": []}

    with pipeline_trace("safehire.platform_answer", {}) as root:
        raw = retrieve_platform_evidence(q, top_k=14)
        evidence = _normalize_evidence(raw)
        llm = _llm_answer(q, evidence)
        used_llm = llm is not None
        answer = llm if used_llm else _deterministic_answer(q, evidence)

        emit_pipeline_event(
            root,
            "platform_answered",
            {
                "evidence_count": len(evidence),
                "answer_length": len(answer),
                "used_llm": used_llm,
            },
        )

        return {"answer": answer, "evidence": evidence}
