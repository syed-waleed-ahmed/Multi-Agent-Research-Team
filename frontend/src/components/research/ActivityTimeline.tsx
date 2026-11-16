import {
  Ban,
  CircleCheck,
  CircleDot,
  CircleX,
  Clock,
  Cpu,
  ArrowRightLeft,
  Play,
  RotateCcw,
  Search,
  SearchX,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useRef } from "react";
import { cn } from "../../lib/cn";
import { formatTime } from "../../lib/format";
import { buildTimeline, type ConnectionState, type TimelineItem, type TimelineKind, type TimelineTone } from "../../lib/jobState";
import { stageInfo } from "../../lib/labels";
import type { EventOut } from "../../lib/types";
import { Spinner } from "../ui/Spinner";
import { cardClasses } from "../ui/styles";

const KIND_ICONS: Record<TimelineKind, typeof Search> = {
  queued: Clock,
  run: Play,
  stage_started: CircleDot,
  stage_completed: CircleCheck,
  stage_failed: CircleX,
  llm: Cpu,
  search: Search,
  search_failed: SearchX,
  retry: RotateCcw,
  fallback: ArrowRightLeft,
  completed: Sparkles,
  failed: CircleX,
  cancelled: Ban,
  other: CircleDot,
};

const TONE_STYLES: Record<TimelineTone, string> = {
  neutral: "bg-surface-muted text-fg-muted",
  info: "bg-accent-soft text-accent-soft-fg",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
};

function TimelineEntry({ item }: { item: TimelineItem }) {
  const Icon = KIND_ICONS[item.kind];
  const stageAgent = item.stage ? stageInfo(item.stage).agent : null;
  // Stage events already name their agent ("Research Agent started").
  const agent = stageAgent && !item.title.includes(stageAgent) ? stageAgent : null;
  return (
    <li className="relative flex gap-3 pb-4 last:pb-0" data-kind={item.kind}>
      <span
        aria-hidden="true"
        className="absolute top-8 bottom-0 left-[0.9375rem] w-px bg-line [li:last-child>&]:hidden"
      />
      <span className={cn("relative flex size-8 shrink-0 items-center justify-center rounded-full", TONE_STYLES[item.tone])}>
        <Icon aria-hidden="true" className="size-4" />
      </span>
      <div className="min-w-0 flex-1 pt-1">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <p className="text-sm font-medium break-words text-fg">{item.title}</p>
          {agent && <span className="text-xs text-fg-subtle">{agent}</span>}
        </div>
        {item.detail && <p className="mt-0.5 text-sm break-words text-fg-muted">{item.detail}</p>}
      </div>
      <time dateTime={item.timestamp} className="shrink-0 pt-1 text-xs text-fg-subtle tabular-nums">
        {formatTime(item.timestamp)}
      </time>
    </li>
  );
}

interface ActivityTimelineProps {
  events: EventOut[];
  connection: ConnectionState;
  active: boolean;
}

/** The real event log of the run: searches, model requests, retries, fallbacks and errors. */
export function ActivityTimeline({ events, connection, active }: ActivityTimelineProps) {
  const items = useMemo(() => buildTimeline(events), [events]);
  const listRef = useRef<HTMLDivElement>(null);

  // Keep the newest entry in view while the run is live, unless the reader scrolled up.
  useEffect(() => {
    const container = listRef.current;
    if (!container || !active) return;
    const distance = container.scrollHeight - container.scrollTop - container.clientHeight;
    if (distance < 160) container.scrollTop = container.scrollHeight;
  }, [items.length, active]);

  const searches = events.filter((event) => event.type === "search").length;

  return (
    <section aria-labelledby="activity-heading" className={cn(cardClasses, "print:hidden")}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-5 py-3.5">
        <h2 id="activity-heading" className="text-sm font-semibold">
          Activity
        </h2>
        <p className="text-xs text-fg-subtle">
          {items.length > 0 ? `${events.length} events · ${searches} web ${searches === 1 ? "search" : "searches"}` : ""}
        </p>
      </div>
      <div ref={listRef} className="max-h-[26rem] overflow-y-auto px-5 py-4">
        {items.length === 0 ? (
          <p className="flex items-center gap-2 text-sm text-fg-muted">
            {connection === "connecting" || connection === "reconnecting" ? (
              <>
                <Spinner />
                Connecting to the activity stream…
              </>
            ) : (
              "No activity recorded yet."
            )}
          </p>
        ) : (
          <ol aria-label="Run events">
            {items.map((item) => (
              <TimelineEntry key={item.key} item={item} />
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}
