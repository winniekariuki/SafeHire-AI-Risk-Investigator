"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback, useState } from "react";
import { SectionCard } from "@/components/SectionCard";
import { askFollowUp } from "@/lib/api";

type Turn = {
  question: string;
  answer: string;
  evidence: { worker_id?: string | null; source: string; content: string }[];
};

export function PlatformAsk() {
  const { getToken } = useAuth();
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    const q = question.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    try {
      const tokenGetter = () => getToken();
      const res = await askFollowUp(null, q, tokenGetter);
      setTurns((prev) => [
        ...prev,
        {
          question: q,
          answer: res.answer,
          evidence: res.evidence ?? [],
        },
      ]);
      setQuestion("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, [question, getToken]);

  return (
    <SectionCard title="Ask across all workers">
      <p className="mb-3 text-sm text-zinc-600 dark:text-zinc-400">
        Platform RAG searches every indexed profile (and seeded CSV fallbacks). Example:{" "}
        <span className="italic">
          Which worker is good with children?
        </span>
      </p>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="min-w-0 flex-1">
          <label
            htmlFor="platform-q"
            className="text-sm font-medium text-zinc-700 dark:text-zinc-300"
          >
            Question
          </label>
          <textarea
            id="platform-q"
            rows={2}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
            placeholder="e.g. Who has the strongest references for childcare?"
            className="mt-1.5 w-full rounded-lg border border-zinc-300/80 bg-white/90 px-3 py-2 text-sm text-zinc-900 shadow-sm backdrop-blur-sm focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-400/30 disabled:opacity-60 dark:border-zinc-600 dark:bg-zinc-900/80 dark:text-zinc-100"
          />
        </div>
        <button
          type="button"
          disabled={loading || !question.trim()}
          onClick={() => void submit()}
          className="inline-flex h-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 px-5 text-sm font-medium text-white shadow-md transition hover:from-violet-500 hover:to-fuchsia-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Searching…" : "Ask platform"}
        </button>
      </div>
      {error ? (
        <p className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>
      ) : null}
      <div className="mt-6 space-y-4">
        {turns.map((t, i) => (
          <div
            key={`${i}-${t.question.slice(0, 24)}`}
            className="overflow-hidden rounded-xl border border-white/60 bg-white/70 shadow-sm backdrop-blur-md dark:border-zinc-700/60 dark:bg-zinc-900/70"
          >
            <p className="border-b border-zinc-100/80 bg-gradient-to-r from-violet-50/90 to-cyan-50/50 px-4 py-2 text-sm font-medium text-zinc-900 dark:border-zinc-800 dark:from-violet-950/40 dark:to-zinc-900/60 dark:text-zinc-100">
              {t.question}
            </p>
            <p className="px-4 py-3 text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
              {t.answer}
            </p>
            {t.evidence.length ? (
              <div className="border-t border-zinc-100/80 px-4 py-3 dark:border-zinc-800">
                <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                  Citations
                </p>
                <ul className="mt-2 space-y-2">
                  {t.evidence.map((ev, j) => (
                    <li
                      key={`${ev.source}-${j}`}
                      className="rounded-md bg-zinc-50/90 p-2 text-xs dark:bg-zinc-950/50"
                    >
                      <span className="font-medium text-violet-800 dark:text-violet-300">
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
    </SectionCard>
  );
}
