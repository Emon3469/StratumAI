import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, parseBlock, streamChat } from "./api";
import type { StreamEvent } from "./types";

function sseResponse(chunks: string[], status = 200) {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      chunks.forEach((c) => controller.enqueue(encoder.encode(c)));
      controller.close();
    },
  });
  return new Response(body, { status, headers: { "Content-Type": "text/event-stream" } });
}

afterEach(() => vi.restoreAllMocks());

describe("parseBlock", () => {
  it("parses an event with JSON data", () => {
    expect(parseBlock('event: token\ndata: {"content":"hi"}')).toEqual({ event: "token", data: { content: "hi" } });
  });

  it("ignores blocks without data or with invalid JSON", () => {
    expect(parseBlock(": keep-alive")).toBeNull();
    expect(parseBlock("event: token\ndata: {oops")).toBeNull();
  });
});

describe("streamChat", () => {
  it("reassembles events split across network chunks and CRLF line endings", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      sseResponse([
        'event: ready\r\ndata: {"request_id":"1"}\r\n\r\nevent: tok',
        'en\ndata: {"content":"Hel"}\n\nevent: token\ndata: {"con',
        'tent":"lo"}\n\nevent: done\ndata: {"provider":"groq","latency_ms":10}',
      ]),
    );
    const events: StreamEvent[] = [];
    await streamChat({ message: "hi", history: [] }, (e) => events.push(e));
    expect(events.map((e) => e.event)).toEqual(["ready", "token", "token", "done"]);
    const text = events.flatMap((e) => (e.event === "token" ? [e.data.content] : [])).join("");
    expect(text).toBe("Hello");
  });

  it("sends the payload as JSON to the stream endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(sseResponse([]));
    await streamChat({ message: "q", history: [{ role: "user", content: "a" }], provider: "groq" }, () => {});
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/chat\/stream$/);
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({ message: "q", history: [{ role: "user", content: "a" }], provider: "groq" });
  });

  it("raises ApiError with the server detail on HTTP errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Too many requests." }), { status: 429 }),
    );
    await expect(streamChat({ message: "q", history: [] }, () => {})).rejects.toMatchObject({
      status: 429,
      message: "Too many requests.",
    });
  });

  it("falls back to a generic message when the error body is not JSON", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("Bad Gateway", { status: 502 }));
    const error = await streamChat({ message: "q", history: [] }, () => {}).catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toContain("502");
  });
});
