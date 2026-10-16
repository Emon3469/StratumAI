"use client";

import { Check, Copy } from "lucide-react";
import { memo, useState, type ComponentProps, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import { linkCitations } from "@/lib/citations";
import type { Source } from "@/lib/types";
import { formatSource } from "@/lib/utils";

function textOf(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  if (node && typeof node === "object" && "props" in node) {
    return textOf((node as { props: { children?: ReactNode } }).props.children);
  }
  return "";
}

function CodeBlock({ children, ...props }: ComponentProps<"pre">) {
  const [copied, setCopied] = useState(false);
  const child = Array.isArray(children) ? children[0] : children;
  const className =
    child && typeof child === "object" && "props" in child
      ? ((child as { props: { className?: string } }).props.className ?? "")
      : "";
  const language = /language-([\w-]+)/.exec(className)?.[1] ?? "text";

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(textOf(children).replace(/\n$/, ""));
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {}
  };

  return (
    <div className="not-prose overflow-hidden rounded-xl border border-line bg-[var(--code-bg)]">
      <div className="flex items-center justify-between bg-[var(--code-header)] px-4 py-1.5 text-xs text-muted">
        <span className="font-mono">{language}</span>
        <button type="button" onClick={copy} className="inline-flex items-center gap-1 hover:text-fg">
          {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre {...props}>{children}</pre>
    </div>
  );
}

interface Props {
  content: string;
  sources?: Source[];
}

function MarkdownImpl({ content, sources = [] }: Props) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
        components={{
          pre: CodeBlock,
          table: ({ children }) => (
            <div className="overflow-x-auto rounded-xl border border-line">
              <table>{children}</table>
            </div>
          ),
          a: ({ href, children }) => {
            if (href?.startsWith("#cite-")) {
              const n = Number(href.slice(6));
              const source = sources.find((s) => s.id === n);
              return (
                <span
                  title={source ? formatSource(source.source) : undefined}
                  className="mx-0.5 inline-flex h-[18px] min-w-[18px] -translate-y-px items-center justify-center rounded-full bg-subtle px-1.5 align-middle text-[10px] font-semibold text-muted no-underline ring-1 ring-line"
                >
                  {n}
                </span>
              );
            }
            return (
              <a href={href} target="_blank" rel="noreferrer noopener">
                {children}
              </a>
            );
          },
        }}
      >
        {linkCitations(content, sources.length)}
      </ReactMarkdown>
    </div>
  );
}

export const Markdown = memo(MarkdownImpl);
