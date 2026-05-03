"""Demo investigation payloads aligned with the frontend dashboard shapes."""

from __future__ import annotations

from typing import Any

WORKERS: list[dict[str, str]] = [
    {"id": "w-001", "name": "Alex Morgan", "role": "Licensed practical nurse"},
    {"id": "w-002", "name": "Jordan Lee", "role": "Home health aide"},
    {"id": "w-003", "name": "Sam Rivera", "role": "Care coordinator"},
]


def get_worker(worker_id: str) -> dict[str, str] | None:
    for w in WORKERS:
        if w["id"] == worker_id:
            return w
    return None


def build_investigate_payload(worker_id: str) -> dict[str, Any]:
    worker = get_worker(worker_id)
    if worker is None:
        raise KeyError(worker_id)

    wid = worker["id"]
    elevated = wid == "w-002"

    return {
        "riskScore": 62 if elevated else 38,
        "riskBand": "elevated" if elevated else "moderate",
        "summary": (
            "Mixed verification signals with gaps in recent supervision notes; "
            "elevated attention recommended."
            if elevated
            else "Overall alignment with policy and references; a few documentation gaps to close."
        ),
        "profile": {
            "name": worker["name"],
            "role": worker["role"],
            "tenure": "3 yrs 4 mo",
            "location": "Metro North region",
            "lastVerified": "2026-03-12",
        },
        "strengths": [
            "Consistent positive references from two prior placements.",
            "Completed mandatory training within SLA.",
            "No substantiated misconduct in internal logs for reviewed window.",
        ],
        "concerns": (
            [
                "Two reference responses delayed beyond policy window.",
                "Sparse documentation for one incident follow-up.",
            ]
            if elevated
            else ["One verification note lacks reviewer signature."]
        ),
        "missingInfo": [
            "Supervisor attestation for Q1 2026 (if applicable).",
            "Clarification on temporary assignment gap (Apr 2025).",
        ],
        "evidence": [
            {
                "title": "Reference packet — Primary supervisor",
                "source": "reference_notes.csv",
                "excerpt": (
                    '"Reliable on shifts; communicates escalations promptly." '
                    "— verified 2026-02-01."
                ),
            },
            {
                "title": "Policy excerpt — Documentation standards",
                "source": "policy_docs/handbook §4.2",
                "excerpt": (
                    "Incident notes must include timeline, parties involved, and "
                    "resolution status within 72 hours."
                ),
            },
            {
                "title": "Verification note — Credential check",
                "source": "verification_notes.csv",
                "excerpt": (
                    "License active; next renewal due 2027-06; no sanctions found "
                    "in queried registry."
                ),
            },
        ],
        "riskSignals": {
            "reference_timeliness_risk": "elevated" if elevated else "low",
            "documentation_completeness": 0.71 if elevated else 0.88,
            "policy_alignment_score": 0.74 if elevated else 0.91,
            "flags": (
                ["delayed_reference", "thin_supervision_notes"]
                if elevated
                else []
            ),
        },
        "markdownReport": _markdown_report(worker["name"], worker["role"], elevated),
        "followUpQa": [
            {
                "q": "Why is risk elevated despite no substantiated misconduct?",
                "a": (
                    "Elevation reflects documentation timeliness and verification gaps, "
                    "not proven violations. Signals are probabilistic and should be "
                    "confirmed in review."
                ),
            },
            {
                "q": "What would downgrade the band?",
                "a": (
                    "Closing missing attestations, receiving complete references within "
                    "policy windows, and adding supervisor notes for the flagged period."
                ),
            },
        ],
    }


def _markdown_report(name: str, role: str, elevated: bool) -> str:
    band = "Elevated" if elevated else "Moderate"
    return f"""# Investigation summary — {name}

## Overview
This assessment synthesizes references, verification artifacts, and policy-aligned checks for **{role}**.

## Findings
- **Risk posture**: {band} based on retrieval coverage and signal extraction.
- **Evidence quality**: Sufficient for an automated draft; human review recommended where noted.

## Recommendations
1. Obtain missing attestations listed under *Missing information*.
2. If elevated band persists, route to manual review queue.

---
*Demo response from POST /investigate — replace with orchestrator output.*
"""


def demo_answer(question: str, worker_id: str | None) -> str:
    """Static demo answers for POST /ask."""
    q = question.strip().lower()
    worker = get_worker(worker_id) if worker_id else None
    ctx = f" ({worker['name']})" if worker else ""

    if "risk" in q and ("elevated" in q or "high" in q):
        return (
            "Demo answer%s: Elevated bands usually combine weaker verification coverage "
            "with documentation gaps—not necessarily proven misconduct. Confirm with "
            "primary sources in review."
            % ctx
        )
    if "missing" in q or "attestation" in q:
        return (
            "Demo answer%s: Missing attestations should be requested from the assigned "
            "supervisor and tracked until received before finalizing the investigation."
            % ctx
        )
    return (
        "Demo answer%s: This endpoint returns canned guidance until the LLM graph is "
        "wired. Ask about risk bands, missing attestations, or documentation gaps."
        % ctx
    )
