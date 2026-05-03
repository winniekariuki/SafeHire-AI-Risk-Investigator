"""Rule-based risk bands from CSV-backed workers."""

from __future__ import annotations

import pytest

from app.risk.risk_scorer import score_worker


@pytest.mark.parametrize(
    ("worker_id", "expected_band"),
    [
        ("W001", "Low"),
        ("W002", "Medium"),
        ("W004", "High"),
    ],
)
def test_worker_risk_band(worker_id: str, expected_band: str) -> None:
    out = score_worker(worker_id)
    assert out["risk_level"] == expected_band


def test_w001_low_recommendation() -> None:
    out = score_worker("W001")
    assert out["recommendation"] == "Proceed with standard screening"


def test_w002_medium_recommendation() -> None:
    out = score_worker("W002")
    assert out["recommendation"] == "Proceed with caution"


def test_w004_high_recommendation() -> None:
    out = score_worker("W004")
    assert out["recommendation"] == "Manual review required before hire"
