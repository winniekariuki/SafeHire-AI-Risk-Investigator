"""
Single source of truth for retrieval / classifier / end-to-end eval metrics.

CLI modules under repo ``evals/`` should call these functions when ``backend`` is on ``sys.path``.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --- Retrieval -----------------------------------------------------------------

_DEFAULT_RETRIEVAL_BENCHMARK_PATH = (
    Path(__file__).resolve().parent / "retrieval_benchmark.json"
)

_RETRIEVAL_CI_TARGETS: list[dict[str, float | int | str]] = [
    {"metric": "recall_at_k", "k": 3, "pass_threshold": 0.9, "warn_threshold": 0.75},
    {"metric": "ndcg_at_k", "k": 3, "pass_threshold": 0.8, "warn_threshold": 0.65},
    {"metric": "map_at_k", "k": 3, "pass_threshold": 0.75, "warn_threshold": 0.6},
    {"metric": "hit_rate_at_k", "k": 3, "pass_threshold": 1.0, "warn_threshold": 0.9},
]


def _normalize(text: str) -> str:
    return text.lower()


def _load_retrieval_cases() -> list[dict[str, Any]]:
    raw_path = Path(str(os.getenv("RETRIEVAL_BENCHMARK_PATH") or _DEFAULT_RETRIEVAL_BENCHMARK_PATH))
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("retrieval benchmark must contain a non-empty 'cases' list")
    return cases


def _doc_match(chunk: dict[str, Any], qrel: dict[str, Any]) -> bool:
    chunk_source = _normalize(str(chunk.get("source") or ""))
    chunk_content = _normalize(str(chunk.get("content") or ""))
    qrel_source = _normalize(str(qrel.get("source") or ""))
    qrel_substring = _normalize(str(qrel.get("content_substring") or ""))
    if qrel_source and qrel_source != chunk_source:
        return False
    return bool(qrel_substring) and qrel_substring in chunk_content


def _align_ranked_relevance(
    chunks: list[dict[str, Any]],
    qrels: list[dict[str, Any]],
) -> tuple[list[int], list[str]]:
    """
    Convert retrieved chunks into graded relevance labels aligned by rank.

    ``aligned_relevance[i]`` is the graded relevance of the chunk at rank i+1.
    A qrel is matched at most once.
    """
    remaining = list(qrels)
    aligned_relevance: list[int] = []
    matched_ids: list[str] = []
    for chunk in chunks:
        hit_idx = -1
        for idx, qrel in enumerate(remaining):
            if _doc_match(chunk, qrel):
                hit_idx = idx
                break
        if hit_idx == -1:
            aligned_relevance.append(0)
            continue
        hit = remaining.pop(hit_idx)
        rel = int(hit.get("relevance", 1))
        aligned_relevance.append(max(0, rel))
        matched_ids.append(str(hit.get("id") or ""))
    return aligned_relevance, matched_ids


def _precision_at_k(aligned_relevance: list[int], k: int) -> float:
    if k <= 0:
        return 0.0
    top_k = aligned_relevance[:k]
    hits = sum(1 for rel in top_k if rel > 0)
    return hits / k


def _recall_at_k(aligned_relevance: list[int], k: int, num_relevant: int) -> float:
    if num_relevant <= 0:
        return 0.0
    top_k = aligned_relevance[:k]
    hits = sum(1 for rel in top_k if rel > 0)
    return hits / num_relevant


def _mrr_at_k(aligned_relevance: list[int], k: int) -> float:
    for rank, rel in enumerate(aligned_relevance[:k], start=1):
        if rel > 0:
            return 1.0 / rank
    return 0.0


def _hit_rate_at_k(aligned_relevance: list[int], k: int) -> float:
    return 1.0 if any(rel > 0 for rel in aligned_relevance[:k]) else 0.0


def _average_precision_at_k(aligned_relevance: list[int], k: int) -> float:
    top_k = aligned_relevance[:k]
    num_relevant_in_top_k = sum(1 for rel in top_k if rel > 0)
    if num_relevant_in_top_k == 0:
        return 0.0
    precision_sum = 0.0
    hits = 0
    for rank, rel in enumerate(top_k, start=1):
        if rel <= 0:
            continue
        hits += 1
        precision_sum += hits / rank
    return precision_sum / num_relevant_in_top_k


def _dcg_at_k(aligned_relevance: list[int], k: int) -> float:
    dcg = 0.0
    for rank, rel in enumerate(aligned_relevance[:k], start=1):
        if rel <= 0:
            continue
        dcg += (2**rel - 1) / math.log2(rank + 1)
    return dcg


def _ndcg_at_k(aligned_relevance: list[int], qrels: list[dict[str, Any]], k: int) -> float:
    dcg = _dcg_at_k(aligned_relevance, k)
    ideal = sorted((max(0, int(q.get("relevance", 1))) for q in qrels), reverse=True)
    idcg = _dcg_at_k(ideal, k)
    if idcg == 0:
        return 0.0
    return dcg / idcg


def _retrieval_run_case(case: dict[str, Any]) -> dict[str, Any]:
    from app.rag.retriever import retrieve_worker_evidence

    worker_id = str(case["worker_id"])
    query = str(case["query"])
    qrels = list(case.get("relevant_documents") or [])
    k_values = [int(k) for k in case.get("k_values", [1, 3, 5, 8])]
    k_values = sorted({k for k in k_values if k > 0})
    k_max = max(k_values) if k_values else 8

    chunks = retrieve_worker_evidence(worker_id, query, top_k=k_max)
    aligned_relevance, matched_ids = _align_ranked_relevance(chunks, qrels)
    num_relevant = len(qrels)

    metrics_by_k: dict[str, dict[str, float]] = {}
    for k in k_values:
        metrics_by_k[str(k)] = {
            "precision_at_k": round(_precision_at_k(aligned_relevance, k), 4),
            "recall_at_k": round(_recall_at_k(aligned_relevance, k, num_relevant), 4),
            "mrr_at_k": round(_mrr_at_k(aligned_relevance, k), 4),
            "ndcg_at_k": round(_ndcg_at_k(aligned_relevance, qrels, k), 4),
            "map_at_k": round(_average_precision_at_k(aligned_relevance, k), 4),
            "hit_rate_at_k": round(_hit_rate_at_k(aligned_relevance, k), 4),
        }

    return {
        "case_id": str(case.get("id") or f"{worker_id}:{query[:32]}"),
        "worker_id": worker_id,
        "query": query,
        "k_values": k_values,
        "requested_top_k": k_max,
        "num_chunks_retrieved": len(chunks),
        "num_relevant_documents": num_relevant,
        "matched_relevant_ids": matched_ids,
        "metrics_by_k": metrics_by_k,
    }


def run_retrieval_eval() -> dict[str, Any]:
    rows = [_retrieval_run_case(c) for c in _load_retrieval_cases()]
    n = len(rows) or 1
    k_values = sorted({k for r in rows for k in r.get("k_values", [])})

    def _avg(metric_name: str, k: int) -> float:
        total = sum(
            float(r["metrics_by_k"].get(str(k), {}).get(metric_name, 0.0)) for r in rows
        )
        return round(total / n, 4)

    mean_precision = {str(k): _avg("precision_at_k", k) for k in k_values}
    mean_recall = {str(k): _avg("recall_at_k", k) for k in k_values}
    mean_mrr = {str(k): _avg("mrr_at_k", k) for k in k_values}
    mean_ndcg = {str(k): _avg("ndcg_at_k", k) for k in k_values}
    mean_map = {str(k): _avg("map_at_k", k) for k in k_values}
    mean_hit_rate = {str(k): _avg("hit_rate_at_k", k) for k in k_values}

    metric_aggregates: dict[str, dict[str, float]] = {
        "precision_at_k": mean_precision,
        "recall_at_k": mean_recall,
        "mrr_at_k": mean_mrr,
        "ndcg_at_k": mean_ndcg,
        "map_at_k": mean_map,
        "hit_rate_at_k": mean_hit_rate,
    }

    ci_items: list[dict[str, Any]] = []
    failed_checks: list[str] = []
    for target in _RETRIEVAL_CI_TARGETS:
        metric = str(target["metric"])
        k = int(target["k"])
        pass_threshold = float(target["pass_threshold"])
        warn_threshold = float(target["warn_threshold"])
        observed = float(metric_aggregates.get(metric, {}).get(str(k), 0.0))
        status = (
            "pass"
            if observed >= pass_threshold
            else "warn"
            if observed >= warn_threshold
            else "fail"
        )
        check = {
            "metric": metric,
            "k": k,
            "value": round(observed, 4),
            "pass_threshold": pass_threshold,
            "warn_threshold": warn_threshold,
            "status": status,
            "pass": status == "pass",
        }
        ci_items.append(check)
        if status != "pass":
            failed_checks.append(f"{metric}@{k}")

    return {
        "suite": "retrieval",
        "schema_version": "1.0.0",
        "cases": rows,
        "aggregate": {
            "k_values": k_values,
            "mean_precision_at_k": mean_precision,
            "mean_recall_at_k": mean_recall,
            "mean_mrr_at_k": mean_mrr,
            "mean_ndcg_at_k": mean_ndcg,
            "mean_map_at_k": mean_map,
            "mean_hit_rate_at_k": mean_hit_rate,
            "num_cases": len(rows),
            "ci_gates": {
                "overall_pass": len(failed_checks) == 0,
                "items": ci_items,
                "failed_checks": failed_checks,
            },
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
    from app.risk.signal_extractor import extract_signals

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
    from app.orchestrator.investigation_orchestrator import run_investigation

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
    """Run retrieval eval only. ``classifier`` / ``end_to_end`` are left null for API compatibility."""
    payload: dict[str, Any] = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "retrieval": None,
        "classifier": None,
        "end_to_end": None,
        "errors": {},
    }
    try:
        payload["retrieval"] = run_retrieval_eval()
    except Exception as exc:  # pragma: no cover - defensive for UI/API
        payload["errors"]["retrieval"] = str(exc)
    return payload
