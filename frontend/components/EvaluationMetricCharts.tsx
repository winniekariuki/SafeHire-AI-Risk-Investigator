"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
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
