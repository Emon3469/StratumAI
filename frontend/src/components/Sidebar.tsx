"use client";

import {
  Bookmark,
  Check,
  History,
  PanelLeft,
  Pencil,
  Pin,
  Search,
  Settings,
  SquarePen,
  Trash2,
  User,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import type { Conversation } from "@/lib/types";
import { cn, relativeGroup } from "@/lib/utils";
import { IconButton } from "./IconButton";
import { LogoMark } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

export type DrawerView = "history" | "pinned" | "search" | "settings" | null;

interface RailProps {
  view: DrawerView;
  onView: (view: DrawerView) => void;
  onNewChat: () => void;
}

export function IconRail({ view, onView, onNewChat }: RailProps) {
  const toggle = (next: Exclude<DrawerView, null>) => onView(view === next ? null : next);
  return (
    <nav
      aria-label="Primary"
      className="hidden w-[60px] shrink-0 flex-col items-center justify-between border-r border-line bg-rail py-3 md:flex"
    >
      <div className="flex flex-col items-center gap-1.5">
        <IconButton label={view ? "Close sidebar" : "Open sidebar"} tooltipSide="right" onClick={() => toggle("history")}>
          <PanelLeft className="size-5" />
        </IconButton>
        <IconButton label="New chat" tooltipSide="right" onClick={onNewChat}>
          <SquarePen className="size-5" />
        </IconButton>
        <IconButton label="History" tooltipSide="right" active={view === "history"} onClick={() => toggle("history")}>
          <History className="size-5" />
        </IconButton>
        <IconButton label="Pinned chats" tooltipSide="right" active={view === "pinned"} onClick={() => toggle("pinned")}>
          <Bookmark className="size-5" />
        </IconButton>
        <IconButton label="Search chats" tooltipSide="right" active={view === "search"} onClick={() => toggle("search")}>
          <Search className="size-5" />
        </IconButton>
      </div>
      <div className="flex flex-col items-center gap-1.5">
        <ThemeToggle />
        <IconButton label="Settings" tooltipSide="right" active={view === "settings"} onClick={() => toggle("settings")}>
          <Settings className="size-5" />
        </IconButton>
        <span
          aria-label="Guest"
          className="mt-1 flex size-8 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-teal-600 text-white"
        >
          <User className="size-4" />
        </span>
      </div>
    </nav>
  );
}

interface DrawerProps {
  view: DrawerView;
  conversations: Conversation[];
  activeId: string | null;
  onClose: () => void;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onTogglePin: (id: string) => void;
  onClearAll: () => void;
  apiUrl: string;
  backendState: string;
}

function ConversationRow({
  conversation,
  active,
  onSelect,
  onDelete,
  onRename,
  onTogglePin,
}: {
  conversation: Conversation;
  active: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onRename: (title: string) => void;
  onTogglePin: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(conversation.title);

  if (editing) {
    return (
      <form
        className="flex items-center gap-1 rounded-lg bg-hover px-2 py-1"
        onSubmit={(e) => {
          e.preventDefault();
          onRename(draft);
          setEditing(false);
        }}
      >
        <input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => setEditing(false)}
          onKeyDown={(e) => e.key === "Escape" && setEditing(false)}
          className="min-w-0 flex-1 bg-transparent py-1 text-sm outline-none"
        />
        <button type="submit" onMouseDown={(e) => e.preventDefault()} aria-label="Save title" className="p-1 text-muted hover:text-fg">
          <Check className="size-4" />
        </button>
      </form>
    );
  }

  return (
    <div
      className={cn(
        "group relative flex items-center rounded-lg text-sm transition-colors hover:bg-hover",
        active && "bg-hover",
      )}
    >
      <button type="button" onClick={onSelect} className="flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-left">
        {conversation.pinned && <Pin className="size-3.5 shrink-0 text-faint" />}
        <span className="truncate">{conversation.title}</span>
      </button>
      <div className="absolute right-1 hidden items-center rounded-md bg-hover group-hover:flex">
        <button type="button" aria-label="Pin" onClick={onTogglePin} className="p-1.5 text-muted hover:text-fg">
          <Pin className={cn("size-3.5", conversation.pinned && "fill-current")} />
        </button>
        <button
          type="button"
          aria-label="Rename"
          onClick={() => {
            setDraft(conversation.title);
            setEditing(true);
          }}
          className="p-1.5 text-muted hover:text-fg"
        >
          <Pencil className="size-3.5" />
        </button>
        <button type="button" aria-label="Delete" onClick={onDelete} className="p-1.5 text-muted hover:text-red-500">
          <Trash2 className="size-3.5" />
        </button>
      </div>
    </div>
  );
}

export function Drawer({
  view,
  conversations,
  activeId,
  onClose,
  onSelect,
  onNewChat,
  onDelete,
  onRename,
  onTogglePin,
  onClearAll,
  apiUrl,
  backendState,
}: DrawerProps) {
  const [query, setQuery] = useState("");

  const list = useMemo(() => {
    let items = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt);
    if (view === "pinned") items = items.filter((c) => c.pinned);
    if (view === "search" && query.trim()) {
      const q = query.toLowerCase();
      items = items.filter(
        (c) => c.title.toLowerCase().includes(q) || c.messages.some((m) => m.content.toLowerCase().includes(q)),
      );
    }
    return items;
  }, [conversations, view, query]);

  const groups = useMemo(() => {
    const map = new Map<string, Conversation[]>();
    for (const c of list) {
      const key = view === "history" && c.pinned ? "Pinned" : relativeGroup(c.updatedAt);
      map.set(key, [...(map.get(key) ?? []), c]);
    }
    return [...map.entries()].sort(([a], [b]) => (a === "Pinned" ? -1 : b === "Pinned" ? 1 : 0));
  }, [list, view]);

  if (!view) return null;

  const title =
    view === "history" ? "Chats" : view === "pinned" ? "Pinned" : view === "search" ? "Search" : "Settings";

  return (
    <>
      <div className="fixed inset-0 z-30 bg-black/40 md:hidden" onClick={onClose} aria-hidden="true" />
      <aside className="fixed inset-y-0 left-0 z-40 flex w-[280px] animate-slide-in-left flex-col border-r border-line bg-rail md:static md:z-auto">
        <div className="flex items-center justify-between px-3 pt-3 pb-2">
          <div className="flex items-center gap-2 pl-1">
            <LogoMark className="size-6" />
            <span className="font-semibold">{title}</span>
          </div>
          <div className="flex items-center">
            <IconButton label="New chat" onClick={onNewChat}>
              <SquarePen className="size-[18px]" />
            </IconButton>
            <IconButton label="Close" onClick={onClose}>
              <X className="size-[18px]" />
            </IconButton>
          </div>
        </div>

        {view === "search" && (
          <div className="px-3 pb-2">
            <div className="flex items-center gap-2 rounded-lg border border-line bg-bg px-3 py-2">
              <Search className="size-4 text-faint" />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search conversations"
                className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-faint"
              />
            </div>
          </div>
        )}

        {view === "settings" ? (
          <div className="flex-1 space-y-5 overflow-y-auto px-4 py-2 text-sm">
            <section className="space-y-2">
              <h3 className="text-xs font-semibold tracking-wide text-faint uppercase">Appearance</h3>
              <div className="flex items-center justify-between rounded-lg border border-line px-3 py-2">
                <span>Theme</span>
                <ThemeToggle />
              </div>
            </section>
            <section className="space-y-2">
              <h3 className="text-xs font-semibold tracking-wide text-faint uppercase">Connection</h3>
              <div className="space-y-1 rounded-lg border border-line px-3 py-2">
                <div className="flex items-center justify-between">
                  <span>API status</span>
                  <span className="capitalize text-muted">{backendState}</span>
                </div>
                <p className="truncate text-xs text-faint" title={apiUrl}>
                  {apiUrl}
                </p>
              </div>
            </section>
            <section className="space-y-2">
              <h3 className="text-xs font-semibold tracking-wide text-faint uppercase">Data</h3>
              <p className="text-xs text-muted">Conversations are stored only in this browser.</p>
              <button
                type="button"
                onClick={() => {
                  if (confirm("Delete all conversations? This can't be undone.")) onClearAll();
                }}
                className="w-full rounded-lg border border-red-500/30 px-3 py-2 text-left text-red-600 hover:bg-red-500/10 dark:text-red-400"
              >
                Clear all conversations
              </button>
            </section>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto px-2 pb-4">
            {groups.length === 0 ? (
              <p className="px-3 py-6 text-center text-sm text-faint">
                {view === "pinned"
                  ? "Pin a conversation to keep it here."
                  : view === "search" && query
                    ? "No matching conversations."
                    : "No conversations yet."}
              </p>
            ) : (
              groups.map(([label, items]) => (
                <div key={label} className="mt-3">
                  <h3 className="px-3 pb-1 text-xs font-medium text-faint">{label}</h3>
                  {items.map((c) => (
                    <ConversationRow
                      key={c.id}
                      conversation={c}
                      active={c.id === activeId}
                      onSelect={() => onSelect(c.id)}
                      onDelete={() => onDelete(c.id)}
                      onRename={(t) => onRename(c.id, t)}
                      onTogglePin={() => onTogglePin(c.id)}
                    />
                  ))}
                </div>
              ))
            )}
          </div>
        )}
      </aside>
    </>
  );
}
