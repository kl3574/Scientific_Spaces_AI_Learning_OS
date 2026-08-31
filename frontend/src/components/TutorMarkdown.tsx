"use client";

import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import { getSafeTutorMarkdownHref } from "@/lib/tutorWorkspace";

export function TutorMarkdown({ content }: Readonly<{ content: string }>) {
  return (
    <div className="reader-markdown tutor-markdown" data-testid="tutor-answer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { strict: false, throwOnError: false }]]}
        components={{
          a({ children, href }) {
            const safeHref = getSafeTutorMarkdownHref(href);
            if (!safeHref) {
              return <span>{children}</span>;
            }
            const external = safeHref.startsWith("http://") || safeHref.startsWith("https://");
            return (
              <a
                className="font-medium text-emerald-800 underline decoration-emerald-300 underline-offset-2"
                href={safeHref}
                rel={external ? "noreferrer" : undefined}
                target={external ? "_blank" : undefined}
              >
                {children}
              </a>
            );
          },
          img({ alt }) {
            return (
              <span className="block border-l-2 border-amber-300 pl-3 text-sm text-slate-500">
                {alt ? `Image omitted: ${alt}` : "Image omitted."}
              </span>
            );
          },
          pre({ children }) {
            return <pre className="max-w-full overflow-x-auto rounded bg-slate-950 p-3 text-sm text-slate-100">{children}</pre>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
