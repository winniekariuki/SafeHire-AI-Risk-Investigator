"""
Single source of truth for retrieval / classifier / end-to-end eval metrics.

CLI modules under repo ``evals/`` should call these functions when ``backend`` is on ``sys.path``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.orchestrator.investigation_orchestrator import run_investigation
from app.rag.retriever import retrieve_worker_evidence
from app.risk.signal_extractor import extract_signals

# --- Retrieval -----------------------------------------------------------------

RETRIEVAL_CASES: list[dict[str, object]] = [
    {
        "worker_id": "W002",
        "query": "Find evidence of absenteeism",
        "expected_keywords": ["late", "disappeared", "absenteeism"],
        "k": 8,
    },
]


def _normalize(text: str) -> str:
    return text.lower()


def _keyword_coverage(chunks: list[dict[str, object]], keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    blob = _normalize(" ".join(str(c.get("content") or "") for c in chunks))
    hits = sum(1 for kw in keywords if kw.lower() in blob)
    return hits / len(keywords)


def _recall_at_k_keyword_proxy(
    chunks: list[dict[str, object]],
    keywords: list[str],
) -> float:
    return _keyword_coverage(chunks, keywords)


def _mrr_first_keyword_hit(chunks: list[dict[str, object]], keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    kws = [k.lower() for k in keywords]
    for rank, ch in enumerate(chunks, start=1):
        text = _normalize(str(ch.get("content") or ""))
        if any(kw in text for kw in kws):
            return 1.0 / rank
    return 0.0


def _retrieval_run_case(case: dict[str, object]) -> dict[str, object]:
    worker_id = str(case["worker_id"])
    query = str(case["query"])
    keywords = list(case["expected_keywords"])  # type: ignore[list-item]
    k = int(case.get("k", 8))
    chunks = retrieve_worker_evidence(worker_id, query, top_k=k)
    cov = _keyword_coverage(chunks, keywords)
    r_at_k = _recall_at_k_keyword_proxy(chunks, keywords)
    mrr = _mrr_first_keyword_hit(chunks, keywords)
    return {
        "worker_id": worker_id,
        "query": query,
        "k": k,
        "num_chunks": len(chunks),
        "keyword_coverage": round(cov, 4),
        "recall_at_k": round(r_at_k, 4),
        "mrr": round(mrr, 4),
        "expected_keywords": keywords,
    }


def run_retrieval_eval() -> dict[str, Any]:
    rows = [_retrieval_run_case(c) for c in RETRIEVAL_CASES]
    n = len(rows)
    return {
        "cases": rows,
        "aggregate": {
            "mean_keyword_coverage": round(sum(r["keyword_coverage"] for r in rows) / n, 4),
            "mean_recall_at_k": round(sum(r["recall_at_k"] for r in rows) / n, 4),
            "mean_mrr": round(sum(r["mrr"] for r in rows) / n, 4),
            "num_cases": n,
        },
    }


# --- Classifier ----------------------------------------------------------------

CLASSIFIER_CASES: list[dict[str, Any]] = [
    {
        "name": "lateness_absenteeism",
        "text": (
            "She often arrived late and missed work without notice; "
            "absenteeism was discussed with the employer."
        ),
        "expected_risk_signals": ["punctuality_issue", "absenteeism_issue"],
        "expected_severity": "low",
    },
    {
        "name": "user_example_lateness",
        "text": "She often arrived late and missed work without notice.",
        "expected_risk_signals": ["punctuality_issue"],
        "expected_severity": "low",
    },
]


def _refs_from_text(text: str) -> list[dict[str, Any]]:
    return [
        {"worker_id": "EVAL", "source": "Synthetic reference", "note": text},
    ]


def _prf1(expected: set[str], predicted: set[str]) -> tuple[float, float, float]:
    if not expected and not predicted:
        return 1.0, 1.0, 1.0
    if not predicted:
        return 0.0, 0.0, 0.0
    tp = len(expected & predicted)
    fp = len(predicted - expected)
    fn = len(expected - predicted)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


def _json_validity(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    required = {"risk_signals", "severity", "positive_signals", "strengths", "concerns"}
    if not required.issubset(obj.keys()):
        return False
    try:
        json.dumps(obj)
    except (TypeError, ValueError):
        return False
    return True


def _classifier_run_case(case: dict[str, Any]) -> dict[str, Any]:
    text = str(case["text"])
    expected_rs = set(case["expected_risk_signals"])
    expected_sev = case.get("expected_severity")
    references = _refs_from_text(text)
    raw = extract_signals(
        references=references,
        misconduct_reports=[],
        retrieved_evidence=[],
    )
    valid = _json_validity(raw)
    predicted_rs = set(raw.get("risk_signals") or [])
    p, r, f1 = _prf1(expected_rs, predicted_rs)
    pred_sev = str(raw.get("severity") or "")
    sev_ok = pred_sev == expected_sev if expected_sev is not None else None
    return {
        "name": case.get("name", ""),
        "precision_risk_signals": round(p, 4),
        "recall_risk_signals": round(r, 4),
        "f1_risk_signals": round(f1, 4),
        "json_validity": valid,
        "severity_predicted": pred_sev,
        "severity_expected": expected_sev,
        "severity_accuracy": sev_ok,
        "expected_risk_signals": sorted(expected_rs),
        "predicted_risk_signals": sorted(predicted_rs),
    }


def run_classifier_eval() -> dict[str, Any]:
    rows = [_classifier_run_case(c) for c in CLASSIFIER_CASES]
    n = len(rows)
    valid_n = sum(1 for r in rows if r["json_validity"])
    sev_cases = [r for r in rows if r["severity_accuracy"] is not None]
    sev_acc = (
        sum(1 for r in sev_cases if r["severity_accuracy"]) / len(sev_cases)
        if sev_cases
        else None
    )
    agg: dict[str, Any] = {
        "mean_precision": round(sum(r["precision_risk_signals"] for r in rows) / n, 4),
        "mean_recall": round(sum(r["recall_risk_signals"] for r in rows) / n, 4),
        "mean_f1": round(sum(r["f1_risk_signals"] for r in rows) / n, 4),
        "json_validity_rate": round(valid_n / n, 4),
        "severity_accuracy_rate": round(sev_acc, 4) if sev_acc is not None else None,
        "num_cases": n,
    }
    return {"cases": rows, "aggregate": agg}


# --- End-to-end ----------------------------------------------------------------

E2E_CASES: list[dict[str, Any]] = [
    {
        "worker_id": "W001",
        "expected_risk_level": "Low",
        "expected_recommendation": "Proceed with standard screening",
        "expected_manual_review_required": False,
        "expected_evidence_returned": None,
    },
    {
        "worker_id": "W002",
        "expected_risk_level": "Medium",
        "expected_recommendation": "Proceed with caution",
        "expected_manual_review_required": False,
        "expected_evidence_returned": None,
    },
    {
        "worker_id": "W003",
        "expected_risk_level": "Medium",
        "expected_recommendation": "Proceed with caution",
        "expected_manual_review_required": True,
        "expected_evidence_returned": None,
    },
    {
        "worker_id": "W004",
        "expected_risk_level": "High",
        "expected_recommendation": "Manual review required before hire",
        "expected_manual_review_required": None,
        "expected_evidence_returned": None,
    },
]


def _e2e_run_case(case: dict[str, Any]) -> dict[str, Any]:
    wid = str(case["worker_id"])
    out = run_investigation(wid)
    rs = out.get("risk_summary") or {}
    risk_level = str(rs.get("risk_level") or "")
    recommendation = str(rs.get("recommendation") or "")
    manual_top = bool(out.get("manual_review_required"))
    evidence_returned = len(out.get("retrieved_evidence") or []) > 0
    exp_level = case["expected_risk_level"]
    exp_rec = case["expected_recommendation"]
    exp_manual = case.get("expected_manual_review_required")
    exp_evid = case.get("expected_evidence_returned")
    return {
        "worker_id": wid,
        "risk_level_ok": risk_level == exp_level,
        "recommendation_ok": recommendation == exp_rec,
        "risk_level_expected": exp_level,
        "risk_level_actual": risk_level,
        "recommendation_expected": exp_rec,
        "recommendation_actual": recommendation,
        "manual_review_actual": manual_top,
        "manual_review_ok": (
            manual_top == exp_manual if exp_manual is not None else None
        ),
        "evidence_returned": evidence_returned,
        "evidence_ok": (
            evidence_returned == exp_evid if exp_evid is not None else None
        ),
        "score": rs.get("score"),
    }


def _rate_bool(keys: list[bool | None]) -> float | None:
    filtered = [k for k in keys if k is not None]
    if not filtered:
        return None
    return sum(1 for k in filtered if k) / len(filtered)


def run_end_to_end_eval() -> dict[str, Any]:
    rows = [_e2e_run_case(c) for c in E2E_CASES]
    n = len(rows)
    ma = _rate_bool([r["manual_review_ok"] for r in rows])
    ea = _rate_bool([r["evidence_ok"] for r in rows])
    agg: dict[str, Any] = {
        "risk_level_accuracy": round(sum(1 for r in rows if r["risk_level_ok"]) / n, 4),
        "recommendation_accuracy": round(
            sum(1 for r in rows if r["recommendation_ok"]) / n,
            4,
        ),
        "manual_review_accuracy": round(ma, 4) if ma is not None else None,
        "evidence_accuracy": round(ea, 4) if ea is not None else None,
        "num_cases": n,
    }
    return {"cases": rows, "aggregate": agg}


def run_all_evals() -> dict[str, Any]:
    """Run all three suites; failures are captured per suite without aborting."""
    payload: dict[str, Any] = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "retrieval": None,
        "classifier": None,
        "end_to_end": None,
        "errors": {},
    }
    for key, fn in (
        ("retrieval", run_retrieval_eval),
        ("classifier", run_classifier_eval),
        ("end_to_end", run_end_to_end_eval),
    ):
        try:
            payload[key] = fn()
        except Exception as exc:  # pragma: no cover - defensive for UI/API
            payload["errors"][key] = str(exc)
    return payload
