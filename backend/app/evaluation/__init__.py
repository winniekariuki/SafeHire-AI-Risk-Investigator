"""Offline evaluation harness. ``POST /eval/run`` runs retrieval eval only; other suites are for direct/CLI use."""

from app.evaluation.harness import (
    run_all_evals,
    run_classifier_eval,
    run_end_to_end_eval,
    run_retrieval_eval,
)

__all__ = [
    "run_all_evals",
    "run_classifier_eval",
    "run_end_to_end_eval",
    "run_retrieval_eval",
]
