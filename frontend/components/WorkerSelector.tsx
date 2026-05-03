import type { WorkerOption } from "@/lib/types";

export function WorkerSelector({
  workers,
  value,
  onChange,
  disabled,
}: {
  workers: WorkerOption[];
  value: string;
  onChange: (workerId: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor="worker"
        className="text-sm font-medium text-zinc-700 dark:text-zinc-300"
      >
        Worker
      </label>
      <select
        id="worker"
        value={value}
        disabled={disabled || workers.length === 0}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 min-w-[240px] rounded-lg border border-zinc-300 bg-white px-3 text-sm text-zinc-900 shadow-sm focus:border-zinc-500 focus:outline-none focus:ring-2 focus:ring-zinc-400/30 disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
      >
        {workers.length === 0 ? (
          <option value="">No workers loaded</option>
        ) : (
          workers.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name} — {w.role}
            </option>
          ))
        )}
      </select>
    </div>
  );
}
