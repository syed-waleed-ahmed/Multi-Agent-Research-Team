import { CircleStop } from "lucide-react";
import { useNow } from "../../hooks/useNow";
import { formatDateTime, formatRelative } from "../../lib/format";
import { DEPTH_INFO, REPORT_STYLE_INFO } from "../../lib/labels";
import type { ConnectionState } from "../../lib/jobState";
import { isActive, type JobOut } from "../../lib/types";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Spinner } from "../ui/Spinner";
import { ConnectionIndicator } from "./ConnectionIndicator";
import { JobStatusBadge } from "./JobStatusBadge";

interface JobHeaderProps {
  job: JobOut;
  connection: ConnectionState;
  cached: boolean;
  /** Shown only when this browser holds the owner token and the job is active. */
  onCancel: (() => void) | null;
  cancelling: boolean;
}

export function JobHeader({ job, connection, cached, onCancel, cancelling }: JobHeaderProps) {
  const now = useNow(30_000);
  const active = isActive(job.status);

  return (
    <header className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <JobStatusBadge status={job.status} />
        {cached && <Badge tone="accent">Served from cache</Badge>}
        {active && <ConnectionIndicator connection={connection} />}
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <h1 className="min-w-0 text-2xl font-semibold tracking-tight break-words sm:text-3xl">{job.topic}</h1>
        {onCancel && active && (
          <Button variant="danger" onClick={onCancel} disabled={cancelling} className="self-start print:hidden">
            {cancelling ? <Spinner /> : <CircleStop aria-hidden="true" className="size-4" />}
            {cancelling ? "Cancelling…" : "Cancel run"}
          </Button>
        )}
      </div>

      <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm print:hidden">
        <div className="flex gap-1.5">
          <dt className="text-fg-subtle">Depth</dt>
          <dd className="font-medium">{DEPTH_INFO[job.options.depth].label}</dd>
        </div>
        <div className="flex gap-1.5">
          <dt className="text-fg-subtle">Style</dt>
          <dd className="font-medium">{REPORT_STYLE_INFO[job.options.report_style].label}</dd>
        </div>
        <div className="flex min-w-0 gap-1.5">
          <dt className="text-fg-subtle">Model</dt>
          <dd className="truncate font-medium">{job.options.model}</dd>
        </div>
        <div className="flex gap-1.5">
          <dt className="text-fg-subtle">Created</dt>
          <dd className="font-medium" title={formatDateTime(job.created_at)}>
            <time dateTime={job.created_at}>{formatRelative(job.created_at, now)}</time>
          </dd>
        </div>
      </dl>

      {job.options.instructions && (
        <p className="rounded-lg border border-line bg-surface-muted px-3 py-2 text-sm break-words text-fg-muted print:hidden">
          <span className="font-medium text-fg">Instructions:</span> {job.options.instructions}
        </p>
      )}
    </header>
  );
}
