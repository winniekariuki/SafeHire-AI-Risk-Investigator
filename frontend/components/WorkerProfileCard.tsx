import { SectionCard } from "@/components/SectionCard";

const PREFERRED_ORDER = [
  "worker_id",
  "name",
  "county",
  "years_experience",
  "id_verified",
  "phone_verified",
  "references_completed",
  "misconduct_reports",
];

function formatLabel(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export function WorkerProfileCard({ worker }: { worker: Record<string, unknown> }) {
  const keys = Object.keys(worker);
  const ordered = [
    ...PREFERRED_ORDER.filter((k) => keys.includes(k)),
    ...keys.filter((k) => !PREFERRED_ORDER.includes(k)).sort(),
  ];

  return (
    <SectionCard title="Worker profile">
      <dl className="grid gap-3 sm:grid-cols-2">
        {ordered.map((key) => (
          <div key={key}>
            <dt className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              {formatLabel(key)}
            </dt>
            <dd className="mt-0.5 text-sm text-zinc-900 dark:text-zinc-100">
              {formatValue(worker[key])}
            </dd>
          </div>
        ))}
      </dl>
    </SectionCard>
  );
}
