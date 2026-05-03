"""
Deterministic rule-based risk scoring.

The numeric score and band are owned entirely by these rules — not by an LLM.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.misconduct_service import get_misconduct_reports
from app.services.profile_service import get_worker
from app.services.reference_service import get_reference_notes
from app.services.verification_service import get_verification

# Point weights (additive, capped at SCORE_CAP)
WEIGHT_ID_NOT_VERIFIED = 20
WEIGHT_PHONE_NOT_VERIFIED = 10
WEIGHT_FEWER_THAN_TWO_REFERENCES = 15
WEIGHT_PUNCTUALITY_ISSUE = 15
WEIGHT_ABSENTEEISM_ISSUE = 20
WEIGHT_CHILD_SAFETY_CONCERN = 35
WEIGHT_VERIFIED_HIGH_SEVERITY_MISCONDUCT = 40

SCORE_CAP = 100

_SCORE_BANDS: tuple[tuple[int, int, str], ...] = (
    (0, 30, "Low"),
    (31, 65, "Medium"),
    (66, SCORE_CAP, "High"),
)


def _truthy(value: object) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _risk_band(score: int) -> str:
    for lo, hi, label in _SCORE_BANDS:
        if lo <= score <= hi:
            return label
    return "High"


def _recommendation(band: str) -> str:
    return {
        "Low": "Proceed with standard screening",
        "Medium": "Proceed with caution",
        "High": "Manual review required before hire",
    }[band]


def _confidence(
    *,
    ref_count: int,
    id_verified: bool,
    phone_verified: bool,
) -> str:
    if ref_count >= 2 and id_verified and phone_verified:
        return "High"
    if ref_count == 0 or (not id_verified and not phone_verified):
        return "Low"
    return "Moderate"


def _collect_text_blobs(
    references: list[dict[str, object]],
    misconducts: list[dict[str, object]],
) -> tuple[list[str], list[str]]:
    ref_texts = [str(r.get("note") or "") for r in references]
    mis_texts = [str(m.get("report") or "") for m in misconducts]
    return ref_texts, mis_texts


def _punctuality_issue(ref_texts: list[str]) -> bool:
    """Late attendance / disappearance signals in reference narrative."""
    for t in ref_texts:
        s = t.lower()
        if re.search(r"\blate\b", s) or "disappeared" in s:
            return True
    return False


def _absenteeism_issue(ref_texts: list[str], mis_texts: list[str]) -> bool:
    for t in ref_texts + mis_texts:
        s = t.lower()
        if "absenteeism" in s:
            return True
        if "unexplained absence" in s or "unexplained absences" in s:
            return True
        if "repeated absent" in s:
            return True
    return False


def _child_safety_concern(ref_texts: list[str], mis_texts: list[str]) -> bool:
    for t in ref_texts + mis_texts:
        s = t.lower()
        if "child safety" in s:
            return True
        if "safety concern" in s and ("child" in s or "children" in s):
            return True
        if "children" in s and ("shout" in s or "shouting" in s):
            return True
        if "child" in s and "aggressive" in s:
            return True
    return False


def _verified_high_severity(misconducts: list[dict[str, object]]) -> bool:
    for m in misconducts:
        sev = str(m.get("severity") or "").strip().lower()
        if sev == "high" and _truthy(m.get("verified")):
            return True
    return False


def compute_risk(
    *,
    verification: dict[str, Any],
    references: list[dict[str, Any]],
    misconducts: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Rule-based score from verification + reference + misconduct rows.

    Numeric score and band are authoritative — not derived from LLM signals.
    """
    reasons: list[str] = []
    score = 0

    id_ok = _truthy(verification.get("id_verified"))
    phone_ok = _truthy(verification.get("phone_verified"))

    if not id_ok:
        score += WEIGHT_ID_NOT_VERIFIED
        reasons.append("Government ID not verified")

    if not phone_ok:
        score += WEIGHT_PHONE_NOT_VERIFIED
        reasons.append("Phone number not verified")

    ref_count = len(references)
    if ref_count < 2:
        score += WEIGHT_FEWER_THAN_TWO_REFERENCES
        reasons.append(
            "No reference notes on file"
            if ref_count == 0
            else "Only one reference completed"
        )

    ref_texts, mis_texts = _collect_text_blobs(references, misconducts)

    if _punctuality_issue(ref_texts):
        score += WEIGHT_PUNCTUALITY_ISSUE
        reasons.append("Punctuality or attendance reliability concern in references")

    if _absenteeism_issue(ref_texts, mis_texts):
        score += WEIGHT_ABSENTEEISM_ISSUE
        reasons.append("Absenteeism signal found")

    if _child_safety_concern(ref_texts, mis_texts):
        score += WEIGHT_CHILD_SAFETY_CONCERN
        reasons.append("Child safety concern flagged in source material")

    if _verified_high_severity(misconducts):
        score += WEIGHT_VERIFIED_HIGH_SEVERITY_MISCONDUCT
        reasons.append("Verified high-severity misconduct on file")

    score = min(score, SCORE_CAP)
    band = _risk_band(score)

    return {
        "score": score,
        "risk_level": band,
        "confidence": _confidence(
            ref_count=ref_count,
            id_verified=id_ok,
            phone_verified=phone_ok,
        ),
        "recommendation": _recommendation(band),
        "reasons": reasons,
    }


def score_worker(worker_id: str) -> dict[str, Any]:
    """
    Compute risk from CSV-backed services only.

    Raises:
        ValueError: If the worker or verification row is missing.
    """
    wid = worker_id.strip()
    get_worker(wid)
    verification = get_verification(wid)
    references = get_reference_notes(wid)
    misconducts = get_misconduct_reports(wid)
    return compute_risk(
        verification=verification,
        references=references,
        misconducts=misconducts,
    )


def score(
    *,
    profile: dict[str, Any],
    verification: dict[str, Any],
    signals: dict[str, Any],
    reports: list[dict[str, Any]],
    sufficiency: dict[str, Any],
) -> dict[str, Any]:
    """
    Main orchestrator entry: same numeric rules as :func:`score_worker`, plus
    non-scoring context (signal summary, sufficiency gate).

    Final numeric score is still produced only by rule logic — never by the LLM.
    """
    wid = str(profile.get("worker_id", "")).strip()
    references = get_reference_notes(wid)
    base = compute_risk(
        verification=verification,
        references=references,
        misconducts=reports,
    )
    out = dict(base)
    out["signal_context"] = {
        "severity": signals.get("severity"),
        "risk_signals": signals.get("risk_signals"),
        "positive_signals": signals.get("positive_signals"),
        "evidence_strength": signals.get("evidence_strength"),
    }
    out["manual_review_required"] = bool(sufficiency.get("manual_review_required"))
    return out
