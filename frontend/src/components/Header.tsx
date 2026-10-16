"use client";

import { Check, ChevronDown, Menu, Share, SquarePen, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { BackendState } from "@/hooks/useBackend";
import type { ProviderInfo } from "@/lib/types";
import { cn } from "@/lib/utils";
import { IconButton } from "./IconButton";
import { ThemeToggle } from "./ThemeToggle";

const STATE_LABEL: Record<BackendState, string> = {
  connecting: "Connecting",
  waking: "Waking server",
  online: "Online",
  offline: "Offline",
};

export function ModelPicker({
  providers,
  value,
  onChange,
  align = "left",
}: {
  providers: ProviderInfo[];
  value: string;
  onChange: (value: string) => void;
  align?: "left" | "right";
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  const current = providers.find((p) => p.id === value);
  const label = current ? current.model.split("/").pop() : "Auto";

  const options = [
    { id: "auto", title: "Auto", subtitle: "Fastest healthy model with automatic fallback", healthy: true },
    ...providers.map((p) => ({ id: p.id, title: p.label, subtitle: p.model, healthy: p.healthy })),
  ];

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="inline-flex items-center gap-1 rounded-md px-1 text-xs text-muted transition-colors hover:text-fg"
      >
        {label}
        <ChevronDown className="size-3.5" />
      </button>
      {open && (
        <div
          role="listbox"
          className={cn(
            "absolute top-full z-50 mt-2 w-72 animate-fade-in rounded-2xl border border-line bg-elevated p-1.5 shadow-xl",
            align === "right" ? "right-0" : "left-0",
          )}
        >
          <p className="px-3 pt-1.5 pb-1 text-xs text-faint">Model</p>
          {options.map((o) => (
            <button
              key={o.id}
              type="button"
              role="option"
              aria-selected={value === o.id}
              onClick={() => {
                onChange(o.id);
                setOpen(false);
              }}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left hover:bg-hover"
            >
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2 text-sm font-medium">
                  {o.title}
                  {!o.healthy && <span className="rounded bg-amber-500/15 px-1.5 text-[10px] text-amber-600">cooling down</span>}
                </span>
                <span className="block truncate text-xs text-faint">{o.subtitle}</span>
              </span>
              {value === o.id && <Check className="size-4 shrink-0" />}
            </button>
          ))}
          {providers.length === 0 && <p className="px-3 py-2 text-xs text-faint">Connecting to the server…</p>}
        </div>
      )}
    </div>
  );
}

interface HeaderProps {
  providers: ProviderInfo[];
  model: string;
  onModelChange: (value: string) => void;
  backendState: BackendState;
  onMenu: () => void;
  onNewChat: () => void;
  onShare?: () => void;
  shareDisabled?: boolean;
}

export function Header({
  providers,
  model,
  onModelChange,
  backendState,
  onMenu,
  onNewChat,
  onShare,
  shareDisabled,
}: HeaderProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-2 px-3 md:px-5">
      <div className="flex items-center gap-1">
        <IconButton label="Open menu" onClick={onMenu} className="md:hidden">
          <Menu className="size-5" />
        </IconButton>
        <div className="flex flex-col leading-tight">
          <span className="flex items-center gap-2 text-[15px] font-semibold">
            StratumAI
            <span
              title={STATE_LABEL[backendState]}
              className={cn(
                "size-2 rounded-full",
                backendState === "online" && "bg-emerald-500",
                (backendState === "connecting" || backendState === "waking") && "animate-pulse bg-amber-500",
                backendState === "offline" && "bg-red-500",
              )}
            />
          </span>
          <ModelPicker providers={providers} value={model} onChange={onModelChange} />
        </div>
      </div>
      <div className="flex items-center gap-1">
        <ThemeToggle className="md:hidden" />
        <IconButton label="New chat" onClick={onNewChat} className="md:hidden">
          <SquarePen className="size-5" />
        </IconButton>
        {onShare && (
          <button
            type="button"
            onClick={onShare}
            disabled={shareDisabled}
            className="hidden items-center gap-2 rounded-full border border-line px-3.5 py-1.5 text-sm transition-colors hover:bg-hover disabled:opacity-40 sm:inline-flex"
          >
            <Share className="size-4" />
            Share
          </button>
        )}
      </div>
    </header>
  );
}

export function PanelHeader({
  providers,
  model,
  onModelChange,
  onClose,
}: {
  providers: ProviderInfo[];
  model: string;
  onModelChange: (value: string) => void;
  onClose: () => void;
}) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between px-4">
      <div className="flex flex-col leading-tight">
        <span className="text-[15px] font-semibold">StratumAI</span>
        <ModelPicker providers={providers} value={model} onChange={onModelChange} />
      </div>
      <IconButton label="Close thread" onClick={onClose}>
        <X className="size-5" />
      </IconButton>
    </header>
  );
}
