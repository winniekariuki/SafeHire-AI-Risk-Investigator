import type { ReactNode } from "react";

/** Normalize API lists — backend sends string[] but guards against null/odd payloads. */
export function normalizeInsightList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((x) => (x === null || x === undefined ? "" : String(x).trim()))
    .filter(Boolean);
}

function SparkIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M10 2a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 2zM10 15a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 15zM3.182 5.182a.75.75 0 011.06 0l1.06 1.061a.75.75 0 01-1.06 1.06l-1.06-1.06a.75.75 0 010-1.061zM14.718 14.718a.75.75 0 011.06 0l1.061 1.06a.75.75 0 11-1.06 1.061l-1.061-1.06a.75.75 0 010-1.06zM2 10a.75.75 0 01.75-.75h1.5a.75.75 0 010 1.5h-1.5A.75.75 0 012 10zM15.25 9.25a.75.75 0 010 1.5h1.5a.75.75 0 000-1.5h-1.5zM4.243 14.718a.75.75 0 010-1.06l1.06-1.061a.75.75 0 111.061 1.06l-1.06 1.061a.75.75 0 01-1.06 0zM14.657 5.182a.75.75 0 010 1.06l-1.06 1.06a.75.75 0 11-1.06-1.06l1.06-1.06a.75.75 0 011.06 0z" />
    </svg>
  );
}

function AlertIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm1 6.25a1 1 0 11-2 0 1 1 0 012 0z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function ClipboardIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden
    >
      <path
        fillRule="evenodd"
        d="M4.5 2A1.5 1.5 0 003 3.5v17A1.5 1.5 0 004.5 22h15a1.5 1.5 0 001.5-1.5v-17A1.5 1.5 0 0019.5 2h-15zm4.25 5.5a.75.75 0 010 1.5h-2.5a.75.75 0 010-1.5h2.5zm3.5 0a.75.75 0 010 1.5h-1.5a.75.75 0 010-1.5h1.5zm3.5 0a.75.75 0 010 1.5h-1.5a.75.75 0 010-1.5h1.5zm-7 3a.75.75 0 010 1.5h-2.5a.75.75 0 010-1.5h2.5zm3.5 0a.75.75 0 010 1.5h-1.5a.75.75 0 010-1.5h1.5zm3.5 0a.75.75 0 010 1.5h-1.5a.75.75 0 010-1.5h1.5zm-7 3a.75.75 0 010 1.5h-2.5a.75.75 0 010-1.5h2.5zm3.5 0a.75.75 0 010 1.5h-1.5a.75.75 0 010-1.5h1.5zm3.5 0a.75.75 0 010 1.5h-1.5a.75.75 0 010-1.5h1.5z"
        clipRule="evenodd"
      />
    </svg>
  );
}

type Variant = "strengths" | "concerns" | "missing";

const VARIANTS: Record<
  Variant,
  {
    title: string;
    subtitle: string;
    emptyHint: string;
    icon: (p: { className?: string }) => ReactNode;
    shell: string;
    titleBar: string;
    iconWrap: string;
    itemRow: string;
    bullet: string;
  }
> = {
  strengths: {
    title: "Strengths",
    subtitle: "Positive signals grounded in retrieved evidence",
    emptyHint: "No strengths were extracted for this worker from the current evidence set.",
    icon: SparkIcon,
    shell:
      "border-emerald-200/90 bg-gradient-to-br from-emerald-50/95 via-white to-white shadow-emerald-900/5 ring-emerald-500/10 dark:border-emerald-900/40 dark:from-emerald-950/40 dark:via-zinc-950 dark:to-zinc-950 dark:ring-emerald-500/15",
    titleBar:
      "border-emerald-100/90 bg-emerald-500/10 dark:border-emerald-900/50 dark:bg-emerald-950/50",
    iconWrap:
      "bg-emerald-500/20 text-emerald-700 dark:bg-emerald-500/25 dark:text-emerald-300",
    itemRow:
      "border-emerald-100/80 bg-white/90 dark:border-emerald-900/40 dark:bg-emerald-950/20",
    bullet: "bg-emerald-500 dark:bg-emerald-400",
  },
  concerns: {
    title: "Concerns",
    subtitle: "Risk-relevant findings from evidence — not final judgments",
    emptyHint: "No concern phrases were flagged from the evidence for this assessment.",
    icon: AlertIcon,
    shell:
      "border-amber-200/90 bg-gradient-to-br from-amber-50/95 via-white to-white shadow-amber-900/5 ring-amber-500/10 dark:border-amber-900/40 dark:from-amber-950/35 dark:via-zinc-950 dark:to-zinc-950 dark:ring-amber-500/15",
    titleBar:
      "border-amber-100/90 bg-amber-500/10 dark:border-amber-900/50 dark:bg-amber-950/50",
    iconWrap:
      "bg-amber-500/20 text-amber-800 dark:bg-amber-500/25 dark:text-amber-200",
    itemRow:
      "border-amber-100/80 bg-white/90 dark:border-amber-900/40 dark:bg-amber-950/20",
    bullet: "bg-amber-500 dark:bg-amber-400",
  },
  missing: {
    title: "Missing information",
    subtitle: "Gaps that limit confidence — from verification & sufficiency checks",
    emptyHint:
      "Nothing flagged as missing for this run; file still may benefit from updates.",
    icon: ClipboardIcon,
    shell:
      "border-violet-200/90 bg-gradient-to-br from-violet-50/90 via-white to-cyan-50/40 shadow-violet-900/5 ring-violet-500/10 dark:border-violet-900/40 dark:from-violet-950/35 dark:via-zinc-950 dark:to-zinc-950 dark:ring-violet-500/15",
    titleBar:
      "border-violet-100/90 bg-violet-500/10 dark:border-violet-900/50 dark:bg-violet-950/45",
    iconWrap:
      "bg-violet-500/20 text-violet-800 dark:bg-violet-500/25 dark:text-violet-200",
    itemRow:
      "border-violet-100/80 bg-white/90 dark:border-violet-900/40 dark:bg-violet-950/25",
    bullet: "bg-violet-500 dark:bg-violet-400",
  },
};

function InsightColumnCard({
  variant,
  items,
}: {
  variant: Variant;
  items: string[];
}) {
  const cfg = VARIANTS[variant];
  const Icon = cfg.icon;
  const count = items.length;

  return (
    <section
      className={`flex flex-col overflow-hidden rounded-2xl border shadow-lg ring-1 ${cfg.shell}`}
    >
      <div className={`flex items-start gap-3 border-b px-4 py-3 sm:px-5 ${cfg.titleBar}`}>
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${cfg.iconWrap}`}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-2">
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              {cfg.title}
            </h2>
            <span className="rounded-full bg-black/5 px-2 py-0.5 text-[11px] font-semibold tabular-nums text-zinc-600 ring-1 ring-black/5 dark:bg-white/10 dark:text-zinc-400 dark:ring-white/10">
              {count}
            </span>
          </div>
          <p className="mt-0.5 text-xs leading-snug text-zinc-600 dark:text-zinc-400">
            {cfg.subtitle}
          </p>
        </div>
      </div>

      <div className="flex flex-1 flex-col px-4 py-4 sm:px-5">
        {count === 0 ? (
          <p className="text-sm italic leading-relaxed text-zinc-500 dark:text-zinc-400">
            {cfg.emptyHint}
          </p>
        ) : (
          <ul className="space-y-2.5">
            {items.map((item, i) => (
              <li key={`${variant}-${i}-${item.slice(0, 48)}`}>
                <div
                  className={`flex gap-3 rounded-xl border px-3 py-2.5 text-sm leading-snug text-zinc-800 dark:border-zinc-700/80 dark:text-zinc-200 ${cfg.itemRow}`}
                >
                  <span
                    className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${cfg.bullet}`}
                    aria-hidden
                  />
                  <span>{item}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

/**
 * Three-column assessment insights: strengths (signals), concerns (signals), missing (sufficiency).
 * Pass through API fields explicitly — do not swap or merge with ``risk_signals``.
 */
export function AssessmentInsightCards({
  strengths,
  concerns,
  missing_information,
}: {
  strengths: unknown;
  concerns: unknown;
  missing_information: unknown;
}) {
  const s = normalizeInsightList(strengths);
  const c = normalizeInsightList(concerns);
  const m = normalizeInsightList(missing_information);

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <InsightColumnCard variant="strengths" items={s} />
      <InsightColumnCard variant="concerns" items={c} />
      <InsightColumnCard variant="missing" items={m} />
    </div>
  );
}
