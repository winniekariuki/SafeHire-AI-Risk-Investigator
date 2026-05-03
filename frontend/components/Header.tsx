import type { ReactNode } from "react";

export function Header({
  eyebrow = "SafeHire · AI risk investigator",
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-10 flex flex-col gap-6 border-b border-zinc-200 pb-8 dark:border-zinc-800 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
          {eyebrow}
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
          {title}
        </h1>
        {description ? (
          <p className="mt-2 max-w-2xl text-base text-zinc-600 dark:text-zinc-400">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex shrink-0 items-center gap-3 self-start sm:self-auto">
          {actions}
        </div>
      ) : null}
    </header>
  );
}
