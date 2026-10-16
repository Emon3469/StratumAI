"use client";

import { CornerDownRight, Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useBackend } from "@/hooks/useBackend";
import { useConversations } from "@/hooks/useConversations";
import { useStreamingReply } from "@/hooks/useStreamingReply";
import { API_URL } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import { cn, uid } from "@/lib/utils";
import { Composer } from "./Composer";
import { EmptyState } from "./EmptyState";
import { Header, PanelHeader } from "./Header";
import { Drawer, IconRail, type DrawerView } from "./Sidebar";
import { Thread } from "./Thread";

const HISTORY_LIMIT = 12;
const PANEL_KEY = "side-thread";

function toHistory(messages: ChatMessage[]) {
  return messages
    .filter((m) => m.content && m.status !== "error")
    .map((m) => ({ role: m.role, content: m.content }))
    .slice(-HISTORY_LIMIT);
}

function userMessage(content: string, quote?: string): ChatMessage {
  return { id: uid(), role: "user", content, quote, createdAt: Date.now(), status: "done" };
}

function pendingReply(): ChatMessage {
  return { id: uid(), role: "assistant", content: "", createdAt: Date.now(), status: "streaming", stage: "Thinking" };
}

function withQuote(quote: string, question: string) {
  return `Regarding this part of your earlier answer:\n"""${quote}"""\n\n${question}`;
}

interface SidePanelState {
  quote: string;
  messages: ChatMessage[];
}

export function ChatApp() {
  const store = useConversations();
  const { run, stop } = useStreamingReply();
  const { state: backendState, providers } = useBackend();
  const [model, setModel] = useState("auto");
  const [panelModel, setPanelModel] = useState("auto");
  const [knowledgeBase, setKnowledgeBase] = useState(true);
  const [drawer, setDrawer] = useState<DrawerView>(null);
  const [panel, setPanel] = useState<SidePanelState | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const { active, activeId, create, appendMessages, patchMessage, truncateFrom, setActiveId } = store;
  const messages = useMemo(() => active?.messages ?? [], [active]);
  const busy = messages.at(-1)?.status === "streaming";
  const panelBusy = panel?.messages.at(-1)?.status === "streaming";

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2200);
    return () => clearTimeout(t);
  }, [toast]);

  const startReply = useCallback(
    (conversationId: string, prompt: string, history: ChatMessage[], regenerate = false) => {
      const reply = pendingReply();
      appendMessages(conversationId, [reply]);
      run(
        conversationId,
        {
          message: prompt,
          history: toHistory(history),
          provider: model,
          use_knowledge_base: knowledgeBase,
          regenerate,
        },
        (fn) => patchMessage(conversationId, reply.id, fn),
      );
    },
    [appendMessages, patchMessage, run, model, knowledgeBase],
  );

  const send = useCallback(
    (text: string) => {
      const conversationId = activeId ?? create(text);
      const history = activeId ? messages : [];
      appendMessages(conversationId, [userMessage(text)]);
      startReply(conversationId, text, history);
    },
    [activeId, create, messages, appendMessages, startReply],
  );

  const regenerate = useCallback(
    (assistantId: string) => {
      if (!activeId || busy) return;
      const index = messages.findIndex((m) => m.id === assistantId);
      const user = messages[index - 1];
      if (index < 1 || user?.role !== "user") return;
      truncateFrom(activeId, assistantId);
      const prompt = user.quote ? withQuote(user.quote, user.content) : user.content;
      startReply(activeId, prompt, messages.slice(0, index - 1), true);
    },
    [activeId, busy, messages, truncateFrom, startReply],
  );

  const feedback = useCallback(
    (messageId: string, value: "up" | "down" | null) => {
      if (activeId) patchMessage(activeId, messageId, (m) => ({ ...m, feedback: value }));
    },
    [activeId, patchMessage],
  );

  const newChat = useCallback(() => {
    if (activeId && busy) stop(activeId);
    setActiveId(null);
    setPanel(null);
    if (window.matchMedia("(max-width: 767px)").matches) setDrawer(null);
  }, [activeId, busy, setActiveId, stop]);

  const openPanel = useCallback((quote: string) => {
    stop(PANEL_KEY);
    setPanel({ quote, messages: [] });
  }, [stop]);

  const patchPanel = useCallback((replyId: string, fn: (m: ChatMessage) => ChatMessage) => {
    setPanel((p) => (p ? { ...p, messages: p.messages.map((m) => (m.id === replyId ? fn(m) : m)) } : p));
  }, []);

  const sendInPanel = useCallback(
    (text: string) => {
      if (!panel) return;
      const first = panel.messages.length === 0;
      const user = userMessage(text, first ? panel.quote : undefined);
      const reply = pendingReply();
      const history = [...toHistory(messages).slice(-6), ...toHistory(panel.messages)];
      setPanel({ ...panel, messages: [...panel.messages, user, reply] });
      run(
        PANEL_KEY,
        {
          message: withQuote(panel.quote, text),
          history,
          provider: panelModel,
          use_knowledge_base: knowledgeBase,
        },
        (fn) => patchPanel(reply.id, fn),
      );
    },
    [panel, messages, run, panelModel, knowledgeBase, patchPanel],
  );

  const share = useCallback(async () => {
    if (!active) return;
    const transcript = [
      `# ${active.title}`,
      ...active.messages.map((m) => `**${m.role === "user" ? "You" : "StratumAI"}:**\n\n${m.content}`),
    ].join("\n\n---\n\n");
    try {
      if (navigator.share && window.matchMedia("(pointer: coarse)").matches) {
        await navigator.share({ title: active.title, text: transcript });
        return;
      }
      await navigator.clipboard.writeText(transcript);
      setToast("Conversation copied to clipboard");
    } catch {}
  }, [active]);

  const selectConversation = (id: string) => {
    setActiveId(id);
    setPanel(null);
    if (window.matchMedia("(max-width: 767px)").matches) setDrawer(null);
  };

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-bg text-fg">
      <IconRail view={drawer} onView={setDrawer} onNewChat={newChat} />
      <Drawer
        view={drawer}
        conversations={store.conversations}
        activeId={activeId}
        onClose={() => setDrawer(null)}
        onSelect={selectConversation}
        onNewChat={newChat}
        onDelete={store.remove}
        onRename={store.rename}
        onTogglePin={store.togglePin}
        onClearAll={store.clearAll}
        apiUrl={API_URL}
        backendState={backendState}
      />

      <main className={cn("flex min-w-0 flex-1 flex-col", panel && "hidden lg:flex")}>
        <Header
          providers={providers}
          model={model}
          onModelChange={setModel}
          backendState={backendState}
          onMenu={() => setDrawer("history")}
          onNewChat={newChat}
          onShare={share}
          shareDisabled={!active || messages.length === 0}
        />

        {backendState === "waking" && (
          <div className="mx-auto mb-1 flex items-center gap-2 rounded-full bg-amber-500/10 px-3 py-1 text-xs text-amber-700 dark:text-amber-400">
            <Loader2 className="size-3.5 animate-spin" />
            Waking up the server, the first response can take up to a minute.
          </div>
        )}
        {backendState === "offline" && (
          <div className="mx-auto mb-1 rounded-full bg-red-500/10 px-3 py-1 text-xs text-red-600 dark:text-red-400">
            The server is unreachable right now. Messages will retry when you send them.
          </div>
        )}

        {messages.length === 0 ? (
          <EmptyState onPick={send} />
        ) : (
          <Thread messages={messages} onRegenerate={regenerate} onFeedback={feedback} onAskAbout={openPanel} />
        )}

        <div className="mx-auto w-full max-w-3xl px-3 pb-2 md:px-6">
          <Composer
            onSend={send}
            onStop={() => activeId && stop(activeId)}
            busy={busy}
            autoFocus
            knowledgeBase={knowledgeBase}
            onToggleKnowledgeBase={() => setKnowledgeBase((v) => !v)}
          />
          <p className="py-2 text-center text-[11px] text-faint">
            AI-generated, for reference only. Verify critical commands before running them.
          </p>
        </div>
      </main>

      {panel && (
        <aside className="flex w-full min-w-0 animate-slide-in-right flex-col border-l border-line bg-panel lg:w-[420px] lg:shrink-0 xl:w-[460px]">
          <PanelHeader
            providers={providers}
            model={panelModel}
            onModelChange={setPanelModel}
            onClose={() => {
              stop(PANEL_KEY);
              setPanel(null);
            }}
          />
          <Thread
            compact
            messages={panel.messages}
            header={
              panel.messages.length === 0 ? (
                <div className="flex items-start gap-2 rounded-2xl border border-line bg-subtle px-4 py-3 text-sm text-muted">
                  <CornerDownRight className="mt-0.5 size-4 shrink-0" />
                  <span className="line-clamp-6">{panel.quote}</span>
                </div>
              ) : null
            }
          />
          <div className="px-3 pb-3">
            <Composer
              compact
              autoFocus
              onSend={sendInPanel}
              onStop={() => stop(PANEL_KEY)}
              busy={!!panelBusy}
              placeholder="Ask about this excerpt"
            />
            <p className="pt-2 text-center text-[11px] text-faint">AI-generated, for reference only</p>
          </div>
        </aside>
      )}

      {toast && (
        <div className="fixed bottom-24 left-1/2 z-50 -translate-x-1/2 animate-fade-in rounded-lg bg-neutral-900 px-4 py-2 text-sm text-white shadow-lg dark:bg-white dark:text-neutral-900">
          {toast}
        </div>
      )}
    </div>
  );
}
