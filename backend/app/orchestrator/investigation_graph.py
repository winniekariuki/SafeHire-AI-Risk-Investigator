"""
LangGraph wrapper around :func:`run_investigation`.

The imperative orchestrator in ``investigation_orchestrator.py`` is the source of truth.
This graph exists so demos can show “workflow execution” in LangGraph tooling with a
single compiled pipeline node.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.constants import END
from langgraph.graph import START, StateGraph

from app.orchestrator.investigation_orchestrator import run_investigation


class InvestigationGraphState(TypedDict, total=False):
    worker_id: str
    retrieval_query: str | None
    response: dict[str, Any]


def _pipeline(state: InvestigationGraphState) -> dict[str, Any]:
    out = run_investigation(
        state["worker_id"],
        retrieval_query=state.get("retrieval_query"),
    )
    return {"response": out}


def build_graph() -> Any:
    g = StateGraph(InvestigationGraphState)
    g.add_node("investigation_pipeline", _pipeline)
    g.add_edge(START, "investigation_pipeline")
    g.add_edge("investigation_pipeline", END)
    return g.compile()


_compiled_graph: Any | None = None


def get_compiled_graph() -> Any:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
