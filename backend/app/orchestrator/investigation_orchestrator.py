"""Main investigation orchestrator — imperative pipeline (source of truth)."""

from __future__ import annotations

from typing import Any

from app.core.telemetry import emit_pipeline_event, pipeline_trace
from app.rag import retriever
from app.reports.report_generator import generate as generate_report
from app.risk import risk_scorer, signal_extractor, sufficiency_checker
from app.services import (
    misconduct_service,
    profile_service,
    reference_service,
    verification_service,
)

DEFAULT_RETRIEVAL_QUERY = (
    "Assess hiring risk, strengths, concerns, and missing verification evidence"
)


def run_investigation(
    worker_id: str,
    *,
    retrieval_query: str | None = None,
) -> dict[str, Any]:
    """
    Load CSV rows → retrieve Chroma evidence → signals → sufficiency → rule-based risk → report.

    Populate Chroma first: ``python -m app.rag.ingest``.
    """
    wid = worker_id.strip()
    query = (retrieval_query or "").strip() or DEFAULT_RETRIEVAL_QUERY

    with pipeline_trace("safehire.investigation", {"worker_id": wid}) as root:
        emit_pipeline_event(root, "investigation_started", {"worker_id": wid})

        profile = profile_service.get_worker(wid)
        verification = verification_service.get_status(wid)
        references = reference_service.get_references(wid)
        reports = misconduct_service.get_reports(wid)

        emit_pipeline_event(
            root,
            "profile_loaded",
            {
                "worker_id": wid,
                "references_count": len(references),
                "misconduct_reports_count": len(reports),
            },
        )

        retrieved_evidence = retriever.retrieve_worker_evidence(
            worker_id=wid,
            query=query,
            top_k=8,
        )

        emit_pipeline_event(
            root,
            "evidence_retrieved",
            {"worker_id": wid, "chunk_count": len(retrieved_evidence)},
        )

        extracted_signals = signal_extractor.extract_from_records(
            references=references,
            reports=reports,
            evidence=retrieved_evidence,
        )

        emit_pipeline_event(
            root,
            "signals_extracted",
            {
                "worker_id": wid,
                "severity": str(extracted_signals.get("severity", "")),
                "strengths_count": len(extracted_signals.get("strengths") or []),
                "concerns_count": len(extracted_signals.get("concerns") or []),
            },
        )

        sufficiency = sufficiency_checker.check(
            profile=profile,
            verification=verification,
            references=references,
            reports=reports,
            evidence=retrieved_evidence,
        )

        manual_required = bool(sufficiency.get("manual_review_required"))
        if manual_required:
            emit_pipeline_event(
                root,
                "manual_review_triggered",
                {
                    "worker_id": wid,
                    "manual_review_required": True,
                    "missing_information_count": len(
                        sufficiency.get("missing_information") or [],
                    ),
                },
            )

        risk_result = risk_scorer.score(
            profile=profile,
            verification=verification,
            signals=extracted_signals,
            reports=reports,
            sufficiency=sufficiency,
        )

        try:
            score_val = int(risk_result["score"])
        except (KeyError, TypeError, ValueError):
            score_val = 0

        emit_pipeline_event(
            root,
            "risk_scored",
            {
                "worker_id": wid,
                "risk_level": str(risk_result.get("risk_level", "")),
                "score": score_val,
                "manual_review_required": bool(
                    risk_result.get("manual_review_required"),
                ),
            },
        )

        report = generate_report(
            profile=profile,
            verification=verification,
            evidence=retrieved_evidence,
            signals=extracted_signals,
            risk=risk_result,
            sufficiency=sufficiency,
            references=references,
            reports=reports,
        )

        emit_pipeline_event(
            root,
            "report_generated",
            {"worker_id": wid, "report_length": len(report)},
        )

        worker_out: dict[str, Any] = {
            **{str(k): v for k, v in profile.items()},
            **{str(k): v for k, v in verification.items()},
            "references_completed": len(references),
            "misconduct_reports": len(reports),
        }

        return {
            "worker": worker_out,
            "risk_summary": risk_result,
            "strengths": extracted_signals["strengths"],
            "concerns": extracted_signals["concerns"],
            "missing_information": sufficiency["missing_information"],
            "retrieved_evidence": retrieved_evidence,
            "risk_signals": extracted_signals,
            "report": report,
            "manual_review_required": sufficiency["manual_review_required"],
        }
