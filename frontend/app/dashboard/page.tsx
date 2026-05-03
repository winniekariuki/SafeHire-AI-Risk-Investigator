"use client";

import { UserButton, useAuth } from "@clerk/nextjs";
import { useCallback, useEffect, useState } from "react";
import { EvidenceList } from "@/components/EvidenceList";
import { FollowUpQA } from "@/components/FollowUpQA";
import { Header } from "@/components/Header";
import { ManualReviewAlert } from "@/components/ManualReviewAlert";
import { MarkdownReport } from "@/components/MarkdownReport";
import {
  DEFAULT_PIPELINE_STEPS,
  ProcessingStatus,
  type PipelineStep,
} from "@/components/ProcessingStatus";
import { RiskSummaryCard } from "@/components/RiskSummaryCard";
import { SectionCard } from "@/components/SectionCard";
import { SignalCards } from "@/components/SignalCards";
import { WorkerProfileCard } from "@/components/WorkerProfileCard";
import { PlatformAsk } from "@/components/PlatformAsk";
import { WorkerSelector } from "@/components/WorkerSelector";
import { fetchWorkers, runInvestigation } from "@/lib/api";
import type { InvestigationResponse, WorkerOption } from "@/lib/types";

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

function BulletedListOrNone({ items }: { items: string[] }) {
  if (items.length === 0) {
    return (
      <p className="text-sm italic text-zinc-500 dark:text-zinc-400">None</p>
    );
  }
  return (
    <ul className="list-disc space-y-2 pl-4 text-sm text-zinc-700 dark:text-zinc-300">
      {items.map((item, i) => (
        <li key={`${i}-${item.slice(0, 64)}`}>{item}</li>
      ))}
    </ul>
  );
}

export default function DashboardPage() {
  const { getToken } = useAuth();
  const [workers, setWorkers] = useState<WorkerOption[]>([]);
  const [workersError, setWorkersError] = useState<string | null>(null);
  const [workerId, setWorkerId] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [pipeline, setPipeline] = useState<PipelineStep[]>(() =>
    DEFAULT_PIPELINE_STEPS.map((s) => ({ ...s, done: false })),
  );
  const [result, setResult] = useState<InvestigationResponse | null>(null);
  const [investigateError, setInvestigateError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await fetchWorkers(() => getToken());
        if (cancelled) return;
        setWorkers(list);
        setWorkersError(null);
        setWorkerId((prev) => {
          if (prev && list.some((w) => w.id === prev)) return prev;
          return list[0]?.id ?? "";
        });
      } catch (e) {
        if (!cancelled) {
          setWorkersError(e instanceof Error ? e.message : "Failed to load workers");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [getToken]);

  const runAssessment = useCallback(async () => {
    if (!workerId) return;
    setIsRunning(true);
    setResult(null);
    setInvestigateError(null);
    const initial = DEFAULT_PIPELINE_STEPS.map((s) => ({ ...s, done: false }));
    setPipeline(initial);

    const animate = async () => {
      const copy = DEFAULT_PIPELINE_STEPS.map((s) => ({ ...s, done: false }));
      for (let i = 0; i < copy.length; i++) {
        await sleep(380 + i * 90);
        copy[i] = { ...copy[i]!, done: true };
        setPipeline(copy.map((s) => ({ ...s })));
      }
    };

    try {
      const [data] = await Promise.all([
        runInvestigation(workerId, () => getToken()),
        animate(),
      ]);
      setResult(data);
      setPipeline(DEFAULT_PIPELINE_STEPS.map((s) => ({ ...s, done: true })));
    } catch (e) {
      setInvestigateError(
        e instanceof Error ? e.message : "Investigation request failed",
      );
      setPipeline(DEFAULT_PIPELINE_STEPS.map((s) => ({ ...s, done: false })));
    } finally {
      setIsRunning(false);
    }
  }, [workerId, getToken]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
        <Header
          title="Investigation dashboard"
          description="Select a worker, run the assessment pipeline, and review synthesized risk output, evidence, and follow-ups."
          actions={<UserButton />}
        />

        <div className="flex flex-col gap-6">
          <PlatformAsk />
          <SectionCard title="Assessment controls">
            {workersError ? (
              <p className="text-sm text-red-600 dark:text-red-400">{workersError}</p>
            ) : null}
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <WorkerSelector
                workers={workers}
                value={workerId}
                onChange={setWorkerId}
                disabled={isRunning}
              />
              <button
                type="button"
                disabled={isRunning || !workerId}
                onClick={() => void runAssessment()}
                className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
              >
                {isRunning ? "Running risk assessment…" : "Run risk assessment"}
              </button>
            </div>
          </SectionCard>

          <ProcessingStatus steps={pipeline} isRunning={isRunning} />

          {investigateError ? (
            <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200">
              {investigateError}
            </p>
          ) : null}

          {result?.manual_review_required ? <ManualReviewAlert /> : null}

          {result ? (
            <>
              <RiskSummaryCard risk_summary={result.risk_summary} />
              <WorkerProfileCard worker={result.worker} />
              <div className="grid gap-6 lg:grid-cols-3">
                <SectionCard title="Strengths">
                  <BulletedListOrNone items={result.strengths} />
                </SectionCard>
                <SectionCard title="Concerns">
                  <BulletedListOrNone items={result.concerns} />
                </SectionCard>
                <SectionCard title="Missing information">
                  <BulletedListOrNone items={result.missing_information} />
                </SectionCard>
              </div>
              <SignalCards risk_signals={result.risk_signals} />
              <EvidenceList retrieved_evidence={result.retrieved_evidence} />
              <MarkdownReport report={result.report} />
              <FollowUpQA workerId={workerId} enabled={!!result} />
            </>
          ) : null}

          {!result && !isRunning && !investigateError ? (
            <p className="text-center text-sm text-zinc-500 dark:text-zinc-400">
              Run a risk assessment to populate output from{" "}
              <code className="rounded bg-zinc-200/80 px-1 dark:bg-zinc-800">POST /api/investigate</code>
              .
            </p>
          ) : null}
        </div>
    </div>
  );
}
