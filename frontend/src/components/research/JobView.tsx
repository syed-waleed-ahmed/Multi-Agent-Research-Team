import { FileQuestion, Plus, RefreshCw, Trash } from "lucide-react";
import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";
import { useHistory } from "../../hooks/useHistory";
import { useJob } from "../../hooks/useJob";
import { useStartResearch } from "../../hooks/useStartResearch";
import { api, toApiError, type ApiError } from "../../lib/api";
import { historyStore } from "../../lib/history";
import { isActive, isTerminal, type MetaOut } from "../../lib/types";
import { Alert } from "../ui/Alert";
import { Button } from "../ui/Button";
import { Skeleton } from "../ui/Skeleton";
import { buttonClasses } from "../ui/styles";
import { ActivityTimeline } from "./ActivityTimeline";
import { AgentPipeline } from "./AgentPipeline";
import { ErrorNotice } from "./ErrorNotice";
import { JobHeader } from "./JobHeader";
import { JobOutcome } from "./JobOutcome";

const ResultsView = lazy(() => import("../results/ResultsView"));

function JobSkeleton() {
  return (
    <div aria-busy="true" className="space-y-6">
      <span className="sr-only">Loading research…</span>
      <Skeleton className="h-6 w-28" />
      <Skeleton className="h-9 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <div className="grid gap-3 md:grid-cols-3">
        <Skeleton className="h-44" />
        <Skeleton className="h-44" />
        <Skeleton className="h-44" />
      </div>
      <Skeleton className="h-48" />
    </div>
  );
}

function ResultsSkeleton() {
  return (
    <div aria-busy="true" className="space-y-3">
      <span className="sr-only">Loading report…</span>
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

function NotFound({ jobId, error, onRetry }: { jobId: string; error: ApiError; onRetry: () => void }) {
  const navigate = useNavigate();
  const inHistory = useHistory().some((entry) => entry.id === jobId);

  if (error.status !== 404) {
    return (
      <ErrorNotice
        error={error}
        actions={
          <Button variant="secondary" onClick={onRetry}>
            <RefreshCw aria-hidden="true" className="size-4" />
            Try again
          </Button>
        }
      />
    );
  }

  return (
    <div className="rounded-xl border border-line bg-surface px-6 py-12 text-center shadow-xs">
      <FileQuestion aria-hidden="true" className="mx-auto size-10 text-fg-subtle" />
      <h1 className="mt-4 text-xl font-semibold">This research is no longer available</h1>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-fg-muted">
        Finished research is kept for a limited time, and instances without persistent storage clear it when they
        restart. Download reports you want to keep.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {inHistory && (
          <Button
            variant="secondary"
            onClick={() => {
              historyStore.remove(jobId);
              void navigate("/research");
            }}
          >
            <Trash aria-hidden="true" className="size-4" />
            Remove from history
          </Button>
        )}
        <Link to="/research" className={buttonClasses("primary")}>
          <Plus aria-hidden="true" className="size-4" />
          Start new research
        </Link>
      </div>
    </div>
  );
}

interface JobViewProps {
  jobId: string;
  meta: MetaOut | null;
  /** Called once when the job reaches a final state (e.g. to refresh the quota). */
  onFinished?: () => void;
}

/** Live monitoring and results for one job. Mount with `key={jobId}`. */
export function JobView({ jobId, meta, onFinished }: JobViewProps) {
  const { state, reload, applySnapshot } = useJob(jobId);
  const { job, result, events, connection, loadError, refreshError } = state;
  const history = useHistory();
  const entry = history.find((item) => item.id === jobId);
  const ownerToken = entry?.owner_token ?? null;
  const retry = useStartResearch(onFinished);
  const [cancelling, setCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<ApiError | null>(null);

  useDocumentTitle(job?.topic ?? (loadError ? "Research not found" : "Research"));

  const terminal = job ? isTerminal(job.status) : false;
  useEffect(() => {
    if (terminal) onFinished?.();
  }, [terminal, onFinished]);

  const cancel = useCallback(async () => {
    if (!ownerToken) return;
    setCancelling(true);
    setCancelError(null);
    try {
      applySnapshot(await api.cancel(jobId, ownerToken));
    } catch (caught) {
      const error = toApiError(caught);
      if (error.code !== "already_finished") setCancelError(error);
      setCancelling(false);
    }
  }, [applySnapshot, jobId, ownerToken]);

  if (loadError && !job) {
    return <NotFound jobId={jobId} error={loadError} onRetry={reload} />;
  }
  if (!job) return <JobSkeleton />;

  const active = isActive(job.status);
  const showCancelling = cancelling && active;

  return (
    <div className="space-y-6">
      <JobHeader
        job={job}
        connection={connection}
        cached={entry?.cached === true}
        onCancel={ownerToken ? () => void cancel() : null}
        cancelling={showCancelling}
      />

      {cancelError && <ErrorNotice error={cancelError} />}
      {loadError && <ErrorNotice error={loadError} />}
      {refreshError && active && (
        <Alert tone="warning" role="status">
          Having trouble reaching the server ({refreshError.message}). Still retrying automatically.
        </Alert>
      )}

      {job.status === "queued" && (
        <Alert tone="info" role="status" title="Waiting in the queue">
          {job.queue_position
            ? `Your research is number ${job.queue_position} in line. This instance runs a limited number of jobs at once to stay within free-tier quotas.`
            : "Your research will start as soon as a worker is free."}
        </Alert>
      )}

      <JobOutcome
        job={job}
        retrying={retry.submitting}
        retryError={retry.error}
        onRetry={() =>
          void retry.start({
            topic: job.topic,
            instructions: job.options.instructions,
            depth: job.options.depth,
            report_style: job.options.report_style,
            model: job.options.model,
          })
        }
      />

      <AgentPipeline job={job} />

      {job.status === "succeeded" &&
        (result ? (
          <Suspense fallback={<ResultsSkeleton />}>
            <ResultsView result={result} jobId={job.id} ephemeral={meta?.persistence === "ephemeral"} />
          </Suspense>
        ) : (
          <ResultsSkeleton />
        ))}

      <ActivityTimeline events={events} connection={connection} active={active} />
    </div>
  );
}
