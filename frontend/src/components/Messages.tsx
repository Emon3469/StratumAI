"use client";

import {
  Check,
  Copy,
  CornerDownRight,
  FileText,
  RefreshCw,
  ThumbsDown,
  ThumbsUp,
  Volume2,
  VolumeX,
  Zap,
} from "lucide-react";
import { memo, useEffect, useState } from "react";
import type { ChatMessage, Source } from "@/lib/types";
import { cn, formatSource } from "@/lib/utils";
import { IconButton } from "./IconButton";
import { Avatar } from "./Logo";
import { Markdown } from "./Markdown";

function useCopy() {
  const [copied, setCopied] = useState(false);
  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {}
  };
  return { copied, copy };
}

function toSpeech(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, " Code block omitted. ")
    .replace(/\[(\d+)\]/g, "")
    .replace(/[#*_~>|`]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function useSpeech() {
  const [speaking, setSpeaking] = useState(false);
  useEffect(() => () => window.speechSynthesis?.cancel(), []);
  const toggle = (text: string) => {
    const synth = typeof window !== "undefined" ? window.speechSynthesis : undefined;
    if (!synth) return;
    if (speaking) {
      synth.cancel();
      setSpeaking(false);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(toSpeech(text));
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    synth.cancel();
    synth.speak(utterance);
    setSpeaking(true);
  };
  return { speaking, toggle };
}

export function UserMessage({ message }: { message: ChatMessage }) {
  const { copied, copy } = useCopy();
  return (
    <div className="group flex animate-fade-in flex-col items-end gap-1">
      {message.quote && (
        <div className="flex max-w-[85%] items-start gap-1.5 text-sm text-muted">
          <CornerDownRight className="mt-0.5 size-4 shrink-0" />
          <span className="line-clamp-2">{message.quote}</span>
        </div>
      )}
      <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-3xl bg-bubble px-5 py-2.5 text-[0.95rem] leading-relaxed">
        {message.content}
      </div>
      <div className="flex opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
        <IconButton label={copied ? "Copied" : "Copy"} onClick={() => copy(message.content)} className="size-8">
          {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
        </IconButton>
      </div>
    </div>
  );
}

function Sources({ sources }: { sources: Source[] }) {
  const [open, setOpen] = useState<number | null>(null);
  if (!sources.length) return null;
  const active = sources.find((s) => s.id === open);
  return (
    <div className="mt-4">
      <div className="flex flex-wrap gap-1.5">
        {sources.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setOpen(open === s.id ? null : s.id)}
            className={cn(
              "inline-flex max-w-[16rem] items-center gap-1.5 rounded-full border border-line px-2.5 py-1 text-xs text-muted transition-colors hover:bg-hover hover:text-fg",
              open === s.id && "bg-hover text-fg",
            )}
          >
            <span className="flex size-4 items-center justify-center rounded-full bg-subtle text-[10px] font-semibold ring-1 ring-line">
              {s.id}
            </span>
            <FileText className="size-3.5 shrink-0" />
            <span className="truncate capitalize">{formatSource(s.source)}</span>
          </button>
        ))}
      </div>
      {active && (
        <div className="mt-2 animate-fade-in rounded-xl border border-line bg-subtle p-3 text-xs leading-relaxed text-muted">
          <div className="mb-1 flex items-center justify-between gap-2 font-medium text-fg">
            <span className="truncate">{active.source}</span>
            <span className="shrink-0 text-faint">relevance {Math.round(active.score * 100)}%</span>
          </div>
          <p className="line-clamp-6 whitespace-pre-wrap">{active.snippet}…</p>
        </div>
      )}
    </div>
  );
}

function Thinking({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-1 text-sm text-muted">
      <span className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="size-1.5 animate-bounce rounded-full bg-current"
            style={{ animationDelay: `${i * 120}ms` }}
          />
        ))}
      </span>
      <span className="animate-pulse">{label ?? "Thinking"}…</span>
    </div>
  );
}

interface AssistantProps {
  message: ChatMessage;
  isLast: boolean;
  onRegenerate?: () => void;
  onFeedback?: (value: "up" | "down" | null) => void;
  compact?: boolean;
}

function AssistantMessageImpl({ message, isLast, onRegenerate, onFeedback, compact }: AssistantProps) {
  const { copied, copy } = useCopy();
  const { speaking, toggle } = useSpeech();
  const streaming = message.status === "streaming";
  const meta = message.meta;

  return (
    <div className="group flex animate-fade-in gap-3 md:gap-4" data-role="assistant">
      {!compact && <Avatar className="mt-0.5" />}
      <div className="min-w-0 flex-1">
        {streaming && !message.content ? (
          <Thinking label={message.stage} />
        ) : (
          <div
            data-selectable="true"
            className={cn(
              streaming && "streaming",
              message.status === "error" && "text-red-600 dark:text-red-400",
            )}
          >
            <Markdown content={message.content} sources={message.sources} />
          </div>
        )}

        {message.status === "stopped" && <p className="mt-2 text-xs text-faint">Response stopped.</p>}

        {!streaming && message.sources && <Sources sources={message.sources} />}

        {!streaming && message.content && (
          <div
            className={cn(
              "mt-2 -ml-2 flex flex-wrap items-center gap-0.5 transition-opacity",
              !isLast && "opacity-0 group-hover:opacity-100 focus-within:opacity-100",
            )}
          >
            <IconButton
              label={speaking ? "Stop reading" : "Read aloud"}
              onClick={() => toggle(message.content)}
              className="size-8"
            >
              {speaking ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />}
            </IconButton>
            <IconButton label={copied ? "Copied" : "Copy"} onClick={() => copy(message.content)} className="size-8">
              {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
            </IconButton>
            {onRegenerate && (
              <IconButton label="Regenerate" onClick={onRegenerate} className="size-8">
                <RefreshCw className="size-4" />
              </IconButton>
            )}
            {onFeedback && (
              <>
                <IconButton
                  label="Good response"
                  active={message.feedback === "up"}
                  onClick={() => onFeedback(message.feedback === "up" ? null : "up")}
                  className="size-8"
                >
                  <ThumbsUp className={cn("size-4", message.feedback === "up" && "fill-current")} />
                </IconButton>
                <IconButton
                  label="Bad response"
                  active={message.feedback === "down"}
                  onClick={() => onFeedback(message.feedback === "down" ? null : "down")}
                  className="size-8"
                >
                  <ThumbsDown className={cn("size-4", message.feedback === "down" && "fill-current")} />
                </IconButton>
              </>
            )}
            {meta?.model && meta.provider !== "guardrails" && (
              <span className="ml-1 inline-flex items-center gap-1 text-[11px] text-faint">
                {meta.cached && <Zap className="size-3" />}
                {meta.provider} · {meta.model}
                {typeof meta.ttft_ms === "number" && ` · ${(meta.ttft_ms / 1000).toFixed(1)}s`}
                {meta.fallbacks ? ` · ${meta.fallbacks} fallback${meta.fallbacks > 1 ? "s" : ""}` : ""}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export const AssistantMessage = memo(AssistantMessageImpl);
