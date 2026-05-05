"""
Retrieval evaluation — delegates to ``app.evaluation.harness``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_ROOT = _REPO_ROOT / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.evaluation.harness import run_retrieval_eval


def main() -> None:
    print(json.dumps(run_retrieval_eval(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
