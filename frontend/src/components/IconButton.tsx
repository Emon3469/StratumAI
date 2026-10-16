import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  active?: boolean;
  tooltipSide?: "top" | "bottom" | "right";
}

export function IconButton({ label, active, tooltipSide = "bottom", className, children, ...rest }: Props) {
  return (
    <button
      type="button"
      aria-label={label}
      className={cn(
        "group/btn relative inline-flex size-9 items-center justify-center rounded-lg text-muted transition-colors",
        "hover:bg-hover hover:text-fg focus-visible:outline-2 focus-visible:outline-accent disabled:pointer-events-none disabled:opacity-40",
        active && "bg-hover text-fg",
        className,
      )}
      {...rest}
    >
      {children}
      <span
        role="tooltip"
        className={cn(
          "pointer-events-none absolute z-50 hidden whitespace-nowrap rounded-md bg-neutral-900 px-2 py-1 text-xs font-medium text-white opacity-0 shadow-lg transition-opacity delay-300 group-hover/btn:opacity-100 md:block dark:bg-black",
          tooltipSide === "bottom" && "top-full left-1/2 mt-1.5 -translate-x-1/2",
          tooltipSide === "top" && "bottom-full left-1/2 mb-1.5 -translate-x-1/2",
          tooltipSide === "right" && "left-full top-1/2 ml-2 -translate-y-1/2",
        )}
      >
        {label}
      </span>
    </button>
  );
}
