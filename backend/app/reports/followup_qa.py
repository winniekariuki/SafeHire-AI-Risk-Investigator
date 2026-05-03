"""
Follow-up Q&A over worker-specific evidence + rule-based risk snapshot.

Uses only retrieved snippets and CSV fallbacks — no invented incidents.
"""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

from app.core.telemetry import emit_pipeline_event, pipeline_trace
from app.rag.retriever import retrieve_worker_evidence
from app.risk.risk_scorer import score_worker
from app.services.misconduct_service import get_reports
from app.services.profile_service import get_worker
from app.services.reference_service import get_references

load_dotenv()

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


def _gather_evidence(worker_id: str, query: str) -> list[dict[str, str | None]]:
    """Worker-specific chunks from Chroma, plus CSV rows if retrieval is thin."""
    wid = worker_id.strip()
    q = query.strip() or "hiring risk references misconduct verification attendance"
    chunks = retrieve_worker_evidence(wid, q, top_k=8)

    out: list[dict[str, str | None]] = []
    seen: set[str] = set()

    def add(source: str, content: str) -> None:
        c = _truncate(content)
        key = f"{wid}|{source}|{c}"
        if not c or key in seen:
            return
        seen.add(key)
        out.append({"worker_id": wid, "source": source, "content": c})

    for row in chunks:
        src = str(row.get("source") or "Evidence").strip()
        add(src, str(row.get("content") or ""))

    if len(out) < 3:
        for r in get_references(wid):
            add(str(r.get("source") or "Reference Note"), str(r.get("note") or ""))
        for m in get_reports(wid):
            add(str(m.get("source") or "Misconduct Report"), str(m.get("report") or ""))

    return out[:12]


def _format_evidence_for_prompt(evidence: list[dict[str, str | None]]) -> str:
    lines = []
    for i, e in enumerate(evidence, 1):
        w = e.get("worker_id") or ""
        tag = f"worker {w} · {e['source']}" if w else str(e["source"])
        lines.append(f"{i}. [{tag}] {e['content']}")
    return "\n".join(lines)


_SYSTEM = """You are a SafeHire hiring-risk assistant.

Answer the user's question using ONLY:
- the numbered evidence excerpts, and
- the rule-based risk summary JSON (facts already computed — do not change scores).

Rules:
- Do not invent incidents, employers, dates, or behaviors not supported by the excerpts.
- Do not give legal, criminal, or definitive employment conclusions.
- Frame the reply as decision support: concise, plain language.
- If excerpts are insufficient to answer, say what is missing.
Return ONLY valid JSON: {"answer": "<your reply>"}"""


def _llm_answer(
    question: str,
    evidence: list[dict[str, str | None]],
    risk: dict[str, Any],
) -> str | None:
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        client = OpenAI()
        model = os.getenv("OPENAI_ASK_MODEL", "gpt-4o-mini")
        user_msg = (
            f"Question: {question}\n\n"
            f"Rule-based risk summary (authoritative numbers):\n{json.dumps(risk, indent=2)}\n\n"
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


def _deterministic_answer(
    question: str,
    evidence: list[dict[str, str | None]],
    risk: dict[str, Any],
) -> str:
    qlow = question.lower()
    lvl = str(risk.get("risk_level", "unknown"))
    score = risk.get("score")
    reasons = risk.get("reasons") or []
    rec = str(risk.get("recommendation") or "")

    parts: list[str] = []

    if any(k in qlow for k in ("why", "risk", "medium", "high", "low", "score")):
        parts.append(
            f"The rule-based assessment rates this worker as **{lvl}** risk"
            f"{f' (composite score {score})' if score is not None else ''}. "
            f"Top documented drivers include: {', '.join(reasons[:6]) or 'see evidence excerpts'}."
        )
        if rec:
            parts.append(f"Recommended posture from rules: {rec}.")

    # Surface contrasting snippets (positive vs concern) from evidence only
    positive_hint = next(
        (
            e["content"]
            for e in evidence
            if any(w in e["content"].lower() for w in ("good", "reliable", "chores", "punctual"))
            and not any(w in e["content"].lower() for w in ("late", "absent", "complaint", "shouting"))
        ),
        "",
    )
    concern_hint = next(
        (
            e["content"]
            for e in evidence
            if any(w in e["content"].lower() for w in ("late", "absent", "misconduct", "complaint", "safety"))
        ),
        "",
    )

    if positive_hint:
        parts.append(f"Positive notes in the supplied evidence include: “{_truncate(positive_hint, 220)}”.")
    if concern_hint:
        parts.append(f"Concern-related notes include: “{_truncate(concern_hint, 220)}”.")

    if not parts:
        parts.append(
            "This answer is limited to the supplied excerpts and risk summary. "
            "Review the evidence list for specifics relevant to your question."
        )

    parts.append(
        "This is decision support only—not a final suitability or legal determination."
    )
    return " ".join(parts)


def answer_followup_question(worker_id: str, question: str) -> dict[str, Any]:
    """
    Retrieve evidence, attach rule-based risk snapshot, return answer + cited snippets.

    Raises:
        ValueError: Unknown worker.
    """
    wid = worker_id.strip()
    get_worker(wid)

    with pipeline_trace("safehire.followup_answer", {"worker_id": wid}) as root:
        evidence = _gather_evidence(wid, question)
        risk = score_worker(wid)

        llm_answer = _llm_answer(question, evidence, risk)
        used_llm = llm_answer is not None
        answer = llm_answer if used_llm else _deterministic_answer(
            question,
            evidence,
            risk,
        )

        emit_pipeline_event(
            root,
            "followup_answered",
            {
                "worker_id": wid,
                "evidence_count": len(evidence),
                "answer_length": len(answer),
                "used_llm": used_llm,
            },
        )

        return {
            "answer": answer,
            "evidence": evidence,
        }
