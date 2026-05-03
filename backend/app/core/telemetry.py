"""
LangSmith tracing for SafeHire pipeline milestones.

Each investigation (or follow-up) is a root **chain** run; milestones are child **tool**
runs named after the event (e.g. ``risk_scored``) with the same payload shape as before.

Environment (LangSmith):

- ``LANGSMITH_TRACING=true`` or ``LANGCHAIN_TRACING_V2=true`` — enable posting runs.
- ``LANGSMITH_API_KEY`` or ``LANGCHAIN_API_KEY`` — required for hosted LangSmith.
- ``LANGSMITH_PROJECT`` / ``LANGCHAIN_PROJECT`` — project in the LangSmith UI (optional).
- ``LANGSMITH_ENDPOINT`` / ``LANGCHAIN_ENDPOINT`` — optional API URL (e.g. EU region).

When tracing is disabled or no API key is set, helpers no-op: no network calls.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from langsmith import utils as ls_utils
from langsmith.run_trees import RunTree

_LOGGER = logging.getLogger("safehire.telemetry")

_CONFIGURED = False


def _truthy(name: str, default: str = "") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def langsmith_pipeline_tracing_enabled() -> bool:
    """Whether SafeHire should emit LangSmith runs for pipeline milestones."""
    if not ls_utils.get_api_key(None):
        return False
    # Align with LangSmith SDK (LANGSMITH_* / LANGCHAIN_* TRACING_V2 / TRACING).
    if ls_utils.tracing_is_enabled() is True:
        return True
    # Allow common spellings the SDK treats as off but operators often set (e.g. LANGSMITH_TRACING=yes).
    return (
        _truthy("LANGSMITH_TRACING")
        or _truthy("LANGCHAIN_TRACING")
        or _truthy("LANGSMITH_TRACING_V2")
        or _truthy("LANGCHAIN_TRACING_V2")
    )


def _normalize_value(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, bool | int | float | str):
        return val
    if isinstance(val, dict):
        return _normalize_payload(val)
    if isinstance(val, (list, tuple)):
        return [_normalize_value(x) for x in val]
    return str(val)


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Coerce values to JSON-friendly primitives for run inputs/outputs."""
    out: dict[str, Any] = {}
    for key, val in payload.items():
        if val is None:
            continue
        out[key] = _normalize_value(val)
    return out


def emit_pipeline_event(root: RunTree | None, event: str, payload: dict[str, Any]) -> None:
    """Record a pipeline milestone as a child LangSmith run named ``event``."""
    if root is None:
        return
    safe = _normalize_payload(payload)
    child = root.create_child(
        name=event,
        run_type="tool",
        inputs={"event": event, **safe},
    )
    child.end(outputs=safe)
    child.post()


def configure_langsmith() -> None:
    """Idempotent startup hook — logs whether pipeline tracing will emit runs."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True
    if langsmith_pipeline_tracing_enabled():
        project = ls_utils.get_tracer_project() or "(default project)"
        _LOGGER.info("LangSmith pipeline tracing enabled (project=%s)", project)
    elif not ls_utils.get_api_key(None):
        _LOGGER.info(
            "LangSmith pipeline tracing disabled: no API key "
            "(set LANGSMITH_API_KEY or LANGCHAIN_API_KEY)",
        )
    else:
        _LOGGER.info(
            "LangSmith pipeline tracing disabled: tracing flag off "
            "(set LANGSMITH_TRACING=true or LANGCHAIN_TRACING_V2=true)",
        )


@contextmanager
def pipeline_trace(name: str, inputs: dict[str, Any]) -> Generator[RunTree | None, None, None]:
    """Root run for a pipeline (investigation or follow-up). Yields ``None`` when tracing is off."""
    if not langsmith_pipeline_tracing_enabled():
        yield None
        return
    root = RunTree(name=name, run_type="chain", inputs=_normalize_payload(inputs))
    root.post()
    try:
        yield root
        root.end(outputs={"status": "completed"})
    except Exception as exc:
        root.end(error=str(exc))
        raise
    finally:
        root.patch()
        try:
            root.client.flush(timeout=15.0)
        except Exception as exc:
            _LOGGER.warning("LangSmith flush failed (runs may appear delayed): %s", exc)
