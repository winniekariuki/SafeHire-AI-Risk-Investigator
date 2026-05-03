"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/dashboard", label: "Investigation" },
  { href: "/dashboard/evaluation", label: "Evaluation" },
] as const;

export function DashboardNav() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-wrap gap-2 sm:gap-8" aria-label="Dashboard sections">
      {tabs.map(({ href, label }) => {
        const active =
          href === "/dashboard"
            ? pathname === "/dashboard" || pathname === "/dashboard/"
            : Boolean(pathname?.startsWith(href));
        return (
          <Link
            key={href}
            href={href}
            className={`border-b-2 pb-2 text-sm font-medium transition ${
              active
                ? "border-zinc-900 text-zinc-950 dark:border-zinc-100 dark:text-zinc-50"
                : "border-transparent text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200"
            }`}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
