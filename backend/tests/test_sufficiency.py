"""Evidence sufficiency and manual-review gate."""

from __future__ import annotations

from app.risk.sufficiency_checker import check_sufficiency


def test_w003_triggers_manual_review() -> None:
    """W003 has no references, failed ID check, and no RAG rows in this check → insufficient."""
    out = check_sufficiency("W003")
    assert out["manual_review_required"] is True
    assert out["sufficient"] is False
    assert "No completed references" in out["missing_information"]
    assert "ID verification missing" in out["missing_information"]


def test_w003_reason_insufficient() -> None:
    out = check_sufficiency("W003")
    assert "Insufficient evidence" in out["reason"]
