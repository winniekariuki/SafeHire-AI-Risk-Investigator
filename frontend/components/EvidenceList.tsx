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
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          No vector-retrieved chunks for this query (index worker data or widen retrieval).
        </p>
      ) : (
        <ul className="space-y-4">
          {retrieved_evidence.map((ev, i) => {
            const title =
              ev.source ||
              ev.metadata?.source_file ||
              ev.metadata?.risk_area ||
              `Evidence ${i + 1}`;
            const metaBits = [
              ev.metadata?.risk_area,
              ev.worker_id && ev.worker_id !== title ? ev.worker_id : null,
            ].filter(Boolean);
            return (
              <li
                key={`${title}-${i}`}
                className="rounded-lg border border-zinc-100 bg-zinc-50/80 p-4 dark:border-zinc-800 dark:bg-zinc-900/40"
              >
                <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  {title}
                </p>
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
