import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={cn("shrink-0", className)} aria-hidden="true">
      <defs>
        <linearGradient id="stratum-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#34d399" />
          <stop offset="1" stopColor="#0d9488" />
        </linearGradient>
      </defs>
      <path d="M32 10 54 21 32 32 10 21Z" fill="url(#stratum-g)" />
      <path d="M13.8 30 32 39.1 50.2 30 54 32 32 43 10 32Z" fill="#2dd4bf" opacity=".85" />
      <path d="M13.8 41 32 50.1 50.2 41 54 43 32 54 10 43Z" fill="#5eead4" opacity=".7" />
    </svg>
  );
}

export function Avatar({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-full border border-line bg-elevated",
        className,
      )}
    >
      <LogoMark className="size-5" />
    </span>
  );
}
