import { Gauge } from "lucide-react";
import type { ApiError } from "../../lib/api";
import { cn } from "../../lib/cn";
import type { MetaOut, UsageOut } from "../../lib/types";
import { Skeleton } from "../ui/Skeleton";
import { cardClasses } from "../ui/styles";

function Meter({ used, limit, label }: { used: number; limit: number; label: string }) {
  const ratio = limit > 0 ? Math.min(1, used / limit) : 1;
  const tone = ratio >= 1 ? "bg-danger" : ratio >= 0.8 ? "bg-warning" : "bg-accent-solid";
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="text-fg-muted">{label}</span>
        <span className="font-medium tabular-nums">
          {used} / {limit}
        </span>
      </div>
      <div aria-hidden="true" className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-muted">
        <div className={cn("h-full rounded-full", tone)} style={{ width: `${Math.round(ratio * 100)}%` }} />
      </div>
    </div>
  );
}

interface QuotaCardProps {
  usage: UsageOut | null;
  error: ApiError | null;
  meta: MetaOut | null;
}

/** Remaining quota from `GET /api/v1/usage` (rolling 24 hours, per visitor and per instance). */
export function QuotaCard({ usage, error, meta }: QuotaCardProps) {
  const remaining = usage ? Math.max(0, usage.jobs_per_ip_per_day - usage.jobs_today) : null;

  return (
    <section aria-labelledby="quota-heading" className={cn(cardClasses, "p-5")}>
      <h2 id="quota-heading" className="flex items-center gap-2 text-sm font-semibold">
        <Gauge aria-hidden="true" className="size-4 text-fg-subtle" />
        Free-tier quota
      </h2>
      {usage ? (
        <div className="mt-4 space-y-4">
          <p className="text-sm">
            <span className="text-2xl font-semibold tabular-nums">{remaining}</span>{" "}
            <span className="text-fg-muted">research {remaining === 1 ? "run" : "runs"} left for you</span>
          </p>
          <Meter used={usage.jobs_today} limit={usage.jobs_per_ip_per_day} label="Your runs, last 24 h" />
          <Meter
            used={usage.global_jobs_today}
            limit={usage.global_jobs_per_day}
            label="Whole instance, last 24 h"
          />
          <p className="text-xs leading-5 text-fg-muted">
            {usage.active_jobs} of {usage.max_concurrent_jobs} running · {usage.queued_jobs} waiting in the queue
            {meta ? ` · up to ${meta.limits.jobs_per_ip_per_hour} runs per hour per visitor` : ""}. Repeating a
            recent identical request reuses its report and does not use quota.
          </p>
        </div>
      ) : error ? (
        <p className="mt-3 text-sm text-fg-muted">Quota information is unavailable right now.</p>
      ) : (
        <div className="mt-4 space-y-3" aria-hidden="true">
          <Skeleton className="h-7 w-40" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
        </div>
      )}
    </section>
  );
}
