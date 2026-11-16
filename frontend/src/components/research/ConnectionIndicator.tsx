import { cn } from "../../lib/cn";
import type { ConnectionState } from "../../lib/jobState";
import { Spinner } from "../ui/Spinner";

const LABELS: Record<ConnectionState, string> = {
  connecting: "Connecting to server…",
  live: "Live",
  reconnecting: "Connection lost, reconnecting…",
  polling: "Live stream unavailable, checking every few seconds",
  closed: "Up to date",
};

/** Honest state of the live-update channel while a job is in progress. */
export function ConnectionIndicator({ connection }: { connection: ConnectionState }) {
  const waiting = connection === "connecting" || connection === "reconnecting";
  return (
    <span className="inline-flex items-center gap-2 text-xs text-fg-muted">
      {waiting ? (
        <Spinner className="size-3.5" />
      ) : (
        <span
          aria-hidden="true"
          className={cn(
            "size-2 rounded-full",
            connection === "live" ? "bg-success motion-safe:animate-pulse" : "bg-warning",
          )}
        />
      )}
      {LABELS[connection]}
    </span>
  );
}
