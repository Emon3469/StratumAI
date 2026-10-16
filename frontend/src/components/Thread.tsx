"use client";

import { ArrowDown, MessageSquareQuote } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { AssistantMessage, UserMessage } from "./Messages";

interface Props {
  messages: ChatMessage[];
  onRegenerate?: (assistantId: string) => void;
  onFeedback?: (messageId: string, value: "up" | "down" | null) => void;
  onAskAbout?: (quote: string) => void;
  compact?: boolean;
  header?: ReactNode;
}

interface SelectionState {
  text: string;
  top: number;
  left: number;
}

export function Thread({ messages, onRegenerate, onFeedback, onAskAbout, compact, header }: Props) {
  const scroller = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);
  const [showJump, setShowJump] = useState(false);
  const [selection, setSelection] = useState<SelectionState | null>(null);

  const scrollToBottom = useCallback((smooth = false) => {
    const el = scroller.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: smooth ? "smooth" : "auto" });
  }, []);

  useLayoutEffect(() => {
    if (pinned.current) scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    const el = content.current;
    if (!el) return;
    const observer = new ResizeObserver(() => pinned.current && scrollToBottom());
    observer.observe(el);
    return () => observer.disconnect();
  }, [scrollToBottom]);

  const lastUserId = [...messages].reverse().find((m) => m.role === "user")?.id;
  useEffect(() => {
    pinned.current = true;
    scrollToBottom(true);
  }, [lastUserId, scrollToBottom]);

  const onScroll = () => {
    const el = scroller.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    pinned.current = distance < 80;
    setShowJump(distance > 240);
    if (selection) setSelection(null);
  };

  const onMouseUp = () => {
    if (!onAskAbout) return;
    setTimeout(() => {
      const sel = window.getSelection();
      const text = sel?.toString().trim() ?? "";
      if (!sel || sel.rangeCount === 0 || text.length < 3) {
        setSelection(null);
        return;
      }
      const anchor = sel.anchorNode instanceof Element ? sel.anchorNode : sel.anchorNode?.parentElement;
      if (!anchor?.closest("[data-selectable='true']") || !scroller.current) {
        setSelection(null);
        return;
      }
      const rect = sel.getRangeAt(0).getBoundingClientRect();
      const host = scroller.current.getBoundingClientRect();
      setSelection({
        text: text.slice(0, 600),
        top: rect.top - host.top + scroller.current.scrollTop - 44,
        left: Math.min(Math.max(rect.left - host.left + rect.width / 2, 80), host.width - 80),
      });
    }, 0);
  };

  const lastId = messages.at(-1)?.id;

  return (
    <div className="relative min-h-0 flex-1">
      <div ref={scroller} onScroll={onScroll} onMouseUp={onMouseUp} className="relative h-full overflow-y-auto">
        <div ref={content} className={cn("mx-auto w-full px-4", compact ? "max-w-none py-4" : "max-w-3xl py-6 md:px-6")}>
          {header}
          <div className={cn("flex flex-col", compact ? "gap-6" : "gap-8")}>
            {messages.map((m) =>
              m.role === "user" ? (
                <UserMessage key={m.id} message={m} />
              ) : (
                <AssistantMessage
                  key={m.id}
                  message={m}
                  compact={compact}
                  isLast={m.id === lastId}
                  onRegenerate={onRegenerate && m.status !== "streaming" ? () => onRegenerate(m.id) : undefined}
                  onFeedback={onFeedback ? (v) => onFeedback(m.id, v) : undefined}
                />
              ),
            )}
          </div>
          <div className="h-6" />
        </div>
        {selection && onAskAbout && (
          <button
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => {
              onAskAbout(selection.text);
              setSelection(null);
              window.getSelection()?.removeAllRanges();
            }}
            style={{ top: selection.top, left: selection.left }}
            className="absolute z-20 inline-flex -translate-x-1/2 animate-fade-in items-center gap-1.5 rounded-full bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white shadow-lg hover:bg-neutral-800 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
          >
            <MessageSquareQuote className="size-3.5" />
            Ask StratumAI
          </button>
        )}
      </div>
      {showJump && (
        <button
          type="button"
          aria-label="Scroll to bottom"
          onClick={() => {
            pinned.current = true;
            scrollToBottom(true);
          }}
          className="absolute bottom-3 left-1/2 flex size-8 -translate-x-1/2 items-center justify-center rounded-full border border-line bg-bg shadow-md hover:bg-hover"
        >
          <ArrowDown className="size-4" />
        </button>
      )}
    </div>
  );
}
