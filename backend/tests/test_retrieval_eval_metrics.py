"""Unit tests for ranked retrieval metrics in the eval harness."""

from __future__ import annotations

from app.evaluation.harness import (
    _average_precision_at_k,
    _align_ranked_relevance,
    _hit_rate_at_k,
    _mrr_at_k,
    _ndcg_at_k,
    _precision_at_k,
    _recall_at_k,
)


def test_align_ranked_relevance_matches_once_per_qrel() -> None:
    chunks = [
        {"source": "Reference Note", "content": "often came late and once disappeared"},
        {"source": "Reference Note", "content": "often came late and once disappeared"},
        {"source": "Misconduct Report", "content": "repeated absenteeism and poor communication"},
    ]
    qrels = [
        {
            "id": "ref",
            "source": "Reference Note",
            "content_substring": "came late and once disappeared",
            "relevance": 2,
        },
        {
            "id": "misconduct",
            "source": "Misconduct Report",
            "content_substring": "repeated absenteeism",
            "relevance": 3,
        },
    ]

    aligned, matched_ids = _align_ranked_relevance(chunks, qrels)

    assert aligned == [2, 0, 3]
    assert matched_ids == ["ref", "misconduct"]


def test_ranked_metrics_values() -> None:
    aligned = [3, 0, 2, 0]
    num_relevant = 2
    qrels = [{"relevance": 3}, {"relevance": 2}]

    assert _precision_at_k(aligned, 3) == 2 / 3
    assert _recall_at_k(aligned, 1, num_relevant) == 0.5
    assert _mrr_at_k(aligned, 4) == 1.0
    assert round(_ndcg_at_k(aligned, qrels, 2), 4) == 0.7872
    assert round(_average_precision_at_k(aligned, 4), 4) == 0.8333
    assert _hit_rate_at_k(aligned, 1) == 1.0
    assert _hit_rate_at_k([0, 0, 0], 3) == 0.0
