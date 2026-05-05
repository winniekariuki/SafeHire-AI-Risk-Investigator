"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type MetricRow = { metric: string; value: number };

function humanizeKey(key: string): string {
  return key
    .replace(/^mean_/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Build chart rows from aggregate dict (0–1 floats); skips null/undefined. */
export function aggregateToRows(
  agg: Record<string, number | null | undefined> | undefined,
): MetricRow[] {
  if (!agg) return [];
  return Object.entries(agg)
    .filter(([k, v]) => k !== "num_cases" && typeof v === "number" && !Number.isNaN(v))
    .map(([k, v]) => ({
      metric: humanizeKey(k),
      value: Math.min(1, Math.max(0, v as number)),
    }));
}

export function EvaluationMetricChart({
  title,
  data,
  emptyMessage,
}: {
  title: string;
  data: MetricRow[];
  emptyMessage?: string;
}) {
  if (data.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-zinc-50/80 p-6 dark:border-zinc-800 dark:bg-zinc-900/40">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{title}</h3>
        <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
          {emptyMessage ?? "No aggregate metrics to chart."}
        </p>
      </div>
    );
  }

  return (
    <div className="text-zinc-700 dark:text-zinc-300">
      <h3 className="mb-3 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
        {title}
      </h3>
      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 8, right: 24, left: 4, bottom: 8 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              className="stroke-zinc-200 dark:stroke-zinc-700"
              horizontal={false}
            />
            <XAxis
              type="number"
              domain={[0, 1]}
              tickFormatter={(v) => `${Math.round(Number(v) * 100)}%`}
              className="text-xs"
              stroke="currentColor"
            />
            <YAxis
              type="category"
              dataKey="metric"
              width={148}
              tick={{ fontSize: 11 }}
              stroke="currentColor"
            />
            <Tooltip
              formatter={(value) => [
                `${(Number(value ?? 0) * 100).toFixed(1)}%`,
                "Value",
              ]}
              contentStyle={{
                borderRadius: "8px",
                border: "1px solid rgb(228 228 231)",
                fontSize: "12px",
              }}
            />
            <Bar
              dataKey="value"
              fill="#3f3f46"
              radius={[0, 4, 4, 0]}
              maxBarSize={28}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/** One row per K cutoff; values are 0–1 for chart domain. */
export type RetrievalTrendRow = {
  k: string;
  Precision: number;
  Recall: number;
  MRR: number;
  nDCG: number;
  MAP: number;
  HitRate: number;
};

export function buildRetrievalTrendData(aggregate: {
  k_values?: number[];
  mean_precision_at_k?: Record<string, number>;
  mean_recall_at_k?: Record<string, number>;
  mean_mrr_at_k?: Record<string, number>;
  mean_ndcg_at_k?: Record<string, number>;
  mean_map_at_k?: Record<string, number>;
  mean_hit_rate_at_k?: Record<string, number>;
} | null | undefined): RetrievalTrendRow[] {
  if (!aggregate?.k_values?.length) return [];
  const sorted = [...aggregate.k_values].sort((a, b) => a - b);
  return sorted.map((kv) => {
    const ks = String(kv);
    const num = (rec: Record<string, number> | undefined) =>
      typeof rec?.[ks] === "number" && !Number.isNaN(rec[ks]) ? rec[ks] : 0;
    return {
      k: `@${ks}`,
      Precision: num(aggregate.mean_precision_at_k),
      Recall: num(aggregate.mean_recall_at_k),
      MRR: num(aggregate.mean_mrr_at_k),
      nDCG: num(aggregate.mean_ndcg_at_k),
      MAP: num(aggregate.mean_map_at_k),
      HitRate: num(aggregate.mean_hit_rate_at_k),
    };
  });
}

const TREND_COLORS = {
  Precision: "#6366f1",
  Recall: "#22c55e",
  MRR: "#f59e0b",
  nDCG: "#ec4899",
  MAP: "#06b6d4",
  HitRate: "#a855f7",
} as const;

/** Grouped bars: K on the X axis, one series per metric (mean aggregate). */
export function RetrievalMetricsTrendChart({
  title,
  data,
  emptyMessage,
}: {
  title: string;
  data: RetrievalTrendRow[];
  emptyMessage?: string;
}) {
  if (data.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-zinc-50/80 p-6 dark:border-zinc-800 dark:bg-zinc-900/40">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{title}</h3>
        <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
          {emptyMessage ?? "No retrieval aggregate metrics to chart."}
        </p>
      </div>
    );
  }

  return (
    <div className="text-zinc-700 dark:text-zinc-300">
      <h3 className="mb-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">{title}</h3>
      <p className="mb-3 text-xs text-zinc-500 dark:text-zinc-400">
        Mean metrics across benchmark cases by cutoff K (hover for exact %).
      </p>
      <div className="h-[360px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 8, right: 8, left: 4, bottom: 8 }}
            barCategoryGap="18%"
          >
            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              className="stroke-zinc-200 dark:stroke-zinc-700"
            />
            <XAxis
              dataKey="k"
              tick={{ fontSize: 11 }}
              stroke="currentColor"
              className="text-xs"
            />
            <YAxis
              domain={[0, 1]}
              tickFormatter={(v) => `${Math.round(Number(v) * 100)}%`}
              width={44}
              tick={{ fontSize: 11 }}
              stroke="currentColor"
            />
            <Tooltip
              formatter={(value) => `${(Number(value ?? 0) * 100).toFixed(1)}%`}
              contentStyle={{
                borderRadius: "8px",
                border: "1px solid rgb(228 228 231)",
                fontSize: "12px",
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: "11px" }}
              formatter={(value) => <span className="text-zinc-600 dark:text-zinc-400">{value}</span>}
            />
            <Bar dataKey="Precision" name="Precision" fill={TREND_COLORS.Precision} radius={[2, 2, 0, 0]} maxBarSize={14} />
            <Bar dataKey="Recall" name="Recall" fill={TREND_COLORS.Recall} radius={[2, 2, 0, 0]} maxBarSize={14} />
            <Bar dataKey="MRR" name="MRR" fill={TREND_COLORS.MRR} radius={[2, 2, 0, 0]} maxBarSize={14} />
            <Bar dataKey="nDCG" name="nDCG" fill={TREND_COLORS.nDCG} radius={[2, 2, 0, 0]} maxBarSize={14} />
            <Bar dataKey="MAP" name="MAP" fill={TREND_COLORS.MAP} radius={[2, 2, 0, 0]} maxBarSize={14} />
            <Bar dataKey="HitRate" name="Hit rate" fill={TREND_COLORS.HitRate} radius={[2, 2, 0, 0]} maxBarSize={14} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
