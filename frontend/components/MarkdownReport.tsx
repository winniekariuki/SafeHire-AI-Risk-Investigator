import ReactMarkdown from "react-markdown";
import { SectionCard } from "@/components/SectionCard";

export function MarkdownReport({ report }: { report: string }) {
  return (
    <SectionCard title="Investigation report">
      <div
        className="max-h-[28rem] overflow-auto rounded-lg border border-zinc-200 bg-zinc-50/80 p-4 text-sm leading-relaxed text-zinc-800 dark:border-zinc-800 dark:bg-zinc-900/50 dark:text-zinc-200 [&_a]:text-blue-600 [&_a]:underline dark:[&_a]:text-blue-400 [&_code]:rounded [&_code]:bg-zinc-200/80 [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-xs dark:[&_code]:bg-zinc-800 [&_h1]:mb-3 [&_h1]:mt-4 [&_h1]:text-xl [&_h1]:font-semibold [&_h1]:first:mt-0 [&_h2]:mb-2 [&_h2]:mt-4 [&_h2]:text-lg [&_h2]:font-semibold [&_li]:my-1 [&_ol]:list-decimal [&_ol]:pl-6 [&_p]:my-2 [&_ul]:list-disc [&_ul]:pl-6"
      >
        <ReactMarkdown>{report}</ReactMarkdown>
      </div>
    </SectionCard>
  );
}
