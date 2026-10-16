"use client";

import { useSyncExternalStore } from "react";
import { ChatApp } from "./ChatApp";
import { LogoMark } from "./Logo";

const subscribe = () => () => {};

export function ClientApp() {
  const mounted = useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );

  if (mounted) return <ChatApp />;

  return (
    <div className="flex h-dvh w-full bg-bg">
      <div className="hidden w-[60px] shrink-0 border-r border-line bg-rail md:block" />
      <div className="flex flex-1 flex-col items-center justify-center gap-3">
        <LogoMark className="size-10 animate-pulse" />
      </div>
    </div>
  );
}
