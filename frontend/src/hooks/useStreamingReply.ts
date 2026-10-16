"use client";

import { useCallback, useEffect, useRef } from "react";
import { ApiError, streamChat, type ChatPayload } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

type Patch = (update: (message: ChatMessage) => ChatMessage) => void;

const NETWORK_ERROR =
  "I couldn't reach the server. It may be waking up after a period of inactivity, please try again in a moment.";

export function useStreamingReply() {
  const controllers = useRef(new Map<string, AbortController>());

  useEffect(() => {
    const active = controllers.current;
    return () => active.forEach((controller) => controller.abort());
  }, []);

  const stop = useCallback((key: string) => {
    controllers.current.get(key)?.abort();
  }, []);

  const isRunning = useCallback((key: string) => controllers.current.has(key), []);

  const run = useCallback(async (key: string, payload: ChatPayload, patch: Patch) => {
    controllers.current.get(key)?.abort();
    const controller = new AbortController();
    controllers.current.set(key, controller);

    let buffer = "";
    let frame: ReturnType<typeof setTimeout> | null = null;
    const flush = () => {
      frame = null;
      if (!buffer) return;
      const chunk = buffer;
      buffer = "";
      patch((m) => ({ ...m, content: m.content + chunk, stage: undefined }));
    };
    const schedule = () => {
      if (!frame) frame = setTimeout(flush, 24);
    };

    try {
      await streamChat(
        payload,
        (evt) => {
          switch (evt.event) {
            case "status":
              patch((m) => (m.content ? m : { ...m, stage: evt.data.message }));
              break;
            case "sources":
              patch((m) => ({ ...m, sources: evt.data.items }));
              break;
            case "model":
              patch((m) => ({ ...m, meta: { ...m.meta, ...evt.data } }));
              break;
            case "token":
              buffer += evt.data.content;
              schedule();
              break;
            case "done":
              if (frame) clearTimeout(frame);
              flush();
              patch((m) => ({ ...m, status: "done", stage: undefined, meta: { ...m.meta, ...evt.data } }));
              break;
            case "error":
              if (frame) clearTimeout(frame);
              flush();
              patch((m) => ({
                ...m,
                status: "error",
                stage: undefined,
                content: m.content || evt.data.message,
              }));
              break;
          }
        },
        controller.signal,
      );
      if (frame) clearTimeout(frame);
      flush();
      patch((m) => (m.status === "streaming" ? { ...m, status: "done", stage: undefined } : m));
    } catch (error) {
      if (frame) clearTimeout(frame);
      flush();
      if (controller.signal.aborted) {
        patch((m) => ({ ...m, status: "stopped", stage: undefined }));
      } else {
        const message =
          error instanceof ApiError && error.status === 429
            ? "You're sending messages a little too quickly. Please wait a moment and try again."
            : error instanceof ApiError
              ? error.message
              : NETWORK_ERROR;
        patch((m) => ({ ...m, status: "error", stage: undefined, content: m.content || message }));
      }
    } finally {
      if (controllers.current.get(key) === controller) controllers.current.delete(key);
    }
  }, []);

  return { run, stop, isRunning };
}
