import { RefreshCw } from "lucide-react";
import { useMeta } from "../../hooks/metaContext";
import { describeApiError } from "../../lib/labels";
import { Button } from "../ui/Button";
import { Spinner } from "../ui/Spinner";

/**
 * Honest status of the first contact with the server. Free instances sleep
 * when idle, so the first request can take up to a minute.
 */
export function ServerStatusBanner() {
  const { meta, error, wakingUp, retry } = useMeta();

  if (meta) return null;

  if (error) {
    const { title, message } = describeApiError(error);
    return (
      <div role="alert" className="border-b border-danger-line bg-danger-soft print:hidden">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 text-sm sm:px-6 lg:px-8">
          <p className="min-w-0 flex-1 text-fg">
            <span className="font-semibold">{title}.</span> {message}
          </p>
          <Button variant="secondary" size="sm" onClick={retry}>
            <RefreshCw aria-hidden="true" className="size-4" />
            Try again
          </Button>
        </div>
      </div>
    );
  }

  if (!wakingUp) return null;

  return (
    <div role="status" className="border-b border-warning-line bg-warning-soft print:hidden">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3 text-sm text-fg sm:px-6 lg:px-8">
        <Spinner className="text-warning" />
        <p>
          <span className="font-semibold">Waking up the server</span> — free instances sleep when idle; this can
          take up to a minute.
        </p>
      </div>
    </div>
  );
}
