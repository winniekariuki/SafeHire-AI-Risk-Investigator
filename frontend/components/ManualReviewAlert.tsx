import { SectionCard } from "@/components/SectionCard";

export function ManualReviewAlert() {
  return (
    <SectionCard title="Manual review required">
      <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 ring-1 ring-amber-500/20 dark:bg-amber-500/5">
        <p className="text-sm font-medium text-amber-950 dark:text-amber-100">
          Automated confidence or sufficiency checks flagged this file for human review.
        </p>
        <p className="mt-2 text-sm leading-relaxed text-amber-900/90 dark:text-amber-200/90">
          Have a reviewer validate evidence spans, adjudicate flags, and record an explicit
          decision before hire.
        </p>
      </div>
    </SectionCard>
  );
}
