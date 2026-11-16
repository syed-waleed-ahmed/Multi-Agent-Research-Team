import { Ban, CircleCheck, CircleX, Clock, LoaderCircle } from "lucide-react";
import { cn } from "../../lib/cn";
import { JOB_STATUS_LABEL } from "../../lib/labels";
import type { JobStatus } from "../../lib/types";
import { Badge, type Tone } from "../ui/Badge";

const STYLE: Record<JobStatus, { tone: Tone; Icon: typeof Clock }> = {
  queued: { tone: "neutral", Icon: Clock },
  running: { tone: "accent", Icon: LoaderCircle },
  succeeded: { tone: "success", Icon: CircleCheck },
  failed: { tone: "danger", Icon: CircleX },
  cancelled: { tone: "neutral", Icon: Ban },
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  const { tone, Icon } = STYLE[status];
  return (
    <Badge tone={tone} size="md">
      <Icon aria-hidden="true" className={cn("size-3.5", status === "running" && "motion-safe:animate-spin")} />
      <span data-testid="job-status">{JOB_STATUS_LABEL[status]}</span>
    </Badge>
  );
}
