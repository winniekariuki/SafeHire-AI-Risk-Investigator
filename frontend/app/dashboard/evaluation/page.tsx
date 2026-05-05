"use client";

import { UserButton, useAuth } from "@clerk/nextjs";
import { useCallback, useMemo, useState } from "react";
import {
  buildRetrievalTrendData,
  RetrievalMetricsTrendChart,
} from "@/components/EvaluationMetricCharts";
import { Header } from "@/components/Header";
import { SectionCard } from "@/components/SectionCard";
import { runEvaluations } from "@/lib/api";
import type { EvalRunResponse } from "@/lib/types";

type RetrievalAggregate = {
  k_values?: number[];
  mean_precision_at_k?: Record<string, number>;
  mean_recall_at_k?: Record<string, number>;
  mean_mrr_at_k?: Record<string, number>;
  mean_ndcg_at_k?: Record<string, number>;
  mean_map_at_k?: Record<string, number>;
  mean_hit_rate_at_k?: Record<string, number>;
  ci_gates?: {
    overall_pass?: boolean;
    items?: RetrievalCiGate[];
    failed_checks?: string[];
  };
};

type RetrievalMetricAtK = {
  precision_at_k?: number;
  recall_at_k?: number;
  mrr_at_k?: number;
  ndcg_at_k?: number;
  map_at_k?: number;
  hit_rate_at_k?: number;
};

type RetrievalCiGate = {
  metric: string;
  k: number;
  value: number;
  pass_threshold: number;
  warn_threshold: number;
  status: "pass" | "warn" | "fail" | string;
  pass: boolean;
};

type RetrievalCase = {
  case_id: string;
  worker_id: string;
  query: string;
  num_chunks_retrieved?: number;
  matched_relevant_ids?: string[];
  metrics_by_k?: Record<string, RetrievalMetricAtK>;
};

function asRetrievalCases(value: unknown): RetrievalCase[] {
  if (!Array.isArray(value)) return [];
  return value.filter((c): c is RetrievalCase => {
    if (!c || typeof c !== "object") return false;
    const candidate = c as Partial<RetrievalCase>;
    return (
      typeof candidate.case_id === "string" &&
      typeof candidate.worker_id === "string" &&
      typeof candidate.query === "string"
    );
  });
}

function formatPct(value: number | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "-";
  return `${(value * 100).toFixed(1)}%`;
}

function gateStatusStyles(status: string): string {
  if (status === "pass") {
    return "border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/40 dark:text-green-200";
  }
  if (status === "warn") {
    return "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200";
  }
  return "border-red-200 bg-red-50 text-red-800 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200";
}

export default function EvaluationPage() {
  const { getToken } = useAuth();
  const [retrievalK, setRetrievalK] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<EvalRunResponse | null>(null);

  const evaluate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runEvaluations(() => getToken());
      setResult(data);
    } catch (e) {
      const msg =
        e instanceof Error
          ? e.name === "AbortError"
            ? "Evaluation timed out (try again or run evals on the server)."
            : e.message
          : "Evaluation failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  const retrievalSuite = result?.retrieval ?? null;
  const retrievalErr = result?.errors?.retrieval;
  const retrievalAggregate = retrievalSuite?.aggregate as RetrievalAggregate | undefined;
  const retrievalCases = useMemo(
    () => asRetrievalCases(retrievalSuite?.cases),
    [retrievalSuite],
  );
  const trendData = useMemo(
    () => buildRetrievalTrendData(retrievalAggregate),
    [retrievalAggregate],
  );

  const retrievalKValues = useMemo(
    () =>
      (retrievalAggregate?.k_values ?? [])
        .map((k) => String(k))
        .filter((k) => k.length > 0),
    [retrievalAggregate],
  );
  const selectedRetrievalK = retrievalKValues.includes(retrievalK)
    ? retrievalK
    : retrievalKValues[retrievalKValues.length - 1] ?? "";

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
      <Header
        title="Retrieval evaluation"
        description="Run the labeled RAG benchmark against your API: mean ranking metrics by K, CI gates, and per-case breakdown."
        actions={<UserButton />}
      />

      <div className="flex flex-col gap-6">
        <SectionCard title="Controls">
          <div className="flex flex-wrap items-center gap-4">
            <button
              type="button"
              disabled={loading}
              onClick={() => void evaluate()}
              className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
            >
              {loading ? "Running retrieval eval…" : "Run retrieval eval"}
            </button>
            {result?.ran_at ? (
              <span className="text-xs text-zinc-500 dark:text-zinc-400">
                Last run: {new Date(result.ran_at).toLocaleString()}
              </span>
            ) : null}
          </div>
          <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
            Calls <code className="rounded bg-zinc-100 px-1 dark:bg-zinc-800">POST /eval/run</code>{" "}
            (retrieval suite only). Ensure embeddings and Supabase vector data are available.
          </p>
        </SectionCard>

        {error ? (
          <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200">
            {error}
          </p>
        ) : null}

        {result ? (
          <SectionCard title="Aggregate metrics by K">
            {retrievalErr ? (
              <p className="text-sm text-red-600 dark:text-red-400">{retrievalErr}</p>
            ) : (
              <div className="space-y-4">
                <RetrievalMetricsTrendChart
                  title="Mean retrieval quality vs. cutoff K"
                  data={trendData}
                  emptyMessage="No aggregate metrics — check retrieval suite errors or benchmark config."
                />

                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <label htmlFor="retrieval-k" className="text-zinc-600 dark:text-zinc-300">
                    Table: show metrics at
                  </label>
                  <select
                    id="retrieval-k"
                    className="rounded-md border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                    value={selectedRetrievalK}
                    onChange={(e) => setRetrievalK(e.target.value)}
                  >
                    {retrievalKValues.map((k) => (
                      <option key={k} value={k}>
                        @{k}
                      </option>
                    ))}
                  </select>
                </div>

                {retrievalAggregate?.ci_gates?.items?.length ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-zinc-700 dark:text-zinc-200">
                        CI quality gates
                      </span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-xs font-medium ${
                          retrievalAggregate.ci_gates.overall_pass
                            ? gateStatusStyles("pass")
                            : gateStatusStyles("fail")
                        }`}
                      >
                        {retrievalAggregate.ci_gates.overall_pass ? "PASS" : "FAIL"}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {retrievalAggregate.ci_gates.items.map((item) => (
                        <span
                          key={`${item.metric}@${item.k}`}
                          className={`rounded-full border px-2.5 py-1 text-xs font-medium ${gateStatusStyles(
                            item.status,
                          )}`}
                          title={`Observed ${formatPct(item.value)}; pass >= ${formatPct(
                            item.pass_threshold,
                          )}, warn >= ${formatPct(item.warn_threshold)}`}
                        >
                          {item.metric.replace("_at_k", "")}@{item.k}: {item.status.toUpperCase()}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}

                {retrievalCases.length > 0 && selectedRetrievalK ? (
                  <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
                    <table className="min-w-full divide-y divide-zinc-200 text-sm dark:divide-zinc-800">
                      <thead className="bg-zinc-50 dark:bg-zinc-900/40">
                        <tr className="text-left text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                          <th className="px-3 py-2">Case</th>
                          <th className="px-3 py-2">Worker</th>
                          <th className="px-3 py-2">Chunks</th>
                          <th className="px-3 py-2">Matches</th>
                          <th className="px-3 py-2">P@{selectedRetrievalK}</th>
                          <th className="px-3 py-2">R@{selectedRetrievalK}</th>
                          <th className="px-3 py-2">MRR@{selectedRetrievalK}</th>
                          <th className="px-3 py-2">nDCG@{selectedRetrievalK}</th>
                          <th className="px-3 py-2">MAP@{selectedRetrievalK}</th>
                          <th className="px-3 py-2">Hit@{selectedRetrievalK}</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                        {retrievalCases.map((c) => {
                          const row = c.metrics_by_k?.[selectedRetrievalK] ?? {};
                          return (
                            <tr key={c.case_id} className="align-top">
                              <td className="px-3 py-2">
                                <div className="font-medium text-zinc-900 dark:text-zinc-100">
                                  {c.case_id}
                                </div>
                                <div className="max-w-[320px] text-xs text-zinc-500 dark:text-zinc-400">
                                  {c.query}
                                </div>
                              </td>
                              <td className="px-3 py-2 text-zinc-700 dark:text-zinc-300">
                                {c.worker_id}
                              </td>
                              <td className="px-3 py-2 text-zinc-700 dark:text-zinc-300">
                                {c.num_chunks_retrieved ?? "-"}
                              </td>
                              <td className="px-3 py-2 text-zinc-700 dark:text-zinc-300">
                                {c.matched_relevant_ids?.length ?? 0}
                              </td>
                              <td className="px-3 py-2">{formatPct(row.precision_at_k)}</td>
                              <td className="px-3 py-2">{formatPct(row.recall_at_k)}</td>
                              <td className="px-3 py-2">{formatPct(row.mrr_at_k)}</td>
                              <td className="px-3 py-2">{formatPct(row.ndcg_at_k)}</td>
                              <td className="px-3 py-2">{formatPct(row.map_at_k)}</td>
                              <td className="px-3 py-2">{formatPct(row.hit_rate_at_k)}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </div>
            )}
          </SectionCard>
        ) : (
          <p className="text-center text-sm text-zinc-500 dark:text-zinc-400">
            Click <strong className="font-medium text-zinc-700 dark:text-zinc-300">Run retrieval eval</strong>{" "}
            to load the chart and tables.
          </p>
        )}

        {result?.retrieval && !retrievalErr ? (
          <SectionCard title="Raw retrieval payload (JSON)">
            <pre className="max-h-72 overflow-auto rounded-lg bg-zinc-950 p-4 font-mono text-xs leading-relaxed text-zinc-100">
              {JSON.stringify(result.retrieval, null, 2)}
            </pre>
          </SectionCard>
        ) : null}
      </div>
    </div>
  );
}
