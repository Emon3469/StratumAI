"use client";

import { ArrowUp, Globe, Mic, MicOff, Paperclip, Square, X, FileText, Layers } from "lucide-react";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { cn } from "@/lib/utils";
import { IconButton } from "./IconButton";

const MAX_CHARS = 7000;
const MAX_FILE_CHARS = 5000;

interface Attachment {
  name: string;
  text: string;
}

interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
}

interface Props {
  onSend: (text: string) => void;
  onStop: () => void;
  busy: boolean;
  disabled?: boolean;
  placeholder?: string;
  autoFocus?: boolean;
  compact?: boolean;
  knowledgeBase?: boolean;
  onToggleKnowledgeBase?: () => void;
}

export function Composer({
  onSend,
  onStop,
  busy,
  disabled,
  placeholder = "Message StratumAI",
  autoFocus,
  compact,
  knowledgeBase = true,
  onToggleKnowledgeBase,
}: Props) {
  const [value, setValue] = useState("");
  const [attachment, setAttachment] = useState<Attachment | null>(null);
  const [listening, setListening] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const recognition = useRef<SpeechRecognitionLike | null>(null);

  useEffect(() => {
    const el = textarea.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
  }, [value]);

  useEffect(() => {
    if (autoFocus && window.matchMedia("(pointer: fine)").matches) textarea.current?.focus();
  }, [autoFocus]);

  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(null), 3500);
    return () => clearTimeout(t);
  }, [notice]);

  useEffect(() => () => recognition.current?.stop(), []);

  const canSend = !busy && !disabled && (value.trim().length > 0 || !!attachment);

  const submit = () => {
    if (!canSend) return;
    let text = value.trim();
    if (attachment) {
      text = `${text || "Summarise the key points of this file."}\n\nAttached file "${attachment.name}":\n"""\n${attachment.text}\n"""`;
    }
    onSend(text.slice(0, MAX_CHARS));
    setValue("");
    setAttachment(null);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  };

  const pickFile = async (file: File | undefined) => {
    if (!file) return;
    if (file.size > 2_000_000 || !/\.(txt|md|log|ya?ml|json|csv|sh|py|ts|js|conf|ini|toml)$/i.test(file.name)) {
      setNotice("Attach a text file such as .txt, .md, .yaml, .json or .log (up to 2 MB).");
      return;
    }
    const text = await file.text();
    setAttachment({ name: file.name, text: text.slice(0, MAX_FILE_CHARS) });
    if (text.length > MAX_FILE_CHARS) setNotice(`Only the first ${MAX_FILE_CHARS.toLocaleString()} characters will be sent.`);
  };

  const toggleVoice = () => {
    if (listening) {
      recognition.current?.stop();
      return;
    }
    const w = window as unknown as {
      SpeechRecognition?: new () => SpeechRecognitionLike;
      webkitSpeechRecognition?: new () => SpeechRecognitionLike;
    };
    const Ctor = w.SpeechRecognition ?? w.webkitSpeechRecognition;
    if (!Ctor) {
      setNotice("Voice input isn't supported in this browser.");
      return;
    }
    const rec = new Ctor();
    const base = value ? `${value.trimEnd()} ` : "";
    rec.lang = navigator.language || "en-US";
    rec.interimResults = true;
    rec.continuous = false;
    rec.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((r) => r[0].transcript)
        .join("");
      setValue(base + transcript);
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recognition.current = rec;
    rec.start();
    setListening(true);
  };

  return (
    <div className="relative">
      {notice && (
        <div className="absolute -top-10 left-1/2 z-10 -translate-x-1/2 animate-fade-in whitespace-nowrap rounded-lg bg-neutral-900 px-3 py-1.5 text-xs text-white shadow-lg dark:bg-black">
          {notice}
        </div>
      )}
      <div
        className={cn(
          "rounded-[26px] border border-line bg-composer shadow-sm transition-shadow focus-within:shadow-md dark:border-transparent",
          compact ? "px-2.5 pt-2.5 pb-2" : "px-3 pt-3 pb-2",
        )}
      >
        {attachment && (
          <div className="mb-2 ml-1 inline-flex max-w-full items-center gap-2 rounded-xl border border-line bg-bg px-3 py-2 text-sm">
            <FileText className="size-4 shrink-0 text-accent" />
            <span className="truncate">{attachment.name}</span>
            <button
              type="button"
              aria-label="Remove attachment"
              onClick={() => setAttachment(null)}
              className="rounded-full p-0.5 text-muted hover:bg-hover hover:text-fg"
            >
              <X className="size-3.5" />
            </button>
          </div>
        )}
        <textarea
          ref={textarea}
          rows={1}
          value={value}
          maxLength={MAX_CHARS}
          disabled={disabled}
          placeholder={placeholder}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          aria-label="Message"
          className="block max-h-[220px] w-full resize-none bg-transparent px-2 py-1 text-[0.95rem] leading-6 text-fg outline-none placeholder:text-faint"
        />
        <div className="mt-2 flex items-center justify-between">
          <div className="flex items-center gap-0.5">
            <input
              ref={fileInput}
              type="file"
              hidden
              accept=".txt,.md,.log,.yaml,.yml,.json,.csv,.sh,.py,.ts,.js,.conf,.ini,.toml"
              onChange={(e) => {
                pickFile(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
            <IconButton label="Attach text file" tooltipSide="top" onClick={() => fileInput.current?.click()}>
              <Paperclip className="size-[18px]" />
            </IconButton>
            {onToggleKnowledgeBase && (
              <IconButton
                label={knowledgeBase ? "Knowledge base: on" : "Knowledge base: off"}
                tooltipSide="top"
                active={knowledgeBase}
                onClick={onToggleKnowledgeBase}
              >
                <Globe className={cn("size-[18px]", knowledgeBase && "text-accent")} />
              </IconButton>
            )}
            {!compact && (
              <span className="ml-1 hidden items-center gap-1 rounded-full border border-line px-2.5 py-1 text-xs text-muted sm:inline-flex">
                <Layers className="size-3.5" />
                Agentic RAG
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <IconButton
              label={listening ? "Stop dictation" : "Dictate"}
              tooltipSide="top"
              active={listening}
              onClick={toggleVoice}
              className={cn(listening && "text-red-500")}
            >
              {listening ? <MicOff className="size-[18px]" /> : <Mic className="size-[18px]" />}
            </IconButton>
            {busy ? (
              <button
                type="button"
                onClick={onStop}
                aria-label="Stop generating"
                className="flex size-9 items-center justify-center rounded-full bg-fg text-bg transition-opacity hover:opacity-80"
              >
                <Square className="size-3.5 fill-current" />
              </button>
            ) : (
              <button
                type="button"
                onClick={submit}
                disabled={!canSend}
                aria-label="Send message"
                className="flex size-9 items-center justify-center rounded-full bg-fg text-bg transition-opacity hover:opacity-80 disabled:opacity-30"
              >
                <ArrowUp className="size-5" strokeWidth={2.4} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
