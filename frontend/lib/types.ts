export type WorkerOption = {
  id: string;
  name: string;
  role: string;
};

export type RiskSummary = {
  score: number;
  risk_level: string;
  confidence: string;
  recommendation: string;
  reasons: string[];
  signal_context?: Record<string, unknown>;
  manual_review_required?: boolean;
};

export type RetrievedEvidenceItem = {
  worker_id?: string;
  source?: string;
  content?: string;
  metadata?: {
    source_file?: string;
    risk_area?: string;
    /** Set when the API filled from CSV because the vector index had no matches. */
    origin?: "structured_reference" | "structured_misconduct" | string;
  };
};

/** Matches `InvestigationApiResponse` from the FastAPI backend. */
export type InvestigationResponse = {
  worker: Record<string, unknown>;
  risk_summary: RiskSummary;
  strengths: string[];
  concerns: string[];
  missing_information: string[];
  retrieved_evidence: RetrievedEvidenceItem[];
  risk_signals: Record<string, unknown>;
  report: string;
  manual_review_required: boolean;
};

export type AskResponse = {
  answer: string;
  evidence: { worker_id?: string | null; source: string; content: string }[];
};

/** Matches ``EvalRunResponse`` from ``POST /eval/run``. */
export type EvalRunResponse = {
  ran_at: string;
  retrieval: EvalSuiteResult | null;
  classifier: EvalSuiteResult | null;
  end_to_end: EvalSuiteResult | null;
  errors: Record<string, string>;
};

export type EvalSuiteResult = {
  cases?: unknown[];
  aggregate?: Record<string, number | null>;
};
