import type { RiskSummary } from "@/lib/types";

type BandKey = "low" | "medium" | "high" | "other";

function normalizeBand(level: string): BandKey {
  const k = level.trim().toLowerCase();
  if (k === "low") return "low";
  if (k === "medium" || k === "moderate") return "medium";
  if (k === "high" || k === "elevated") return "high";
  return "other";
}

const bandTheme: Record<
  BandKey,
  {
    accent: string;
    chip: string;
    meterFrom: string;
    meterTo: string;
    dot: string;
    glow: string;
  }
> = {
  low: {
    accent: "border-l-emerald-500",
    chip:
      "bg-emerald-500/15 text-emerald-800 ring-emerald-500/40 dark:text-emerald-300",
    meterFrom: "from-emerald-400",
    meterTo: "to-teal-500",
    dot: "bg-emerald-500",
    glow: "shadow-emerald-500/10",
  },
  medium: {
    accent: "border-l-amber-500",
    chip:
      "bg-amber-500/15 text-amber-900 ring-amber-500/40 dark:text-amber-200",
    meterFrom: "from-amber-400",
    meterTo: "to-orange-500",
    dot: "bg-amber-500",
    glow: "shadow-amber-500/10",
  },
  high: {
    accent: "border-l-red-500",
    chip: "bg-red-500/15 text-red-900 ring-red-500/40 dark:text-red-300",
    meterFrom: "from-red-400",
    meterTo: "to-rose-600",
    dot: "bg-red-500",
    glow: "shadow-red-500/12",
  },
  other: {
    accent: "border-l-zinc-400",
    chip:
      "bg-zinc-500/15 text-zinc-800 ring-zinc-500/35 dark:text-zinc-300",
    meterFrom: "from-zinc-400",
    meterTo: "to-zinc-600",
    dot: "bg-zinc-500",
    glow: "shadow-zinc-500/10",
  },
};

export function RiskSummaryCard({ risk_summary }: { risk_summary: RiskSummary }) {
  const levelLabel = risk_summary.risk_level ?? "";
  const band = normalizeBand(levelLabel);
  const t = bandTheme[band];
  const raw = Number(risk_summary.score);
  const score = Number.isFinite(raw)
    ? Math.min(100, Math.max(0, raw))
    : 0;
  const review = risk_summary.manual_review_required === true;

  return (
    <section
      className={`relative overflow-hidden rounded-2xl border border-zinc-200/90 bg-gradient-to-br from-white via-white to-zinc-50/90 shadow-lg shadow-zinc-900/5 ring-1 ring-zinc-900/5 dark:border-zinc-700/90 dark:from-zinc-950 dark:via-zinc-950 dark:to-zinc-900/80 dark:ring-white/5 ${t.glow}`}
    >
      <div className={`border-l-4 ${t.accent} px-5 pb-6 pt-5 sm:px-6`}>
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                Risk summary
              </h2>
              {review ? (
                <span className="inline-flex items-center rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-amber-900 ring-1 ring-amber-500/35 dark:text-amber-200">
                  Manual review
                </span>
              ) : null}
            </div>
            <div className="flex flex-wrap items-end gap-x-3 gap-y-1">
              <p className="text-5xl font-bold tabular-nums tracking-tight text-zinc-950 dark:text-zinc-50">
                {score}
              </p>
              <div className="pb-1.5">
                <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
                  out of 100
                </p>
                <p className="text-[11px] text-zinc-400 dark:text-zinc-500">
                  Composite rule-based score
                </p>
              </div>
            </div>
          </div>
          <div className="flex flex-col items-start gap-2 sm:items-end">
            <span
              className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ring-1 ring-inset ${t.chip}`}
            >
              {levelLabel || "—"}
            </span>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 sm:text-right">
              Confidence:{" "}
              <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                {risk_summary.confidence}
              </span>
            </p>
          </div>
        </div>

        <div className="mt-5 space-y-2">
          <div className="flex items-center justify-between text-[11px] font-medium uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
            <span>Lower risk</span>
            <span>Higher risk</span>
          </div>
          <div
            className="relative h-3 overflow-hidden rounded-full bg-zinc-200/90 dark:bg-zinc-800/90"
            role="meter"
            aria-valuenow={score}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Composite risk score out of 100"
          >
            <div
              className={`h-full rounded-full bg-gradient-to-r ${t.meterFrom} ${t.meterTo} transition-[width] duration-500 ease-out`}
              style={{ width: `${score}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] tabular-nums text-zinc-400 dark:text-zinc-500">
            <span>0</span>
            <span>30</span>
            <span>65</span>
            <span>100</span>
          </div>
        </div>

        <div className="mt-6 rounded-xl border border-zinc-200/80 bg-zinc-50/90 px-4 py-3 dark:border-zinc-700/80 dark:bg-zinc-900/60">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            Recommendation
          </p>
          <p className="mt-1.5 text-sm font-medium leading-relaxed text-zinc-900 dark:text-zinc-100">
            {risk_summary.recommendation}
          </p>
        </div>

        {risk_summary.reasons?.length ? (
          <div className="mt-5">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              Key drivers
            </p>
            <ul className="mt-3 space-y-2.5">
              {risk_summary.reasons.map((r) => (
                <li key={r} className="flex gap-3 text-sm leading-snug text-zinc-700 dark:text-zinc-300">
                  <span
                    className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${t.dot}`}
                    aria-hidden
                  />
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </section>
  );
}
