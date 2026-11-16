import {
  Ban,
  CircleCheck,
  CircleDashed,
  CircleMinus,
  CircleX,
  ClipboardCheck,
  CodeXml,
  LoaderCircle,
  Search,
} from "lucide-react";
import { useNow } from "../../hooks/useNow";
import { parseServerDate, serverNow } from "../../lib/clock";
import { cn } from "../../lib/cn";
import { formatClock, formatDuration, formatTime } from "../../lib/format";
import { STAGE_STATUS_LABEL, stageInfo } from "../../lib/labels";
import type { StageOut, StageStatus } from "../../lib/types";

const STAGE_ICONS: Record<string, typeof Search> = {
  research: Search,
  coding: CodeXml,
  synthesis: ClipboardCheck,
};

const STATUS_STYLE: Record<StageStatus, { badge: string; Icon: typeof Search; card: string }> = {
  pending: { badge: "text-fg-subtle", Icon: CircleDashed, card: "border-line" },
  running: { badge: "text-accent", Icon: LoaderCircle, card: "border-accent-solid ring-1 ring-accent-solid/30" },
  completed: { badge: "text-success", Icon: CircleCheck, card: "border-line" },
  failed: { badge: "text-danger", Icon: CircleX, card: "border-danger-line" },
  cancelled: { badge: "text-fg-muted", Icon: Ban, card: "border-line" },
};

interface AgentCardProps {
  stage: StageOut;
  /** 1-based position in the pipeline. */
  step: number;
  /** The job has ended: a stage still pending will never run. */
  jobFinished?: boolean;
}

/** One agent's real status, timing and counters, straight from the job snapshot. */
export function AgentCard({ stage, step, jobFinished = false }: AgentCardProps) {
  const running = stage.status === "running";
  const now = useNow(1000, running);
  const info = stageInfo(stage.stage);
  const StageIcon = STAGE_ICONS[stage.stage] ?? Search;
  const skipped = jobFinished && stage.status === "pending";
  const { badge, Icon, card } = skipped
    ? { badge: "text-fg-subtle", Icon: CircleMinus, card: "border-line" }
    : STATUS_STYLE[stage.status];
  const statusLabel = skipped ? "Not run" : STAGE_STATUS_LABEL[stage.status];

  const started = parseServerDate(stage.started_at);
  const finished = parseServerDate(stage.finished_at);
  let timing: { label: string; value: string } | null = null;
  if (started !== null && running) {
    timing = { label: "Elapsed", value: formatClock((serverNow(now) - started) / 1000) };
  } else if (started !== null && finished !== null) {
    const label = stage.status === "completed" ? "Took" : "Ran for";
    timing = { label, value: formatDuration(Math.max(0, finished - started) / 1000) };
  }

  return (
    <article
      aria-labelledby={`agent-${stage.stage}-name`}
      data-stage={stage.stage}
      data-status={stage.status}
      className={cn("flex h-full flex-col rounded-xl border bg-surface p-4 shadow-xs transition-colors", card)}
    >
      <div className="flex items-center justify-between gap-3">
        <span
          className={cn(
            "flex size-9 shrink-0 items-center justify-center rounded-lg",
            running ? "bg-accent-soft text-accent-soft-fg" : "bg-surface-muted text-fg-muted",
          )}
        >
          <StageIcon aria-hidden="true" className="size-4.5" />
        </span>
        <span className={cn("inline-flex items-center gap-1.5 text-sm font-medium", badge)}>
          <Icon aria-hidden="true" className={cn("size-4", running && "motion-safe:animate-spin")} />
          {statusLabel}
        </span>
      </div>

      <p className="mt-3 text-xs font-medium text-fg-subtle">Step {step}</p>
      <h3 id={`agent-${stage.stage}-name`} className="font-semibold">
        {stage.agent || info.agent}
      </h3>
      {info.role && <p className="mt-1 text-sm leading-6 text-fg-muted">{info.role}</p>}

      <div className="mt-auto pt-4">
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 border-t border-line pt-3 text-sm">
          <div>
            <dt className="text-xs text-fg-subtle">Started</dt>
            <dd className="tabular-nums">{started !== null ? formatTime(stage.started_at) : "Not yet"}</dd>
          </div>
          <div>
            <dt className="text-xs text-fg-subtle">{timing?.label ?? "Duration"}</dt>
            <dd className="tabular-nums" aria-live="off">
              {timing?.value ?? "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-fg-subtle">Web searches</dt>
            <dd className="tabular-nums">{stage.searches}</dd>
          </div>
          <div>
            <dt className="text-xs text-fg-subtle">Model requests</dt>
            <dd className="tabular-nums">{stage.llm_calls}</dd>
          </div>
          {stage.attempts > 1 && (
            <div className="col-span-2">
              <dt className="sr-only">Attempts</dt>
              <dd className="text-xs text-warning">Attempt {stage.attempts} (switched provider after an error)</dd>
            </div>
          )}
        </dl>
      </div>
    </article>
  );
}
