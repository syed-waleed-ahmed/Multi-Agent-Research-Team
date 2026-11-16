import type { ReactNode } from "react";
import type { ApiError } from "../../lib/api";
import { describeApiError } from "../../lib/labels";
import { Alert } from "../ui/Alert";

/** A user-safe API error with its retry timing, plus optional actions. */
export function ErrorNotice({ error, actions, className }: { error: ApiError; actions?: ReactNode; className?: string }) {
  const { title, message, hint } = describeApiError(error);
  const quota = error.status === 429 || error.code === "server_busy";
  return (
    <Alert role="alert" tone={quota ? "warning" : "danger"} title={title} actions={actions} className={className}>
      <p>{message}</p>
      {hint && <p className="mt-1 font-medium text-fg">{hint}</p>}
      {error.requestId && error.status >= 500 && (
        <p className="mt-2 text-xs text-fg-subtle">Request ID: {error.requestId}</p>
      )}
    </Alert>
  );
}
