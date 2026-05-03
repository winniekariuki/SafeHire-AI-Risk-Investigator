"use client";

import { UserButton, useAuth } from "@clerk/nextjs";
import { useCallback, useState } from "react";
import {
  aggregateToRows,
  EvaluationMetricChart,
} from "@/components/EvaluationMetricCharts";
import { Header } from "@/components/Header";
import { SectionCard } from "@/components/SectionCard";
import { runEvaluations } from "@/lib/api";
import type { EvalRunResponse, EvalSuiteResult } from "@/lib/types";

type SuiteKey = "retrieval" | "classifier" | "end_to_end";

const SUITE_TABS: { id: SuiteKey; label: string }[] = [
  { id: "retrieval", label: "Retrieval" },
  { id: "classifier", label: "Classifier" },
  { id: "end_to_end", label: "End-to-end" },
];

function suiteAggregate(suite: EvalSuiteResult | null | undefined) {
  return suite?.aggregate as Record<string, number | null | undefined> | undefined;
}

export default function EvaluationPage() {
  const { getToken } = useAuth();
  const [activeTab, setActiveTab] = useState<SuiteKey>("retrieval");
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

  const suiteData = (key: SuiteKey) => result?.[key] ?? null;
  const errors = result?.errors ?? {};

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
      <Header
        title="Evaluation"
        description="Run offline retrieval, classifier, and end-to-end suites against the API and inspect aggregate metrics."
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
              {loading ? "Running evaluations…" : "Evaluate"}
            </button>
            {result?.ran_at ? (
              <span className="text-xs text-zinc-500 dark:text-zinc-400">
                Last run: {new Date(result.ran_at).toLocaleString()}
              </span>
            ) : null}
          </div>
          <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
            Calls <code className="rounded bg-zinc-100 px-1 dark:bg-zinc-800">POST /eval/run</code>
            — may take up to a few minutes on cold Chroma / first load.
          </p>
        </SectionCard>

        {error ? (
          <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200">
            {error}
          </p>
        ) : null}

        {Object.keys(errors).length > 0 ? (
          <SectionCard title="Suite errors">
            <ul className="space-y-2 text-sm text-red-700 dark:text-red-300">
              {Object.entries(errors).map(([k, v]) => (
                <li key={k}>
                  <span className="font-medium">{k}:</span> {v}
                </li>
              ))}
            </ul>
          </SectionCard>
        ) : null}

        <div className="flex flex-wrap gap-2 border-b border-zinc-200 pb-2 dark:border-zinc-800">
          {SUITE_TABS.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => setActiveTab(id)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                activeTab === id
                  ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                  : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-900"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {result ? (
          <SectionCard title={`${SUITE_TABS.find((t) => t.id === activeTab)?.label ?? ""} metrics`}>
            {errors[activeTab] ? (
              <p className="text-sm text-red-600 dark:text-red-400">{errors[activeTab]}</p>
            ) : (
              <EvaluationMetricChart
                title="Aggregate scores (0–100%)"
                data={aggregateToRows(suiteAggregate(suiteData(activeTab)))}
                emptyMessage="No chart data for this suite."
              />
            )}
          </SectionCard>
        ) : (
          <p className="text-center text-sm text-zinc-500 dark:text-zinc-400">
            Click <strong className="font-medium text-zinc-700 dark:text-zinc-300">Evaluate</strong>{" "}
            to load graphs and case tables.
          </p>
        )}

        {result && suiteData(activeTab) && !errors[activeTab] ? (
          <SectionCard title="Case details (JSON)">
            <pre className="max-h-72 overflow-auto rounded-lg bg-zinc-950 p-4 font-mono text-xs leading-relaxed text-zinc-100">
              {JSON.stringify(suiteData(activeTab), null, 2)}
            </pre>
          </SectionCard>
        ) : null}
      </div>
    </div>
  );
}
