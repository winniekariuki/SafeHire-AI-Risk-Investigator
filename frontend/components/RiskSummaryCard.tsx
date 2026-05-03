import { SectionCard } from "@/components/SectionCard";
import type { RiskSummary } from "@/lib/types";

function bandClass(level: string): string {
  const key = level.trim().toLowerCase();
  if (key === "low")
    return "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30 dark:text-emerald-400";
  if (key === "medium" || key === "moderate")
    return "bg-amber-500/15 text-amber-800 ring-amber-500/30 dark:text-amber-300";
  if (key === "high" || key === "elevated")
    return "bg-red-500/15 text-red-800 ring-red-500/30 dark:text-red-300";
  return "bg-zinc-500/15 text-zinc-800 ring-zinc-500/30 dark:text-zinc-300";
}

export function RiskSummaryCard({ risk_summary }: { risk_summary: RiskSummary }) {
  const level = risk_summary.risk_level ?? "";
  return (
    <SectionCard title="Risk summary">
      <div className="flex flex-wrap items-baseline gap-3">
        <span className="text-4xl font-semibold tabular-nums text-zinc-950 dark:text-zinc-50">
          {risk_summary.score}
        </span>
        <span className="text-sm text-zinc-500 dark:text-zinc-400">
          composite score
        </span>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${bandClass(level)}`}
        >
          {level}
        </span>
        <span className="text-xs text-zinc-500 dark:text-zinc-400">
          Confidence:{" "}
          <span className="font-medium text-zinc-700 dark:text-zinc-300">
            {risk_summary.confidence}
          </span>
        </span>
      </div>
      <p className="mt-2 text-sm font-medium text-zinc-800 dark:text-zinc-200">
        {risk_summary.recommendation}
      </p>
      {risk_summary.reasons?.length ? (
        <ul className="mt-4 list-disc space-y-1.5 pl-4 text-sm text-zinc-600 dark:text-zinc-400">
          {risk_summary.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      ) : null}
    </SectionCard>
  );
}
