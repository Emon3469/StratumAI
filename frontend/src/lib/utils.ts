export { clsx as cn } from "clsx";

export function uid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export function titleFrom(text: string): string {
  const clean = text.replace(/\s+/g, " ").trim();
  return clean.length > 48 ? `${clean.slice(0, 48).trimEnd()}…` : clean || "New chat";
}

export function formatSource(name: string): string {
  return name.replace(/\.(pdf|docx|pptx|html?|txt|md)$/i, "").replace(/[_-]+/g, " ");
}

export function relativeGroup(timestamp: number, now = Date.now()): string {
  const day = 86_400_000;
  const startOfToday = new Date(now).setHours(0, 0, 0, 0);
  if (timestamp >= startOfToday) return "Today";
  if (timestamp >= startOfToday - day) return "Yesterday";
  if (timestamp >= startOfToday - 7 * day) return "Previous 7 days";
  if (timestamp >= startOfToday - 30 * day) return "Previous 30 days";
  return "Older";
}
