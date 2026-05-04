"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback, useState } from "react";
import { AskAnswerMarkdown } from "@/components/AskAnswerMarkdown";
import { SectionCard } from "@/components/SectionCard";
import { askFollowUp } from "@/lib/api";

type Turn = {
  question: string;
  answer: string;
  evidence: { worker_id?: string | null; source: string; content: string }[];
};

export function FollowUpQA({
  workerId,
  enabled,
}: {
  workerId: string;
  enabled: boolean;
}) {
  const { getToken } = useAuth();
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    const q = question.trim();
    if (!q || !enabled) return;
    setLoading(true);
    setError(null);
    try {
      const tokenGetter = () => getToken();
      const res = await askFollowUp(workerId, q, tokenGetter);
      setTurns((prev) => [
        ...prev,
        { question: q, answer: res.answer, evidence: res.evidence ?? [] },
      ]);
      setQuestion("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, [question, workerId, enabled, getToken]);

  return (
    <SectionCard title="Follow-up Q&A">
      {!enabled ? (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Run a risk assessment to enable follow-up questions for this worker.
        </p>
      ) : (
        <>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="min-w-0 flex-1">
              <label
                htmlFor="followup-q"
                className="text-sm font-medium text-zinc-700 dark:text-zinc-300"
              >
                Question
              </label>
              <textarea
                id="followup-q"
                rows={2}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={loading}
                placeholder="Ask about this worker’s file, evidence, or risk posture…"
                className="mt-1.5 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm focus:border-zinc-500 focus:outline-none focus:ring-2 focus:ring-zinc-400/30 disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
              />
            </div>
            <button
              type="button"
              disabled={loading || !question.trim()}
              onClick={() => void submit()}
              className="inline-flex h-10 shrink-0 items-center justify-center rounded-lg bg-zinc-900 px-5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
            >
              {loading ? "Asking…" : "Ask"}
            </button>
          </div>
          {error ? (
            <p className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>
          ) : null}
          <div className="mt-6 space-y-4">
            {turns.map((t, i) => (
              <div
                key={`${i}-${t.question.slice(0, 24)}`}
                className="overflow-hidden rounded-lg border border-zinc-100 dark:border-zinc-800"
              >
                <p className="border-b border-zinc-100 bg-zinc-50 px-4 py-2 text-sm font-medium text-zinc-900 dark:border-zinc-800 dark:bg-zinc-900/60 dark:text-zinc-100">
                  {t.question}
                </p>
                <AskAnswerMarkdown content={t.answer} className="px-4 py-3" />
                {t.evidence.length ? (
                  <div className="border-t border-zinc-100 px-4 py-3 dark:border-zinc-800">
                    <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                      Citations
                    </p>
                    <ul className="mt-2 space-y-2">
                      {t.evidence.map((ev, j) => (
                        <li
                          key={`${ev.source}-${j}`}
                          className="rounded-md bg-zinc-50/80 p-2 text-xs dark:bg-zinc-900/40"
                        >
                          <span className="font-medium text-zinc-800 dark:text-zinc-200">
                            {ev.worker_id ? `${ev.worker_id} · ` : ""}
                            {ev.source}
                          </span>
                          <p className="mt-1 text-zinc-600 dark:text-zinc-400">{ev.content}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </>
      )}
    </SectionCard>
  );
}
