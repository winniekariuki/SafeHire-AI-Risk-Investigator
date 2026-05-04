"""
Platform-wide Q&A: retrieve evidence across workers (Supabase), answer with citations only.

Comparative questions (lowest risk, hiring recommendation) also use the same rule-based
``score_worker`` outputs as investigations so answers are not limited to semantic retrieval hits.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from app.core.telemetry import emit_pipeline_event, pipeline_trace
from app.rag.retriever import retrieve_platform_evidence
from app.risk.risk_scorer import score_worker
from app.services.profile_service import get_worker, list_workers

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

You may receive:
1) ``platform_risk_rankings`` — rule-based composite scores for ALL workers (lower score = lower risk). Treat these numbers as authoritative for comparisons (who has lowest/highest risk).
2) Numbered evidence excerpts from document retrieval.

Rules:
- When the user asks who has the lowest/highest risk, or whom to hire / recommend, you MUST base ordering on ``platform_risk_rankings`` by ``score`` (not on retrieval similarity).
- For other questions, use evidence excerpts; do not invent incidents or employers not in the excerpts.
- Do not give legal or definitive employment conclusions; frame as decision support.
- Never answer "insufficient evidence" for ranking/hiring preference questions if ``platform_risk_rankings`` is non-empty — summarize those scores instead and cite evidence only as supporting context.
- Format the reply as **Markdown** (e.g. `##` headings, `-` bullet lists, **bold** for names and scores).

Return ONLY valid JSON: {"answer": "<markdown string>"} (the model will serialize the string; use real newlines in the markdown content)."""


def _all_worker_risk_rows() -> list[dict[str, Any]]:
    """Rule-based risk for every CSV worker — same engine as per-worker investigation."""
    rows: list[dict[str, Any]] = []
    for w in list_workers():
        wid = str(w.get("worker_id", "")).strip()
        if not wid:
            continue
        try:
            r = score_worker(wid)
        except ValueError:
            continue
        name = str(w.get("name") or wid)
        rows.append(
            {
                "worker_id": wid,
                "name": name,
                "score": int(r.get("score", 0)),
                "risk_level": str(r.get("risk_level", "")),
                "recommendation": str(r.get("recommendation") or ""),
                "reasons": list(r.get("reasons") or [])[:6],
            }
        )
    rows.sort(key=lambda x: x["score"])
    return rows


def _comparison_intent(question: str) -> str | None:
    """Detect cross-worker comparison; rule-based scores answer these reliably."""
    q = question.lower()
    if re.search(
        r"\b(lowest|least|minimum|smallest)\b.*\brisk\b|\brisk\b.*\b(lowest|least|minimum|smallest)\b",
        q,
    ):
        return "lowest"
    if re.search(
        r"\b(highest|greatest|maximum)\b.*\brisk\b|\brisk\b.*\b(highest|greatest|maximum)\b",
        q,
    ):
        return "highest"
    if "hire" in q and any(
        w in q for w in ("recommend", "should", "which", "who", "pick", "choose", "best", "suggest")
    ):
        return "hire"
    if "recommend" in q and "worker" in q:
        return "hire"
    return None


def _comparison_answer(intent: str, rankings: list[dict[str, Any]]) -> str:
    if not rankings:
        return (
            "**No workers could be scored** from the current CSV dataset. "
            "Check that workers, verification, references, and misconduct files are loaded."
        )

    lowest_score = rankings[0]["score"]
    highest_score = rankings[-1]["score"]
    tie_low = [r for r in rankings if r["score"] == lowest_score]
    tie_high = [r for r in rankings if r["score"] == highest_score]

    def fmt_bullet(r: dict[str, Any]) -> str:
        reasons = r.get("reasons") or []
        tail = f" — {', '.join(reasons[:3])}" if reasons else ""
        return (
            f"- **{r['name']}** (`{r['worker_id']}`): score **{r['score']}**, "
            f"{r['risk_level']} risk ({r['recommendation']}){tail}"
        )

    sections: list[str] = []

    if intent == "lowest":
        names = ", ".join(f"**{r['name']}** (`{r['worker_id']}`)" for r in tie_low)
        sections.append("## Lowest risk\n\n")
        sections.append(
            f"By the rule-based composite scores (lower is better), the lowest risk "
            f"{'is ' + names if len(tie_low) == 1 else 'workers are ' + names} "
            f"with score **{lowest_score}**."
        )
    elif intent == "highest":
        names = ", ".join(f"**{r['name']}** (`{r['worker_id']}`)" for r in tie_high)
        sections.append("## Highest risk\n\n")
        sections.append(
            f"By the rule-based composite scores, the highest risk "
            f"{'is ' + names if len(tie_high) == 1 else 'workers are ' + names} "
            f"with score **{highest_score}**."
        )
    else:
        top = tie_low[0] if tie_low else rankings[0]
        sections.append("## Hiring preference (rule-based scores only)\n\n")
        sections.append(
            f"Using **only** these rule-based scores (not interviews or local policy), "
            f"**{top['name']}** (`{top['worker_id']}`) has the lowest composite risk "
            f"(score **{top['score']}**, **{top['risk_level']}** band).\n\n"
            "This is **not** a hire/no-hire decision—verify references, contracts, and compliance yourself."
        )

    if len(rankings) > 1:
        sections.append("\n### All workers (low → high)\n")
        bullets = "\n".join(fmt_bullet(r) for r in rankings[:8])
        sections.append(bullets)
        if len(rankings) > 8:
            sections.append("\n- …")

    sections.append(
        "\n\n---\n\n"
        "*This is decision support only—not a final suitability determination.*"
    )
    return "".join(sections)


def _llm_answer(
    question: str,
    evidence: list[dict[str, str]],
    platform_risk_rankings: list[dict[str, Any]],
) -> str | None:
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        client = OpenAI()
        model = os.getenv("OPENAI_ASK_MODEL", "gpt-4o-mini")
        user_msg = (
            f"Question: {question}\n\n"
            f"platform_risk_rankings (authoritative for cross-worker risk comparison):\n"
            f"{json.dumps(platform_risk_rankings, indent=2)}\n\n"
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
    concern_words = (
        "complaint",
        "absent",
        "late",
        "shouting",
        "safety",
        "aggressive",
        "misconduct",
    )

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
            "> No platform-wide evidence matched this question in the current index.\n\n"
            "Ingest worker documents into Supabase or try rephrasing."
        )

    parts: list[str] = []
    if "who" in qlow or "which" in qlow:
        top = [r for r in ranked if r[0] > 0][:3]
        if top:
            bullets: list[str] = []
            for _score, wid, _ in top:
                name = _worker_display_name(wid)
                bits = [e["content"] for e in by_worker[wid][:2]]
                quote = " ".join(f"“{_truncate(b, 180)}”" for b in bits)
                bullets.append(f"- **{name}** (`{wid}`): {quote}")
            parts.append("### Textual matches\n\n" + "\n".join(bullets))
        else:
            wid = ranked[0][1]
            name = _worker_display_name(wid)
            parts.append(
                f"Closest textual matches point to **{name}** (`{wid}`); review citations below."
            )

    if not parts:
        parts.append("Review the cited excerpts below for details relevant to your question.")

    out = "\n\n".join(parts)
    return (
        f"{out}\n\n---\n\n"
        "*This is decision support only—not a final suitability determination.*"
    )


def answer_platform_question(question: str) -> dict[str, Any]:
    """Retrieve evidence across workers; return answer + snippets with ``worker_id``."""
    q = question.strip()
    if not q:
        return {"answer": "Please enter a question.", "evidence": []}

    with pipeline_trace("safehire.platform_answer", {}) as root:
        intent = _comparison_intent(q)
        rankings = _all_worker_risk_rows()

        raw = retrieve_platform_evidence(q, top_k=14)
        evidence = _normalize_evidence(raw)

        if intent and rankings:
            answer = _comparison_answer(intent, rankings)
            used_llm = False
        else:
            llm = _llm_answer(q, evidence, rankings)
            used_llm = llm is not None
            answer = llm if used_llm else _deterministic_answer(q, evidence)

        emit_pipeline_event(
            root,
            "platform_answered",
            {
                "evidence_count": len(evidence),
                "answer_length": len(answer),
                "used_llm": used_llm,
                "comparison_intent": intent or "",
            },
        )

        return {"answer": answer, "evidence": evidence}
