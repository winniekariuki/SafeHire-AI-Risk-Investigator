import type { ReactNode } from "react";

function str(v: unknown): string {
  if (v === null || v === undefined) return "";
  return String(v);
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return (parts[0]![0]! + parts[parts.length - 1]![0]!).toUpperCase();
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden
    >
      <path
        fillRule="evenodd"
        d="M16.704 4.153a.75.75 0 01.143 1.052l-7.5 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 6.95-9.73a.75.75 0 011.05-.143z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden
    >
      <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
    </svg>
  );
}

function PinIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden
    >
      <path
        fillRule="evenodd"
        d="M9.69 1.2a.75.75 0 01.62 0l7.5 3.6a.75.75 0 01-.04 1.38L12.5 7.88V12a.75.75 0 01-.4.66l-3 1.5a.75.75 0 01-.8-.12L6.5 12.5l-2.3 1.8a.75.75 0 01-1.18-.45V9.64L1.45 6.3a.75.75 0 01.04-1.38l7.5-3.6a.75.75 0 01.2-.1zM10 2.55L3.5 5.65l2.2 2.5a.75.75 0 01.2.48v3.3l1.1-.86a.75.75 0 01.8 0L11 12.2V7.88a.75.75 0 01.2-.48l2.2-2.5L10 2.55z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function StatBox({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "neutral" | "amber" | "emerald";
}) {
  const tones = {
    neutral:
      "border-zinc-200/90 bg-white/80 dark:border-zinc-700/90 dark:bg-zinc-900/50",
    amber:
      "border-amber-200/90 bg-amber-50/90 dark:border-amber-900/50 dark:bg-amber-950/30",
    emerald:
      "border-emerald-200/90 bg-emerald-50/80 dark:border-emerald-900/50 dark:bg-emerald-950/30",
  };

  return (
    <div
      className={`rounded-xl border px-4 py-3 ${tones[tone]}`}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
        {label}
      </p>
      <p className="mt-1 text-lg font-semibold tabular-nums text-zinc-900 dark:text-zinc-100">
        {value}
      </p>
      {hint ? (
        <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{hint}</p>
      ) : null}
    </div>
  );
}

function boolFlag(v: unknown): boolean | null {
  if (v === true || v === false) return v;
  if (typeof v === "string") {
    const s = v.trim().toLowerCase();
    if (s === "true" || s === "1" || s === "yes") return true;
    if (s === "false" || s === "0" || s === "no") return false;
  }
  return null;
}

const LABELS: Record<string, string> = {
  worker_id: "Worker ID",
  name: "Name",
  county: "County / region",
  years_experience: "Experience",
  id_verified: "ID verified",
  phone_verified: "Phone verified",
  references_completed: "Reference records",
  misconduct_reports: "Misconduct reports",
};

function formatLabel(key: string): string {
  return LABELS[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (key === "years_experience") {
    const n = Number(value);
    if (Number.isFinite(n)) return `${n} year${n === 1 ? "" : "s"}`;
  }
  return String(value);
}

export function WorkerProfileCard({ worker }: { worker: Record<string, unknown> }) {
  const name = str(worker.name) || "Worker";
  const wid = str(worker.worker_id) || "—";
  const county = str(worker.county);
  const years = worker.years_experience;
  const yearsNum = Number(years);
  const yearsLabel = Number.isFinite(yearsNum)
    ? `${yearsNum} year${yearsNum === 1 ? "" : "s"}`
    : formatValue("years_experience", years);

  const idOk = boolFlag(worker.id_verified);
  const phoneOk = boolFlag(worker.phone_verified);

  const refCount = worker.references_completed;
  const misCount = worker.misconduct_reports;
  const refN =
    typeof refCount === "number"
      ? refCount
      : Number.parseInt(String(refCount ?? ""), 10);
  const misN =
    typeof misCount === "number"
      ? misCount
      : Number.parseInt(String(misCount ?? ""), 10);

  const displayedKeys = new Set([
    "name",
    "worker_id",
    "county",
    "years_experience",
    "id_verified",
    "phone_verified",
    "references_completed",
    "misconduct_reports",
  ]);

  const extraKeys = Object.keys(worker)
    .filter((k) => !displayedKeys.has(k))
    .sort();

  return (
    <section className="overflow-hidden rounded-2xl border border-zinc-200/90 bg-gradient-to-br from-white via-violet-50/30 to-cyan-50/20 shadow-lg shadow-zinc-900/5 ring-1 ring-zinc-900/5 dark:border-zinc-700/90 dark:from-zinc-950 dark:via-violet-950/20 dark:to-zinc-900/80 dark:ring-white/5">
      <div className="border-b border-zinc-200/80 bg-white/50 px-5 py-4 dark:border-zinc-800/80 dark:bg-zinc-900/40 sm:px-6">
        <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
          Worker profile
        </p>
        <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-start">
          <div
            className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-600 text-lg font-bold text-white shadow-md shadow-violet-500/25"
            aria-hidden
          >
            {initials(name)}
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {name}
            </h3>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center rounded-lg bg-zinc-900/5 px-2.5 py-1 font-mono text-xs font-medium text-zinc-800 ring-1 ring-zinc-900/10 dark:bg-white/5 dark:text-zinc-200 dark:ring-white/10">
                {wid}
              </span>
              {county ? (
                <span className="inline-flex items-center gap-1.5 text-sm text-zinc-600 dark:text-zinc-300">
                  <PinIcon className="h-4 w-4 shrink-0 text-violet-500 dark:text-violet-400" />
                  {county}
                </span>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-5 px-5 py-5 sm:px-6">
        <div className="grid gap-3 sm:grid-cols-3">
          <StatBox
            label="Experience"
            value={yearsLabel}
            hint="Reported tenure"
          />
          <StatBox
            label="Reference records"
            value={Number.isFinite(refN) ? refN : "—"}
            hint="In structured file"
            tone="emerald"
          />
          <StatBox
            label="Misconduct reports"
            value={Number.isFinite(misN) ? misN : "—"}
            hint={
              Number.isFinite(misN) && misN > 0
                ? "Review details below"
                : "None on file"
            }
            tone={
              Number.isFinite(misN) && misN > 0 ? "amber" : "neutral"
            }
          />
        </div>

        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            Verification status
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div className="flex items-center justify-between gap-3 rounded-xl border border-zinc-200/90 bg-white/90 px-4 py-3 dark:border-zinc-700/90 dark:bg-zinc-900/60">
              <span className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
                Government ID
              </span>
              {idOk === null ? (
                <span className="text-sm text-zinc-400">—</span>
              ) : idOk ? (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs font-semibold text-emerald-800 ring-1 ring-emerald-500/30 dark:text-emerald-300">
                  <CheckIcon className="h-4 w-4" /> Verified
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-zinc-500/15 px-2.5 py-1 text-xs font-semibold text-zinc-700 ring-1 ring-zinc-500/25 dark:text-zinc-300">
                  <XIcon className="h-4 w-4" /> Not verified
                </span>
              )}
            </div>
            <div className="flex items-center justify-between gap-3 rounded-xl border border-zinc-200/90 bg-white/90 px-4 py-3 dark:border-zinc-700/90 dark:bg-zinc-900/60">
              <span className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
                Phone number
              </span>
              {phoneOk === null ? (
                <span className="text-sm text-zinc-400">—</span>
              ) : phoneOk ? (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs font-semibold text-emerald-800 ring-1 ring-emerald-500/30 dark:text-emerald-300">
                  <CheckIcon className="h-4 w-4" /> Verified
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-zinc-500/15 px-2.5 py-1 text-xs font-semibold text-zinc-700 ring-1 ring-zinc-500/25 dark:text-zinc-300">
                  <XIcon className="h-4 w-4" /> Not verified
                </span>
              )}
            </div>
          </div>
        </div>

        {extraKeys.length > 0 ? (
          <div className="border-t border-zinc-200/80 pt-5 dark:border-zinc-800/80">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              Additional fields
            </p>
            <dl className="mt-3 grid gap-3 sm:grid-cols-2">
              {extraKeys.map((key) => (
                <div key={key}>
                  <dt className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
                    {formatLabel(key)}
                  </dt>
                  <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
                    {formatValue(key, worker[key])}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        ) : null}
      </div>
    </section>
  );
}
