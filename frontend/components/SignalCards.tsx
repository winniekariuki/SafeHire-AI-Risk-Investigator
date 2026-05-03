"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { SectionCard } from "@/components/SectionCard";

function humanizeCode(code: string): string {
  return code
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const chipBase =
  "inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset";

function MetricChip({ label }: { label: string }) {
  return (
    <span
      className={`${chipBase} bg-zinc-500/10 text-zinc-800 ring-zinc-500/20 dark:text-zinc-300`}
    >
      {label}
    </span>
  );
}

function CodeChip({ code, tone }: { code: string; tone: "pos" | "risk" }) {
  const styles =
    tone === "pos"
      ? "bg-emerald-500/10 text-emerald-800 ring-emerald-500/25 dark:text-emerald-300"
      : "bg-orange-500/10 text-orange-900 ring-orange-500/25 dark:text-orange-200";
  return (
    <span className={`${chipBase} ${styles}`} title={code}>
      {humanizeCode(code)}
    </span>
  );
}

/** Low / medium / high → 0–100 scale for bar length */
function ordinalToPercent(raw: unknown): number | null {
  const v = String(raw ?? "")
    .trim()
    .toLowerCase();
  if (v === "low") return 33;
  if (v === "medium") return 66;
  if (v === "high") return 100;
  return null;
}

function severityBarColor(level: string): string {
  if (level === "low") return "#22c55e";
  if (level === "medium") return "#f59e0b";
  if (level === "high") return "#dc2626";
  return "#71717a";
}

/** Higher evidence strength is better → invert greens vs ambers */
function evidenceBarColor(level: string): string {
  if (level === "high") return "#22c55e";
  if (level === "medium") return "#f59e0b";
  if (level === "low") return "#ea580c";
  return "#71717a";
}

type OverviewRow = {
  name: string;
  value: number;
  level: string;
  fill: string;
  kind: "severity" | "evidence";
};

function SignalOverviewGraphs({
  severity,
  evidenceStrength,
}: {
  severity: unknown;
  evidenceStrength: unknown;
}) {
  const rows: OverviewRow[] = [];

  if (severity != null) {
    const pct = ordinalToPercent(severity);
    const level = String(severity).trim().toLowerCase();
    if (pct != null) {
      rows.push({
        name: "Severity",
        value: pct,
        level,
        fill: severityBarColor(level),
        kind: "severity",
      });
    }
  }

  if (evidenceStrength != null) {
    const pct = ordinalToPercent(evidenceStrength);
    const level = String(evidenceStrength).trim().toLowerCase();
    if (pct != null) {
      rows.push({
        name: "Evidence strength",
        value: pct,
        level,
        fill: evidenceBarColor(level),
        kind: "evidence",
      });
    }
  }

  if (rows.length === 0) {
    return (
      <p className="mt-4 text-xs text-zinc-500 dark:text-zinc-400">
        Chart supports severity and evidence strength when values are low, medium, or high.
      </p>
    );
  }

  return (
    <div className="mt-5 h-[132px] w-full text-zinc-700 dark:text-zinc-300">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 4, right: 16, left: 4, bottom: 4 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            horizontal={false}
            className="stroke-zinc-200 dark:stroke-zinc-700"
          />
          <XAxis
            type="number"
            domain={[0, 100]}
            tickFormatter={(n) => `${n}%`}
            tick={{ fontSize: 11 }}
            stroke="currentColor"
          />
          <YAxis
            type="category"
            dataKey="name"
            width={124}
            tick={{ fontSize: 11 }}
            stroke="currentColor"
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const row = payload[0].payload as OverviewRow;
              return (
                <div className="rounded-md border border-zinc-200 bg-white px-2 py-1.5 text-xs shadow-sm dark:border-zinc-700 dark:bg-zinc-950">
                  <p className="font-medium text-zinc-900 dark:text-zinc-100">
                    {row.name}
                  </p>
                  <p className="text-zinc-600 dark:text-zinc-400">
                    {row.value}% — {humanizeCode(row.level)}
                  </p>
                </div>
              );
            }}
          />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} maxBarSize={22}>
            {rows.map((r) => (
              <Cell key={`${r.kind}-${r.name}`} fill={r.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="mt-2 text-[11px] leading-snug text-zinc-500 dark:text-zinc-400">
        Scale: Low → 33%, Medium → 66%, High → 100%. Severity: higher is riskier.
        Evidence strength: higher is stronger evidence.
      </p>
    </div>
  );
}

function NarrativeList({
  title,
  items,
}: {
  title: string;
  items: string[];
}) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
        {title}
      </p>
      {items.length === 0 ? (
        <p className="mt-2 text-sm italic text-zinc-500 dark:text-zinc-400">None</p>
      ) : (
        <ul className="mt-2 list-disc space-y-1.5 pl-4 text-sm text-zinc-700 dark:text-zinc-300">
          {items.map((line, i) => (
            <li key={`${i}-${line.slice(0, 48)}`}>{line}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function SignalCards({ risk_signals }: { risk_signals: Record<string, unknown> }) {
  const severity = risk_signals.severity;
  const evidenceStrength = risk_signals.evidence_strength;
  const positive = Array.isArray(risk_signals.positive_signals)
    ? (risk_signals.positive_signals as string[])
    : [];
  const risks = Array.isArray(risk_signals.risk_signals)
    ? (risk_signals.risk_signals as string[])
    : [];
  const strengths = Array.isArray(risk_signals.strengths)
    ? (risk_signals.strengths as string[])
    : [];
  const concerns = Array.isArray(risk_signals.concerns)
    ? (risk_signals.concerns as string[])
    : [];

  const hasOverviewMeta = severity != null || evidenceStrength != null;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <SectionCard title="Signal overview">
        <div className="flex flex-wrap gap-2">
          {severity != null ? (
            <MetricChip label={`Severity: ${String(severity)}`} />
          ) : null}
          {evidenceStrength != null ? (
            <MetricChip label={`Evidence strength: ${String(evidenceStrength)}`} />
          ) : null}
        </div>
        {hasOverviewMeta ? (
          <SignalOverviewGraphs
            severity={severity}
            evidenceStrength={evidenceStrength}
          />
        ) : (
          <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-400">
            No severity metadata on this run.
          </p>
        )}
      </SectionCard>
      <SectionCard title="Structured signals">
        <div className="space-y-5">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              Positive signals
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {positive.length ? (
                positive.map((s) => <CodeChip key={s} code={s} tone="pos" />)
              ) : (
                <span className="text-sm italic text-zinc-500 dark:text-zinc-400">
                  None
                </span>
              )}
            </div>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              Risk signals
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {risks.length ? (
                risks.map((s) => <CodeChip key={s} code={s} tone="risk" />)
              ) : (
                <span className="text-sm italic text-zinc-500 dark:text-zinc-400">
                  None
                </span>
              )}
            </div>
          </div>
          <NarrativeList title="Strengths (from signals)" items={strengths} />
          <NarrativeList title="Concerns (from signals)" items={concerns} />
        </div>
      </SectionCard>
    </div>
  );
}
