"""Platform-wide Q&A: evidence normalization and deterministic fallback."""

from unittest.mock import patch

from app.reports.platform_qa import answer_platform_question


@patch("app.reports.platform_qa._llm_answer", return_value=None)
@patch("app.reports.platform_qa.retrieve_platform_evidence")
def test_answer_platform_question_uses_evidence(mock_retrieve, _mock_llm) -> None:
    mock_retrieve.return_value = [
        {"worker_id": "W001", "source": "Reference", "content": "Excellent with children and punctual."},
    ]
    out = answer_platform_question("Which workers are good with children?")
    assert "answer" in out
    assert len(out["evidence"]) == 1
    assert out["evidence"][0]["worker_id"] == "W001"
    assert "children" in out["answer"].lower() or "W001" in out["answer"]


def test_answer_platform_question_empty() -> None:
    out = answer_platform_question("   ")
    assert out["answer"] == "Please enter a question."
    assert out["evidence"] == []


@patch("app.reports.platform_qa._llm_answer", return_value=None)
@patch("app.reports.platform_qa.retrieve_platform_evidence", return_value=[])
def test_platform_lowest_risk_uses_csv_scores(_mock_retrieve, _mock_llm) -> None:
    """Cross-worker risk comparisons must use rule-based scores, not RAG hits."""
    out = answer_platform_question("Which worker has the lowest risk?")
    assert "W001" in out["answer"]
    assert "lowest" in out["answer"].lower() or "score" in out["answer"].lower()


@patch("app.reports.platform_qa._llm_answer", return_value=None)
@patch("app.reports.platform_qa.retrieve_platform_evidence", return_value=[])
def test_platform_hire_recommendation_uses_scores(_mock_retrieve, _mock_llm) -> None:
    out = answer_platform_question("Which of the workers would you recommend I hire?")
    assert "W001" in out["answer"]
    assert "decision support" in out["answer"].lower() or "not a hire" in out["answer"].lower()
