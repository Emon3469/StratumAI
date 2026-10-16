"use client";

import { useEffect, useState } from "react";
import { fetchProviders, pingBackend } from "@/lib/api";
import type { ProviderInfo } from "@/lib/types";

export type BackendState = "connecting" | "waking" | "online" | "offline";

export function useBackend() {
  const [state, setState] = useState<BackendState>("connecting");
  const [providers, setProviders] = useState<ProviderInfo[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    const slow = setTimeout(() => !cancelled && setState((s) => (s === "connecting" ? "waking" : s)), 2500);

    (async () => {
      for (let attempt = 0; attempt < 12 && !cancelled; attempt++) {
        if (await pingBackend(controller.signal)) {
          if (cancelled) return;
          setState("online");
          try {
            setProviders(await fetchProviders(controller.signal));
          } catch {}
          return;
        }
        await new Promise((r) => setTimeout(r, Math.min(2000 + attempt * 1000, 6000)));
      }
      if (!cancelled) setState("offline");
    })();

    return () => {
      cancelled = true;
      clearTimeout(slow);
      controller.abort();
    };
  }, []);

  return { state, providers };
}
