import { SectionCard } from "@/components/SectionCard";
import type { RetrievedEvidenceItem } from "@/lib/types";

export function EvidenceList({
  retrieved_evidence,
}: {
  retrieved_evidence: RetrievedEvidenceItem[];
}) {
  return (
    <SectionCard title="Retrieved evidence">
      {retrieved_evidence.length === 0 ? (
        <div className="rounded-lg border border-dashed border-zinc-200 bg-zinc-50/80 px-4 py-5 dark:border-zinc-700 dark:bg-zinc-900/40">
          <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
            No evidence text to show yet
          </p>
          <p className="mt-2 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
            There are no searchable documents in your database for this worker, and no
            reference or misconduct rows on file. Ingest documents into Supabase
            (see project ingest script) or add records to your worker files, then run
            the assessment again.
          </p>
        </div>
      ) : (
        <ul className="space-y-4">
          {retrieved_evidence.map((ev, i) => {
            const title =
              ev.source ||
              ev.metadata?.source_file ||
              ev.metadata?.risk_area ||
              `Evidence ${i + 1}`;
            const origin = ev.metadata?.origin;
            const fromStructured =
              origin === "structured_reference" ||
              origin === "structured_misconduct";
            const metaBits = [
              ev.metadata?.risk_area,
              ev.worker_id && ev.worker_id !== title ? ev.worker_id : null,
            ].filter(Boolean);
            return (
              <li
                key={`${title}-${i}`}
                className="rounded-lg border border-zinc-100 bg-zinc-50/80 p-4 dark:border-zinc-800 dark:bg-zinc-900/40"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                    {title}
                  </p>
                  {fromStructured ? (
                    <span className="rounded-full bg-violet-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-violet-800 ring-1 ring-violet-500/25 dark:text-violet-200">
                      From records
                    </span>
                  ) : null}
                </div>
                {metaBits.length ? (
                  <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                    {metaBits.join(" · ")}
                  </p>
                ) : null}
                <p className="mt-2 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
                  {ev.content ?? ""}
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </SectionCard>
  );
}
