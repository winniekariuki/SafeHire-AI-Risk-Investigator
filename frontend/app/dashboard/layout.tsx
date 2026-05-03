import { DashboardNav } from "@/components/DashboardNav";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-full bg-zinc-50/80 dark:bg-zinc-950/80">
      <div className="mx-auto max-w-5xl border-b border-zinc-200/70 bg-white/40 px-4 pt-8 pb-4 backdrop-blur-md dark:border-zinc-800/70 dark:bg-zinc-900/30 sm:px-6 lg:px-8">
        <DashboardNav />
      </div>
      {children}
    </div>
  );
}
