import { Activity, Clock, Gauge, ListChecks } from "lucide-react";
import { LogoMark } from "./Logo";

const SUGGESTIONS = [
  { icon: Clock, title: "Schedule a CronJob", prompt: "How do I create a Kubernetes CronJob that runs every 5 minutes?" },
  { icon: Gauge, title: "Autoscale pods", prompt: "How does the Horizontal Pod Autoscaler decide when to scale my deployment?" },
  { icon: ListChecks, title: "Work queues", prompt: "How do I process a work queue in parallel with a Kubernetes Job and Redis?" },
  { icon: Activity, title: "Monitor a Job", prompt: "What commands should I use to monitor a running Job and read its logs?" },
];

export function EmptyState({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 pb-6">
      <div className="mb-8 flex flex-col items-center gap-4 text-center">
        <span className="flex size-14 items-center justify-center rounded-2xl border border-line bg-elevated shadow-sm">
          <LogoMark className="size-9" />
        </span>
        <h1 className="text-2xl font-semibold tracking-tight md:text-[28px]">What are we shipping today?</h1>
        <p className="max-w-md text-sm text-muted">
          Grounded answers on Kubernetes workloads, infrastructure and systems engineering, with sources you can check.
        </p>
      </div>
      <div className="grid w-full max-w-2xl grid-cols-1 gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map(({ icon: Icon, title, prompt }) => (
          <button
            key={title}
            type="button"
            onClick={() => onPick(prompt)}
            className="group flex items-start gap-3 rounded-2xl border border-line p-3.5 text-left transition-colors hover:bg-hover"
          >
            <Icon className="mt-0.5 size-4 shrink-0 text-accent" />
            <span className="min-w-0">
              <span className="block text-sm font-medium">{title}</span>
              <span className="line-clamp-1 text-xs text-muted">{prompt}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
