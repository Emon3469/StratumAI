import type { ChatMessage, ProviderInfo, StreamEvent } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export interface ChatPayload {
  message: string;
  history: Pick<ChatMessage, "role" | "content">[];
  provider?: string | null;
  use_knowledge_base?: boolean;
  regenerate?: boolean;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
  ) {
    super(message);
  }
}

export async function pingBackend(signal?: AbortSignal): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/health`, { signal, cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchProviders(signal?: AbortSignal): Promise<ProviderInfo[]> {
  const res = await fetch(`${API_URL}/api/models`, { signal, cache: "no-store" });
  if (!res.ok) throw new ApiError("Could not load models", res.status);
  const data = (await res.json()) as { providers: ProviderInfo[] };
  return data.providers;
}

export function parseBlock(block: string): StreamEvent | null {
  let event = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  if (!data.length) return null;
  try {
    return { event, data: JSON.parse(data.join("\n")) } as StreamEvent;
  } catch {
    return null;
  }
}

export async function streamChat(
  payload: ChatPayload,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!res.ok || !res.body) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {}
    throw new ApiError(detail, res.status);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const parsed = parseBlock(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      if (parsed) onEvent(parsed);
      boundary = buffer.indexOf("\n\n");
    }
  }
  const tail = parseBlock(buffer.trim());
  if (tail) onEvent(tail);
}
