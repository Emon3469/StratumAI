"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessage, Conversation } from "@/lib/types";
import { titleFrom, uid } from "@/lib/utils";

const STORAGE_KEY = "stratumai.conversations.v1";
const MAX_CONVERSATIONS = 100;

function load(): Conversation[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Conversation[];
    return parsed.map((c) => ({
      ...c,
      messages: c.messages.map((m) => (m.status === "streaming" ? { ...m, status: "stopped" } : m)),
    }));
  } catch {
    return [];
  }
}

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>(load);
  const [activeId, setActiveId] = useState<string | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations.slice(0, MAX_CONVERSATIONS)));
      } catch {}
    }, 400);
  }, [conversations]);

  const active = conversations.find((c) => c.id === activeId) ?? null;

  const create = useCallback((firstMessage: string): string => {
    const id = uid();
    const now = Date.now();
    setConversations((prev) => [
      { id, title: titleFrom(firstMessage), createdAt: now, updatedAt: now, messages: [] },
      ...prev,
    ]);
    setActiveId(id);
    return id;
  }, []);

  const update = useCallback((id: string, fn: (c: Conversation) => Conversation) => {
    setConversations((prev) => prev.map((c) => (c.id === id ? fn(c) : c)));
  }, []);

  const appendMessages = useCallback(
    (id: string, messages: ChatMessage[]) =>
      update(id, (c) => ({ ...c, updatedAt: Date.now(), messages: [...c.messages, ...messages] })),
    [update],
  );

  const patchMessage = useCallback(
    (id: string, messageId: string, fn: (m: ChatMessage) => ChatMessage) =>
      update(id, (c) => ({ ...c, messages: c.messages.map((m) => (m.id === messageId ? fn(m) : m)) })),
    [update],
  );

  const truncateFrom = useCallback(
    (id: string, messageId: string) =>
      update(id, (c) => {
        const index = c.messages.findIndex((m) => m.id === messageId);
        return index === -1 ? c : { ...c, messages: c.messages.slice(0, index) };
      }),
    [update],
  );

  const remove = useCallback((id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    setActiveId((current) => (current === id ? null : current));
  }, []);

  const rename = useCallback(
    (id: string, title: string) => update(id, (c) => ({ ...c, title: title.trim() || c.title })),
    [update],
  );

  const togglePin = useCallback((id: string) => update(id, (c) => ({ ...c, pinned: !c.pinned })), [update]);

  const clearAll = useCallback(() => {
    setConversations([]);
    setActiveId(null);
  }, []);

  return {
    conversations,
    active,
    activeId,
    setActiveId,
    create,
    appendMessages,
    patchMessage,
    truncateFrom,
    remove,
    rename,
    togglePin,
    clearAll,
  };
}
