import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { redirect } from "next/navigation";

export default async function Home() {
  const { userId } = await auth();
  if (userId) redirect("/dashboard");

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-24">
      <main className="w-full max-w-lg rounded-2xl border border-white/50 bg-white/75 p-10 text-center shadow-lg shadow-violet-500/10 backdrop-blur-md dark:border-zinc-700/50 dark:bg-zinc-900/75 dark:shadow-fuchsia-900/20">
        <p className="text-sm font-medium text-violet-600 dark:text-violet-300">
          SafeHire
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
          AI risk investigator
        </h1>
        <p className="mt-4 text-lg leading-relaxed text-zinc-600 dark:text-zinc-400">
          Sign in to run evidence-based risk assessments and get clear, actionable
          hiring recommendations
        </p>
        <div className="mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <Link
            href="/sign-in"
            className="inline-flex h-11 w-full items-center justify-center rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 px-6 text-sm font-medium text-white shadow-md transition hover:from-violet-500 hover:to-fuchsia-500 sm:w-auto"
          >
            Sign in
          </Link>
          <Link
            href="/sign-up"
            className="inline-flex h-11 w-full items-center justify-center rounded-lg border border-zinc-300/80 bg-white/80 px-6 text-sm font-medium text-zinc-900 backdrop-blur-sm transition hover:bg-white sm:w-auto dark:border-zinc-600 dark:bg-zinc-800/80 dark:text-zinc-100 dark:hover:bg-zinc-800"
          >
            Create account
          </Link>
        </div>
      </main>
    </div>
  );
}
