import { ClockFading, Trash } from "lucide-react";
import { NavLink } from "react-router";
import { useHistory } from "../../hooks/useHistory";
import { useNow } from "../../hooks/useNow";
import { cn } from "../../lib/cn";
import { formatDateTime, formatRelative } from "../../lib/format";
import { historyStore } from "../../lib/history";
import { cardClasses } from "../ui/styles";

/** "Your recent research": jobs started in this browser (stored locally). */
export function HistoryList() {
  const entries = useHistory();
  const now = useNow(60_000);
  const persistent = historyStore.isPersistent();

  return (
    <section aria-labelledby="history-heading" className={cn(cardClasses, "p-5")}>
      <h2 id="history-heading" className="flex items-center gap-2 text-sm font-semibold">
        <ClockFading aria-hidden="true" className="size-4 text-fg-subtle" />
        Your recent research
        {entries.length > 0 && <span className="font-normal text-fg-subtle">({entries.length})</span>}
      </h2>

      {entries.length === 0 ? (
        <p className="mt-3 text-sm leading-6 text-fg-muted">
          Research you start in this browser appears here, so you can reopen it later.
        </p>
      ) : (
        <ul className="-mx-2 mt-3 space-y-0.5">
          {entries.map((entry) => (
            <li key={entry.id} className="group flex items-start gap-1">
              <NavLink
                to={`/research/${entry.id}`}
                className={({ isActive }) =>
                  cn(
                    "min-w-0 flex-1 rounded-md px-2 py-2 transition-colors",
                    isActive ? "bg-accent-soft" : "hover:bg-surface-muted",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={cn(
                        "line-clamp-2 text-sm font-medium break-words",
                        isActive ? "text-accent-soft-fg" : "text-fg",
                      )}
                    >
                      {entry.topic}
                    </span>
                    <span className="mt-0.5 block text-xs text-fg-subtle" title={formatDateTime(entry.created_at)}>
                      <time dateTime={entry.created_at}>{formatRelative(entry.created_at, now)}</time>
                    </span>
                  </>
                )}
              </NavLink>
              <button
                type="button"
                onClick={() => historyStore.remove(entry.id)}
                aria-label={`Remove “${entry.topic}” from your history`}
                title="Remove from history"
                className="mt-1 inline-flex size-8 shrink-0 items-center justify-center rounded-md text-fg-subtle transition-colors hover:bg-surface-muted hover:text-danger"
              >
                <Trash aria-hidden="true" className="size-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {!persistent && (
        <p className="mt-3 text-xs leading-5 text-fg-subtle">
          Browser storage is unavailable, so this list only lasts until you close the tab.
        </p>
      )}
    </section>
  );
}
