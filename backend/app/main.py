import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.demo_investigation import build_investigate_payload
from app.evaluation.harness import run_all_evals
from app.orchestrator.investigation_orchestrator import run_investigation
from app.services import profile_service
from app.reports.followup_qa import answer_followup_question
from app.schemas import (
    AskRequest,
    AskResponse,
    EvalRunResponse,
    EvalSummaryResponse,
    IngestRequest,
    IngestResponse,
    InvestigationApiResponse,
    InvestigationGraphRequest,
    InvestigateRequest,
    InvestigateResponse,
    WorkerOut,
)

# Load backend/.env even when uvicorn's cwd is the repo root (not `backend/`).
_backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(_backend_dir / ".env")
load_dotenv()

from app.core.telemetry import configure_langsmith

configure_langsmith()

app = FastAPI(
    title="SafeHire Risk Investigator API",
    description="Backend for worker risk assessments and investigation orchestration.",
    version="0.1.0",
)


def _cors_allow_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


_origins = _cors_allow_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"https://safe-hire-ai-risk-investigator.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness for Docker / App Runner when the service URL is hit directly (no /api prefix)."""
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "safehire-api"}


api_health = APIRouter(prefix="/api")


@api_health.get("/health")
def api_health_check() -> dict[str, str]:
    """Health check behind CloudFront path pattern ``/api/*``."""
    return {"status": "ok"}


# Mounted at ``/api/*`` (production / CloudFront) and at ``/*`` (legacy local URLs without ``/api``).
rest = APIRouter()


@rest.get("/workers", response_model=list[WorkerOut])
def list_workers() -> list[WorkerOut]:
    rows = profile_service.list_workers()
    out: list[WorkerOut] = []
    for r in rows:
        wid = str(r.get("worker_id", ""))
        name = str(r.get("name", ""))
        county = str(r.get("county", "") or "")
        years = r.get("years_experience", "")
        role = county if county else "Worker"
        if years != "" and years is not None:
            role = f"{role} · {years} yrs exp" if county else f"{years} yrs exp"
        out.append(WorkerOut(id=wid, name=name, role=role))
    return out


@rest.post("/investigation/graph")
def investigation_graph(body: InvestigationGraphRequest) -> dict:
    """LangGraph workflow: load → retrieve → signals → sufficiency → branch → report."""
    try:
        return run_investigation(
            body.worker_id,
            retrieval_query=body.retrieval_query,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@rest.post("/investigate", response_model=InvestigationApiResponse)
def investigate(body: InvestigateRequest) -> InvestigationApiResponse:
    """Full investigation pipeline — SafeHire dashboard contract."""
    try:
        payload = run_investigation(body.worker_id.strip())
        return InvestigationApiResponse.model_validate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@rest.post("/investigate/demo", response_model=InvestigateResponse)
def investigate_demo(body: InvestigateRequest) -> InvestigateResponse:
    """Legacy demo payload shape (w-001 style ids only)."""
    try:
        payload = build_investigate_payload(body.worker_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Worker not found") from None
    return InvestigateResponse.model_validate(payload)


@rest.post("/ask", response_model=AskResponse)
def ask(body: AskRequest) -> AskResponse:
    """Follow-up Q&A: retrieve worker evidence, attach rule-based risk snapshot, answer with citations."""
    try:
        payload = answer_followup_question(body.worker_id, body.question)
        return AskResponse.model_validate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@rest.post("/ingest", response_model=IngestResponse)
def ingest(body: IngestRequest) -> IngestResponse:
    job_id = str(uuid.uuid4())
    n = len(body.items or [])
    return IngestResponse(
        accepted=True,
        job_id=job_id,
        message=f"Queued ingest for source={body.source!r} ({n} item(s)). Demo stub.",
    )


@rest.get("/eval/summary", response_model=EvalSummaryResponse)
def eval_summary() -> EvalSummaryResponse:
    return EvalSummaryResponse(
        retrieval={"ndcg_at_5": None, "recall_at_10": None},
        classifier={"accuracy": None, "macro_f1": None},
        end_to_end={"passed": 0, "total": 0},
        notes="Eval harness not executed — placeholder summary.",
    )


@rest.post("/eval/run", response_model=EvalRunResponse)
def eval_run() -> EvalRunResponse:
    """Execute retrieval, classifier, and end-to-end suites (may take tens of seconds)."""
    return EvalRunResponse.model_validate(run_all_evals())


app.include_router(api_health)
app.include_router(rest, prefix="/api")
app.include_router(rest)
