import { RotateCcw } from "lucide-react";
import type { ApiError } from "../../lib/api";
import { describeJobError } from "../../lib/labels";
import type { JobOut } from "../../lib/types";
import { Alert } from "../ui/Alert";
import { Button } from "../ui/Button";
import { Spinner } from "../ui/Spinner";
import { ErrorNotice } from "./ErrorNotice";

interface JobOutcomeProps {
  job: JobOut;
  onRetry: () => void;
  retrying: boolean;
  retryError: ApiError | null;
}

/** Explains a failed or cancelled run and offers to run it again with the same settings. */
export function JobOutcome({ job, onRetry, retrying, retryError }: JobOutcomeProps) {
  if (job.status !== "failed" && job.status !== "cancelled") return null;

  const cancelled = job.status === "cancelled";
  const { title, message, hint } = cancelled
    ? { title: "This run was cancelled", message: job.error?.message || "The research run was cancelled.", hint: null }
    : describeJobError(job.error?.code ?? "", job.error?.message ?? "");

  return (
    <div className="space-y-3">
      <Alert
        role="alert"
        tone={cancelled ? "info" : job.error?.code === "rate_limited" ? "warning" : "danger"}
        title={title}
        actions={
          <Button variant="secondary" onClick={onRetry} disabled={retrying}>
            {retrying ? <Spinner /> : <RotateCcw aria-hidden="true" className="size-4" />}
            {cancelled ? "Start again" : "Try again with the same settings"}
          </Button>
        }
      >
        <p data-testid="job-error-message">{message}</p>
        {hint && <p className="mt-1">{hint}</p>}
      </Alert>
      {retryError && <ErrorNotice error={retryError} />}
    </div>
  );
}
