"""Full investigation pipeline on seeded CSV workers."""

from __future__ import annotations

import pytest

from app.orchestrator.investigation_orchestrator import run_investigation


def test_w001_low_risk() -> None:
    out = run_investigation("W001")
    assert out["risk_summary"]["risk_level"] == "Low"


def test_w002_medium_risk() -> None:
    out = run_investigation("W002")
    assert out["risk_summary"]["risk_level"] == "Medium"


def test_w003_manual_review() -> None:
    out = run_investigation("W003")
    assert out["manual_review_required"] is True


def test_w004_high_risk() -> None:
    out = run_investigation("W004")
    assert out["risk_summary"]["risk_level"] == "High"


def test_w004_high_recommendation_text() -> None:
    out = run_investigation("W004")
    assert (
        out["risk_summary"]["recommendation"]
        == "Manual review required before hire"
    )
