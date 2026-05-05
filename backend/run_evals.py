#!/usr/bin/env python3
"""
Run evaluation modules from the backend directory (no need to cd to repo root).

Usage::

    python run_evals.py retrieval
    python run_evals.py classifier
    python run_evals.py end-to-end

Or with the venv::

    .venv/bin/python run_evals.py retrieval

The repo root is added to sys.path so the ``evals`` package resolves.
"""

from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_ROOT = _REPO_ROOT / "backend"

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency guard
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(_BACKEND_ROOT / ".env")
    load_dotenv()

_MODULES = {
    "retrieval": "evals.eval_retrieval",
    "classifier": "evals.eval_classifier",
    "end-to-end": "evals.eval_end_to_end",
    "e2e": "evals.eval_end_to_end",
    "eval_retrieval": "evals.eval_retrieval",
    "eval_classifier": "evals.eval_classifier",
    "eval_end_to_end": "evals.eval_end_to_end",
}


def main() -> None:
    p = argparse.ArgumentParser(description="SafeHire offline eval harness")
    p.add_argument(
        "which",
        choices=sorted(set(_MODULES.keys())),
        help="Which eval to run",
    )
    args = p.parse_args()
    mod = _MODULES[args.which]
    root = str(_REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    runpy.run_module(mod, run_name="__main__")


if __name__ == "__main__":
    main()
