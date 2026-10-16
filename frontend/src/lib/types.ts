export type Role = "user" | "assistant";

export type MessageStatus = "streaming" | "done" | "error" | "stopped";

export interface Source {
  id: number;
  source: string;
  source_type: string;
  score: number;
  snippet: string;
}

export interface MessageMeta {
  provider?: string | null;
  model?: string | null;
  intent?: string | null;
  plan?: string[];
  cached?: boolean;
  fallbacks?: number;
  latency_ms?: number;
  ttft_ms?: number | null;
}

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  createdAt: number;
  quote?: string;
  status?: MessageStatus;
  stage?: string;
  sources?: Source[];
  meta?: MessageMeta;
  feedback?: "up" | "down" | null;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  pinned?: boolean;
  messages: ChatMessage[];
}

export interface ProviderInfo {
  id: string;
  label: string;
  model: string;
  healthy: boolean;
}

export type StreamEvent =
  | { event: "ready"; data: { request_id: string } }
  | { event: "status"; data: { stage: string; message: string } }
  | { event: "sources"; data: { items: Source[] } }
  | { event: "model"; data: { provider: string; model: string; cached: boolean; fallbacks: number } }
  | { event: "token"; data: { content: string } }
  | { event: "done"; data: MessageMeta }
  | { event: "error"; data: { message: string } };
