import type {
  AskResponse,
  EvalRunResponse,
  InvestigationResponse,
  WorkerOption,
} from "@/lib/types";

/**
 * Public API origin + optional path prefix (e.g. CloudFront ``https://...cloudfront.net/api``).
 * Prefer ``NEXT_PUBLIC_API_BASE_URL`` or ``NEXT_PUBLIC_API_URL`` (either may be set in CI/Docker).
 */
export function getApiBase(): string {
  const raw =
    process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_URL?.trim() ||
    "";
  const base = raw.replace(/\/$/, "");
  if (!base) {
    throw new Error(
      "Set NEXT_PUBLIC_API_BASE_URL or NEXT_PUBLIC_API_URL (e.g. http://localhost:8000/api for Docker)",
    );
  }
  return base;
}

type GetToken = () => Promise<string | null>;

async function jsonHeaders(getToken?: GetToken): Promise<HeadersInit> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (getToken) {
    const token = await getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

export async function fetchWorkers(getToken?: GetToken): Promise<WorkerOption[]> {
  const res = await fetch(`${getApiBase()}/workers`, {
    headers: await jsonHeaders(getToken),
  });
  if (!res.ok) {
    throw new Error(`Failed to load workers (${res.status})`);
  }
  return res.json() as Promise<WorkerOption[]>;
}

export async function runInvestigation(
  workerId: string,
  getToken?: GetToken,
): Promise<InvestigationResponse> {
  const res = await fetch(`${getApiBase()}/investigate`, {
    method: "POST",
    headers: await jsonHeaders(getToken),
    body: JSON.stringify({ worker_id: workerId }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(
      detail || `Investigation failed (${res.status})`,
    );
  }
  return res.json() as Promise<InvestigationResponse>;
}

export async function askFollowUp(
  workerId: string | null,
  question: string,
  getToken?: GetToken,
): Promise<AskResponse> {
  const body =
    workerId == null || workerId === ""
      ? { question, worker_id: null as string | null }
      : { worker_id: workerId, question };
  const res = await fetch(`${getApiBase()}/ask`, {
    method: "POST",
    headers: await jsonHeaders(getToken),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Follow-up failed (${res.status})`);
  }
  return res.json() as Promise<AskResponse>;
}

const EVAL_TIMEOUT_MS = 120_000;

export async function runEvaluations(getToken?: GetToken): Promise<EvalRunResponse> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), EVAL_TIMEOUT_MS);
  try {
    const res = await fetch(`${getApiBase()}/eval/run`, {
      method: "POST",
      headers: await jsonHeaders(getToken),
      body: "{}",
      signal: ctrl.signal,
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || `Evaluation failed (${res.status})`);
    }
    return res.json() as Promise<EvalRunResponse>;
  } finally {
    clearTimeout(timer);
  }
}
