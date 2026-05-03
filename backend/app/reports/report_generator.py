"""
Generate structured markdown reports from pipeline outputs only.

No LLM here — narratives are assembled deterministically from supplied rows,
signals, sufficiency, and risk summaries. Framed strictly as decision support.
"""

from __future__ import annotations

from typing import Any


def _truthy(value: object) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _truncate(text: str, max_len: int = 280) -> str:
    t = text.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 3].rstrip() + "..."


def _missing_information_lines(
    sufficiency: dict[str, Any],
    references: list[dict[str, Any]],
) -> list[str]:
    lines = [str(x).strip() for x in (sufficiency.get("missing_information") or []) if str(x).strip()]
    if len(references) == 1:
        if not any("only one reference" in x.lower() for x in lines):
            lines.append("Only one reference completed")
        if not any("second reference" in x.lower() for x in lines):
            lines.append("Second reference check recommended")
    return lines


def _evidence_used_lines(
    references: list[dict[str, Any]],
    reports: list[dict[str, Any]],
    retrieved: list[dict[str, Any]],
) -> list[str]:
    out: list[str] = []
    for r in references:
        note = str(r.get("note") or "").strip()
        src = str(r.get("source") or "Reference Note").strip()
        if note:
            out.append(f"- **{src}:** {note}")
    for m in reports:
        rep = str(m.get("report") or "").strip()
        src = str(m.get("source") or "Misconduct Report").strip()
        if rep:
            out.append(f"- **{src}:** {rep}")
    for chunk in retrieved:
        content = str(chunk.get("content") or "").strip()
        if not content:
            continue
        src = str(chunk.get("source") or "Retrieved evidence").strip()
        out.append(f"- **{src}** (retrieval): {_truncate(content)}")
    return out


def _next_steps(
    *,
    verification: dict[str, Any],
    references: list[dict[str, Any]],
    signals: dict[str, Any],
    sufficiency: dict[str, Any],
) -> list[str]:
    steps: list[str] = []
    missing_blob = " ".join(sufficiency.get("missing_information") or []).lower()
    concerns_blob = " ".join(signals.get("concerns") or []).lower()

    if len(references) < 2 or "reference" in missing_blob:
        steps.append("Conduct one more reference check if policy permits.")

    if any(k in concerns_blob for k in ("absent", "late", "attendance", "absenteeism")):
        steps.append("Confirm attendance history with the relevant supervisor.")

    if "id verification" in missing_blob or not _truthy(verification.get("id_verified")):
        steps.append("Review verification status (ID and phone) before hiring.")

    if "manual_review" in missing_blob or sufficiency.get("manual_review_required"):
        steps.append("Route this file to manual review using your internal checklist.")

    if not steps:
        steps.append("Complete any remaining verification steps per your standard workflow.")

    steps.append(
        "Use this document as decision support only—it is not a final judgment on suitability."
    )
    return steps


def generate(
    *,
    profile: dict[str, Any],
    verification: dict[str, Any],
    evidence: list[dict[str, Any]],
    signals: dict[str, Any],
    risk: dict[str, Any],
    sufficiency: dict[str, Any],
    references: list[dict[str, Any]] | None = None,
    reports: list[dict[str, Any]] | None = None,
) -> str:
    """
    Build markdown using **only** supplied structured evidence.

    Does not assert legal, criminal, or employment outcomes—decision support framing only.
    """
    references = references or []
    reports = reports or []

    worker_label = str(profile.get("name") or profile.get("worker_id") or "Worker")
    risk_level = str(risk.get("risk_level") or "Unknown")
    recommendation = str(risk.get("recommendation") or "See internal policy.")
    confidence = str(risk.get("confidence") or "Unknown")

    strengths = [str(s).strip() for s in (signals.get("strengths") or []) if str(s).strip()]
    concerns = [str(s).strip() for s in (signals.get("concerns") or []) if str(s).strip()]
    missing_lines = _missing_information_lines(sufficiency, references)
    evidence_lines = _evidence_used_lines(references, reports, evidence)
    next_steps = _next_steps(
        verification=verification,
        references=references,
        signals=signals,
        sufficiency=sufficiency,
    )

    parts: list[str] = [
        "## SafeHire Risk Report",
        "",
        f"*Subject:* {worker_label} (`{profile.get('worker_id', '')}`)",
        "",
        "### Overall Assessment",
        f"Risk Level: {risk_level}  ",
        f"Recommendation: {recommendation}  ",
        f"Confidence: {confidence}  ",
        "",
        "### Key Strengths",
    ]

    if strengths:
        parts.extend(f"- {s}" for s in strengths)
    else:
        parts.append("- *(No strengths recorded in supplied evidence.)*")

    parts.extend(["", "### Key Concerns"])
    if concerns:
        parts.extend(f"- {c}" for c in concerns)
    else:
        parts.append("- *(No concerns recorded in supplied evidence.)*")

    parts.extend(["", "### Missing Information"])
    if missing_lines:
        parts.extend(f"- {m}" for m in missing_lines)
    else:
        parts.append("- *(No sufficiency gaps flagged with current inputs.)*")

    parts.extend(["", "### Evidence Used"])
    if evidence_lines:
        parts.extend(evidence_lines)
    else:
        parts.append("- *(No narrative evidence rows supplied for this worker.)*")

    parts.extend(["", "### Next Steps"])
    parts.extend(f"- {step}" for step in next_steps)

    parts.extend(
        [
            "",
            "---",
            "",
            "**Disclaimer:** This report summarizes supplied records and rule-based signals for "
            "**decision support only**. It does **not** provide legal, criminal, or employment "
            "conclusions, and it must not be treated as a final hiring determination. "
            "Escalate to qualified reviewers where policy requires.",
        ]
    )

    return "\n".join(parts)
