"""
Deterministic evidence sufficiency checks — no LLM.

Drives manual-review / UI fallback when evidence is incomplete or unsafe to automate.
"""

from __future__ import annotations

from typing import Any

from app.services.misconduct_service import get_misconduct_reports
from app.services.profile_service import get_worker
from app.services.reference_service import get_reference_notes
from app.services.verification_service import get_verification

_REASON_INSUFFICIENT = "Insufficient evidence for reliable automated recommendation"
_REASON_SUFFICIENT = "Evidence meets minimum thresholds for automated recommendation"


def _truthy(value: object) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _has_csv_evidence(
    references: list[dict[str, object]],
    misconducts: list[dict[str, object]],
) -> bool:
    return len(references) > 0 or len(misconducts) > 0


def _no_retrieved_evidence(
    references: list[dict[str, object]],
    reports: list[dict[str, object]],
    evidence: list[dict[str, Any]],
) -> bool:
    """True when there is no CSV narrative and no RAG chunks."""
    return not _has_csv_evidence(references, reports) and len(evidence) == 0


def _positive_reference_without_major_negatives(note: str) -> bool:
    """Broadly positive reference without obvious risk language in the same note."""
    s = note.lower()
    positives = (
        "reliable",
        "excellent",
        "great ",
        "good with children",
        "good with chores",
        "punctual",
    )
    negatives = (
        "late",
        "disappeared",
        "complaint",
        "shouting",
        "absent",
        "aggressive",
        "concern",
        "misconduct",
        "safety",
    )
    if not any(p in s for p in positives):
        return False
    return not any(n in s for n in negatives)


def _has_verified_serious_misconduct(
    misconducts: list[dict[str, object]],
) -> bool:
    for m in misconducts:
        if not _truthy(m.get("verified")):
            continue
        sev = str(m.get("severity") or "").strip().lower()
        if sev in ("medium", "high"):
            return True
    return False


def _conflicting_serious_allegations(
    references: list[dict[str, object]],
    misconducts: list[dict[str, object]],
) -> bool:
    """
    Positive reference narrative coexists with verified medium/high misconduct —
    too brittle for a purely automated recommendation without review.
    """
    if not _has_verified_serious_misconduct(misconducts):
        return False
    for r in references:
        note = str(r.get("note") or "")
        if _positive_reference_without_major_negatives(note):
            return True
    return False


def _high_risk_report_unverified(misconducts: list[dict[str, object]]) -> bool:
    for m in misconducts:
        sev = str(m.get("severity") or "").strip().lower()
        if sev == "high" and not _truthy(m.get("verified")):
            return True
    return False


def check(
    *,
    profile: dict[str, Any],
    verification: dict[str, Any],
    references: list[dict[str, Any]],
    reports: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Sufficiency using explicitly supplied records + retrieved chunks.

    ``profile`` is accepted for API symmetry (worker identity already implied by rows).
    """
    _ = profile

    missing_information: list[str] = []

    if len(references) == 0:
        missing_information.append("No completed references")

    if not _truthy(verification.get("id_verified")):
        missing_information.append("ID verification missing")

    if _no_retrieved_evidence(references, reports, evidence):
        missing_information.append("No retrieved evidence")

    if _conflicting_serious_allegations(references, reports):
        missing_information.append("Conflicting serious allegations")

    if _high_risk_report_unverified(reports):
        missing_information.append("High-risk report is unverified")

    manual_review_required = len(missing_information) > 0
    sufficient = not manual_review_required

    return {
        "manual_review_required": manual_review_required,
        "sufficient": sufficient,
        "missing_information": missing_information,
        "reason": _REASON_INSUFFICIENT if manual_review_required else _REASON_SUFFICIENT,
    }


def check_sufficiency(worker_id: str) -> dict[str, Any]:
    """
    Return manual-review flags by loading CSV rows (no RAG chunks).

    Raises:
        ValueError: If worker or verification row is missing.
    """
    wid = worker_id.strip()
    profile = get_worker(wid)
    verification = get_verification(wid)
    references = get_reference_notes(wid)
    reports = get_misconduct_reports(wid)
    return check(
        profile=profile,
        verification=verification,
        references=references,
        reports=reports,
        evidence=[],
    )
