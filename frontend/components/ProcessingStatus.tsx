import { SectionCard } from "@/components/SectionCard";

export type PipelineStep = { id: string; label: string; done: boolean };

export const DEFAULT_PIPELINE_STEPS: Omit<PipelineStep, "done">[] = [
  { id: "load", label: "Load worker context & consent" },
  { id: "retrieve", label: "Retrieve references & policy evidence" },
  { id: "signals", label: "Extract risk signals" },
  { id: "score", label: "Score risk & sufficiency" },
  { id: "report", label: "Generate report & follow-ups" },
];

export function ProcessingStatus({
  steps,
  isRunning,
}: {
  steps: PipelineStep[];
  isRunning: boolean;
}) {
  return (
    <SectionCard title="Processing status">
      <ul className="space-y-2">
        {steps.map((step) => (
          <li
            key={step.id}
            className="flex items-center gap-3 text-sm text-zinc-700 dark:text-zinc-300"
          >
            <span
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                step.done
                  ? "bg-emerald-500/20 text-emerald-700 dark:text-emerald-400"
                  : isRunning
                    ? "animate-pulse bg-zinc-200 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
                    : "bg-zinc-100 text-zinc-400 dark:bg-zinc-900 dark:text-zinc-500"
              }`}
              aria-hidden
            >
              {step.done ? "✓" : "…"}
            </span>
            <span>{step.label}</span>
          </li>
        ))}
      </ul>
      {isRunning ? (
        <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
          Calling the investigation pipeline on the API; steps reflect orchestration
          stages.
        </p>
      ) : null}
    </SectionCard>
  );
}
