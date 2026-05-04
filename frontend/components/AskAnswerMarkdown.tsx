import ReactMarkdown from "react-markdown";

const answerProseClassName =
  "text-sm leading-relaxed text-zinc-700 dark:text-zinc-300 [&_a]:text-blue-600 [&_a]:underline dark:[&_a]:text-blue-400 [&_blockquote]:border-l-4 [&_blockquote]:border-zinc-300 [&_blockquote]:pl-4 [&_blockquote]:italic dark:[&_blockquote]:border-zinc-600 [&_code]:rounded [&_code]:bg-zinc-200/80 [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-xs dark:[&_code]:bg-zinc-800 [&_h2]:mb-2 [&_h2]:mt-4 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:first:mt-0 [&_h3]:mb-2 [&_h3]:mt-3 [&_h3]:text-sm [&_h3]:font-semibold [&_li]:my-1 [&_ol]:list-decimal [&_ol]:pl-6 [&_p]:my-2 [&_p]:first:mt-0 [&_strong]:font-semibold [&_strong]:text-zinc-900 dark:[&_strong]:text-zinc-100 [&_ul]:list-disc [&_ul]:pl-6";

type Props = {
  content: string;
  className?: string;
};

export function AskAnswerMarkdown({ content, className = "" }: Props) {
  return (
    <div className={`${answerProseClassName} ${className}`.trim()}>
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
