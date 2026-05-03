"""
Prompt-based risk signal extraction over structured evidence.

When ``OPENAI_API_KEY`` is set, calls the chat API with JSON-only output.
Otherwise (or on failure), falls back to deterministic keyword rules — still
using only supplied text, no invented facts.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[misc, assignment]


class SignalExtractionResult(BaseModel):
    positive_signals: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high"] = "low"
    evidence_strength: Literal["low", "medium", "high"] = "low"
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)


ALLOWED_POSITIVE = frozenset(
    {
        "chores_positive",
        "reliability_positive",
        "children_positive",
        "punctuality_positive",
        "communication_positive",
        "reference_positive",
    }
)

ALLOWED_RISK = frozenset(
    {
        "punctuality_issue",
        "absenteeism_issue",
        "child_safety_concern",
        "misconduct_report",
        "verification_gap",
        "reference_concern",
        "unexplained_absence",
    }
)


_SYSTEM_PROMPT = """You are a risk signal extractor for domestic-worker vetting.

Return ONLY a single JSON object (no markdown, no prose) with exactly these keys:
- positive_signals: array of strings
- risk_signals: array of strings
- severity: one of "low", "medium", "high"
- evidence_strength: one of "low", "medium", "high"
- strengths: array of short English phrases summarizing positive facts found IN the evidence
- concerns: array of short English phrases summarizing risk-relevant facts found IN the evidence

Use ONLY labels from these vocabularies when possible:
positive_signals allowed: chores_positive, reliability_positive, children_positive, punctuality_positive, communication_positive, reference_positive
risk_signals allowed: punctuality_issue, absenteeism_issue, child_safety_concern, misconduct_report, verification_gap, reference_concern, unexplained_absence

Hard rules:
- Do NOT invent employers, incidents, dates, or behaviors not supported by the evidence text.
- If information is missing or too vague to support a label, omit that label.
- If evidence is sparse, thin, or contradictory, set evidence_strength to "low".
- severity should reflect how serious the documented risks are when taken together; use "low" if only minor issues.

Map misconduct severity fields explicitly mentioned in evidence into overall severity when appropriate."""


def _format_evidence_block(
    *,
    references: list[dict[str, Any]],
    misconduct_reports: list[dict[str, Any]],
    retrieved_evidence: list[dict[str, Any]],
) -> str:
    parts: list[str] = []

    parts.append("=== REFERENCES ===")
    if not references:
        parts.append("(none provided)")
    else:
        for i, r in enumerate(references, 1):
            parts.append(
                f'{i}. worker_id={r.get("worker_id","")} source={r.get("source","")} note={r.get("note","")!r}'
            )

    parts.append("\n=== MISCONDUCT REPORTS ===")
    if not misconduct_reports:
        parts.append("(none provided)")
    else:
        for i, m in enumerate(misconduct_reports, 1):
            parts.append(
                f'{i}. worker_id={m.get("worker_id","")} source={m.get("source","")} '
                f'report={m.get("report","")!r} severity={m.get("severity","")!r} verified={m.get("verified","")!r}'
            )

    parts.append("\n=== RETRIEVED EVIDENCE CHUNKS ===")
    if not retrieved_evidence:
        parts.append("(none provided)")
    else:
        for i, e in enumerate(retrieved_evidence, 1):
            meta = e.get("metadata") if isinstance(e.get("metadata"), dict) else {}
            parts.append(
                f'{i}. worker_id={e.get("worker_id","")} source={e.get("source","")} '
                f'source_file={meta.get("source_file","")} risk_area={meta.get("risk_area","")} '
                f'content={e.get("content","")!r}'
            )

    return "\n".join(parts)


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    return json.loads(text)


def _sanitize_signals(labels: list[str], allowed: frozenset[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for x in labels:
        if not isinstance(x, str):
            continue
        k = x.strip()
        if k in allowed and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _coerce_result(data: dict[str, Any]) -> SignalExtractionResult:
    sev = str(data.get("severity", "low")).lower()
    if sev not in ("low", "medium", "high"):
        sev = "low"
    evs = str(data.get("evidence_strength", "low")).lower()
    if evs not in ("low", "medium", "high"):
        evs = "low"

    pos = _sanitize_signals(list(data.get("positive_signals") or []), ALLOWED_POSITIVE)
    risk = _sanitize_signals(list(data.get("risk_signals") or []), ALLOWED_RISK)

    strengths = [str(s).strip() for s in (data.get("strengths") or []) if str(s).strip()]
    concerns = [str(s).strip() for s in (data.get("concerns") or []) if str(s).strip()]

    return SignalExtractionResult(
        positive_signals=pos,
        risk_signals=risk,
        severity=sev,  # type: ignore[arg-type]
        evidence_strength=evs,  # type: ignore[arg-type]
        strengths=strengths[:12],
        concerns=concerns[:12],
    )


def _extract_with_openai(
    evidence_block: str,
    *,
    model: str | None = None,
) -> SignalExtractionResult | None:
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        client = OpenAI()
        use_model = model or os.getenv("OPENAI_SIGNAL_MODEL", "gpt-4o-mini")
        user_msg = (
            "Analyze the following evidence bundle and produce the JSON object.\n\n"
            + evidence_block
        )
        resp = client.chat.completions.create(
            model=use_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = resp.choices[0].message.content or "{}"
        payload = _parse_json_object(raw)
        return _coerce_result(payload)
    except Exception:
        return None


def _truthy(v: object) -> bool:
    if v is True:
        return True
    if v is False or v is None:
        return False
    if isinstance(v, str):
        return v.strip().lower() in {"true", "1", "yes", "y"}
    return bool(v)


def _deterministic_extract(
    *,
    references: list[dict[str, Any]],
    misconduct_reports: list[dict[str, Any]],
    retrieved_evidence: list[dict[str, Any]],
) -> SignalExtractionResult:
    blobs: list[str] = []
    for r in references:
        blobs.append(str(r.get("note") or ""))
    for m in misconduct_reports:
        blobs.append(str(m.get("report") or ""))
        blobs.append(str(m.get("severity") or ""))
    for e in retrieved_evidence:
        blobs.append(str(e.get("content") or ""))

    combined = " ".join(blobs).strip()
    lower = combined.lower()
    char_len = len(combined)

    positive_signals: list[str] = []
    risk_signals: list[str] = []
    strengths: list[str] = []
    concerns: list[str] = []

    if "good with chores" in lower or "good with chore" in lower:
        positive_signals.append("chores_positive")
        strengths.append("Good with chores")
    if "reliable" in lower:
        positive_signals.append("reliability_positive")
        strengths.append("Described as reliable")
    if "good with children" in lower or ("children" in lower and "good" in lower):
        positive_signals.append("children_positive")
        strengths.append("Positive note regarding children")
    if "punctual" in lower and "late" not in lower and "disappeared" not in lower:
        positive_signals.append("punctuality_positive")

    if re.search(r"\blate\b", lower) or "disappeared" in lower:
        risk_signals.append("punctuality_issue")
        concerns.append("Repeated lateness or disappearance mentioned")
    if "absenteeism" in lower or "unexplained absence" in lower or "unexplained absences" in lower:
        risk_signals.append("absenteeism_issue")
        if "unexplained absence" in lower:
            risk_signals.append("unexplained_absence")
        concerns.append("Absenteeism or unexplained absences noted")
    if ("children" in lower or "child" in lower) and any(
        x in lower for x in ("shout", "shouting", "aggressive", "safety concern", "child safety")
    ):
        risk_signals.append("child_safety_concern")
        concerns.append("Child safety or aggressive behavior mentioned")
    if misconduct_reports:
        risk_signals.append("misconduct_report")
        concerns.append("Formal misconduct report on file")
    for r in references:
        if "complaint" in str(r.get("note") or "").lower():
            risk_signals.append("reference_concern")
            concerns.append("Complaints noted in reference material")
            break

    for m in misconduct_reports:
        if "verified" in m and not _truthy(m.get("verified")):
            risk_signals.append("verification_gap")
            concerns.append("Misconduct report marked unverified")
            break

    # Evidence strength: quantity and diversity of sources
    n_sources = (
        (1 if references else 0)
        + (1 if misconduct_reports else 0)
        + (1 if retrieved_evidence else 0)
    )
    if char_len < 80 or n_sources == 0:
        evidence_strength: Literal["low", "medium", "high"] = "low"
    elif char_len < 400 or n_sources < 2:
        evidence_strength = "medium"
    else:
        evidence_strength = "high"

    # Severity from misconduct + risk density
    sev_rank = 0
    for m in misconduct_reports:
        s = str(m.get("severity") or "").lower()
        if s == "high":
            sev_rank = max(sev_rank, 3)
        elif s == "medium":
            sev_rank = max(sev_rank, 2)
        elif s == "low":
            sev_rank = max(sev_rank, 1)
    if "child_safety_concern" in risk_signals:
        sev_rank = max(sev_rank, 3)
    elif len(set(risk_signals)) >= 3:
        sev_rank = max(sev_rank, 2)
    elif risk_signals:
        sev_rank = max(sev_rank, 1)

    if sev_rank >= 3:
        severity: Literal["low", "medium", "high"] = "high"
    elif sev_rank == 2:
        severity = "medium"
    else:
        severity = "low"

    return SignalExtractionResult(
        positive_signals=_sanitize_signals(positive_signals, ALLOWED_POSITIVE),
        risk_signals=_sanitize_signals(risk_signals, ALLOWED_RISK),
        severity=severity,
        evidence_strength=evidence_strength,
        strengths=strengths[:12],
        concerns=concerns[:12],
    )


def extract_from_records(
    *,
    references: list[dict[str, Any]],
    reports: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    model: str | None = None,
) -> dict[str, Any]:
    """Alias for :func:`extract_signals` using orchestrator naming."""
    return extract_signals(
        references=references,
        misconduct_reports=reports,
        retrieved_evidence=evidence,
        model=model,
    )


def extract_signals(
    *,
    references: list[dict[str, Any]],
    misconduct_reports: list[dict[str, Any]],
    retrieved_evidence: list[dict[str, Any]],
    model: str | None = None,
) -> dict[str, Any]:
    """
    Extract structured signals from supplied evidence only.

    Returns a dict matching the project JSON shape (plain Python types).
    """
    block = _format_evidence_block(
        references=references,
        misconduct_reports=misconduct_reports,
        retrieved_evidence=retrieved_evidence,
    )

    llm_result = _extract_with_openai(block, model=model)
    if llm_result is not None:
        return llm_result.model_dump()

    fallback = _deterministic_extract(
        references=references,
        misconduct_reports=misconduct_reports,
        retrieved_evidence=retrieved_evidence,
    )
    return fallback.model_dump()
