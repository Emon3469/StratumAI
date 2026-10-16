import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ChatMessage, StreamEvent } from "@/lib/types";

const { streamChat } = vi.hoisted(() => ({ streamChat: vi.fn() }));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, streamChat: (...args: unknown[]) => streamChat(...args) };
});

const { useStreamingReply } = await import("./useStreamingReply");
const { ApiError } = await import("@/lib/api");

function harness() {
  let message: ChatMessage = { id: "a", role: "assistant", content: "", createdAt: 0, status: "streaming" };
  const patch = (fn: (m: ChatMessage) => ChatMessage) => {
    message = fn(message);
  };
  return { patch, get: () => message };
}

beforeEach(() => {
  streamChat.mockReset();
});
afterEach(() => vi.useRealTimers());

describe("useStreamingReply", () => {
  it("accumulates tokens, sources and metadata", async () => {
    streamChat.mockImplementation(async (_payload, onEvent: (e: StreamEvent) => void) => {
      onEvent({ event: "status", data: { stage: "retrieving", message: "Searching" } });
      onEvent({ event: "sources", data: { items: [{ id: 1, source: "a.docx", source_type: "true", score: 0.9, snippet: "x" }] } });
      onEvent({ event: "model", data: { provider: "groq", model: "m", cached: false, fallbacks: 1 } });
      onEvent({ event: "token", data: { content: "Hello" } });
      onEvent({ event: "token", data: { content: " there" } });
      onEvent({ event: "done", data: { provider: "groq", latency_ms: 900, ttft_ms: 300 } });
    });
    const h = harness();
    const { result } = renderHook(() => useStreamingReply());
    await act(() => result.current.run("c1", { message: "q", history: [] }, h.patch));
    const m = h.get();
    expect(m.content).toBe("Hello there");
    expect(m.status).toBe("done");
    expect(m.stage).toBeUndefined();
    expect(m.sources).toHaveLength(1);
    expect(m.meta).toMatchObject({ provider: "groq", fallbacks: 1, ttft_ms: 300 });
  });

  it("shows the server error message when nothing was streamed", async () => {
    streamChat.mockImplementation(async (_p, onEvent: (e: StreamEvent) => void) => {
      onEvent({ event: "error", data: { message: "All providers failed" } });
    });
    const h = harness();
    const { result } = renderHook(() => useStreamingReply());
    await act(() => result.current.run("c1", { message: "q", history: [] }, h.patch));
    expect(h.get()).toMatchObject({ status: "error", content: "All providers failed" });
  });

  it("explains rate limiting", async () => {
    streamChat.mockRejectedValue(new ApiError("Too many requests.", 429));
    const h = harness();
    const { result } = renderHook(() => useStreamingReply());
    await act(() => result.current.run("c1", { message: "q", history: [] }, h.patch));
    expect(h.get().status).toBe("error");
    expect(h.get().content).toMatch(/too quickly/);
  });

  it("explains network failures", async () => {
    streamChat.mockRejectedValue(new TypeError("Failed to fetch"));
    const h = harness();
    const { result } = renderHook(() => useStreamingReply());
    await act(() => result.current.run("c1", { message: "q", history: [] }, h.patch));
    expect(h.get().content).toMatch(/couldn't reach the server/);
  });

  it("marks the reply as stopped and keeps partial text when aborted", async () => {
    streamChat.mockImplementation(
      (_p, onEvent: (e: StreamEvent) => void, signal: AbortSignal) =>
        new Promise((_, reject) => {
          onEvent({ event: "token", data: { content: "Partial" } });
          signal.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
        }),
    );
    const h = harness();
    const { result } = renderHook(() => useStreamingReply());
    let pending: Promise<void> = Promise.resolve();
    act(() => {
      pending = result.current.run("c1", { message: "q", history: [] }, h.patch);
    });
    act(() => result.current.stop("c1"));
    await act(() => pending);
    expect(h.get()).toMatchObject({ status: "stopped", content: "Partial" });
  });

  it("aborts the previous request when a new one starts on the same key", async () => {
    const signals: AbortSignal[] = [];
    streamChat.mockImplementation(
      (_p, _on, signal: AbortSignal) =>
        new Promise<void>((resolve) => {
          signals.push(signal);
          signal.addEventListener("abort", () => resolve());
          setTimeout(resolve, 10);
        }),
    );
    const { result } = renderHook(() => useStreamingReply());
    await act(async () => {
      const first = result.current.run("c1", { message: "1", history: [] }, harness().patch);
      const second = result.current.run("c1", { message: "2", history: [] }, harness().patch);
      await Promise.all([first, second]);
    });
    expect(signals[0].aborted).toBe(true);
    expect(signals[1].aborted).toBe(false);
  });
});
