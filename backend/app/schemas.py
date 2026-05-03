from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkerOut(BaseModel):
    id: str
    name: str
    role: str


class InvestigateRequest(BaseModel):
    worker_id: str = Field(..., description="Worker identifier (e.g. W001)")


class InvestigationApiResponse(BaseModel):
    """Frontend dashboard contract — maps 1:1 to UI sections."""

    worker: dict[str, Any]
    risk_summary: dict[str, Any]
    strengths: list[str]
    concerns: list[str]
    missing_information: list[str]
    retrieved_evidence: list[dict[str, Any]]
    risk_signals: dict[str, Any]
    report: str
    manual_review_required: bool


class InvestigationGraphRequest(BaseModel):
    worker_id: str = Field(..., description="CSV worker_id (e.g. W001)")
    retrieval_query: str | None = Field(
        default=None,
        description="Optional retrieval query for Chroma evidence search",
    )


class ProfileOut(BaseModel):
    name: str
    role: str
    tenure: str
    location: str
    lastVerified: str


class EvidenceItem(BaseModel):
    title: str
    source: str
    excerpt: str


class FollowUpQA(BaseModel):
    q: str
    a: str


class InvestigateResponse(BaseModel):
    riskScore: int
    riskBand: Literal["low", "moderate", "elevated", "high"]
    summary: str
    profile: ProfileOut
    strengths: list[str]
    concerns: list[str]
    missingInfo: list[str]
    evidence: list[EvidenceItem]
    riskSignals: dict[str, Any]
    markdownReport: str
    followUpQa: list[FollowUpQA]


class AskRequest(BaseModel):
    worker_id: str = Field(..., description="CSV worker_id (e.g. W002)")
    question: str = Field(..., description="Follow-up question about this worker")


class AskEvidenceSnippet(BaseModel):
    source: str
    content: str


class AskResponse(BaseModel):
    answer: str
    evidence: list[AskEvidenceSnippet] = Field(
        default_factory=list,
        description="Supporting snippets shown to the model / user (no extras beyond retrieval + CSV fallbacks)",
    )


class IngestRequest(BaseModel):
    source: str = Field(..., description="Logical source label (e.g. policy_docs)")
    items: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional records or chunk payloads to index later",
    )


class IngestResponse(BaseModel):
    accepted: bool
    job_id: str
    message: str


class EvalSummaryResponse(BaseModel):
    retrieval: dict[str, Any | None]
    classifier: dict[str, Any | None]
    end_to_end: dict[str, Any | None]
    notes: str


class EvalRunResponse(BaseModel):
    """Payload from ``POST /eval/run`` — full metrics for dashboard charts."""

    ran_at: str
    retrieval: dict[str, Any] | None = None
    classifier: dict[str, Any] | None = None
    end_to_end: dict[str, Any] | None = None
    errors: dict[str, str] = Field(default_factory=dict)
