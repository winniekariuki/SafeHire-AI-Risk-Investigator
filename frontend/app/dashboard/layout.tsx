import { DashboardNav } from "@/components/DashboardNav";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-full bg-zinc-50 dark:bg-black">
      <div className="mx-auto max-w-5xl border-b border-zinc-200 px-4 pt-8 pb-4 dark:border-zinc-800 sm:px-6 lg:px-8">
        <DashboardNav />
      </div>
      {children}
    </div>
  );
}
