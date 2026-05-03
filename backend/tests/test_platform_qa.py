"""Platform-wide Q&A uses CSV fallback when vector RPC is absent."""

from __future__ import annotations

from unittest.mock import patch

from app.reports.platform_qa import answer_platform_question


def test_platform_question_children_prefers_w001() -> None:
    with (
        patch("app.reports.platform_qa.retrieve_platform_evidence") as mock_ret,
        patch("app.reports.platform_qa._llm_answer", return_value=None),
    ):
        mock_ret.return_value = [
            {
                "worker_id": "W001",
                "source": "Reference Note",
                "content": "Mary was reliable, punctual, and good with children.",
                "relevance_score": 1.0,
            },
            {
                "worker_id": "W004",
                "source": "Reference Note",
                "content": "Complaints about shouting at children.",
                "relevance_score": 0.5,
            },
        ]
        out = answer_platform_question(
            "Of all workers on the platform, who is good with children?"
        )
    assert "W001" in out["answer"] or "Mary" in out["answer"]
    assert any(e.get("worker_id") == "W001" for e in out["evidence"])
