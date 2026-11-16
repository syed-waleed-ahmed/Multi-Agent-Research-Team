import { formatRetryAfter } from "./format";
import type { ApiError } from "./api";
import type { Depth, JobStatus, ReportStyle, StageName, StageStatus } from "./types";

export const DEPTH_INFO: Record<Depth, { label: string; searches: number; description: string }> = {
  quick: {
    label: "Quick",
    searches: 2,
    description: "Up to 2 web searches. Fastest, good for a first overview.",
  },
  standard: {
    label: "Standard",
    searches: 4,
    description: "Up to 4 web searches. A balance of coverage and speed.",
  },
  deep: {
    label: "Deep",
    searches: 6,
    description: "Up to 6 web searches. Broader coverage, takes longer.",
  },
};

export const REPORT_STYLE_INFO: Record<ReportStyle, { label: string; description: string }> = {
  technical_report: {
    label: "Technical report",
    description: "Findings, recommended approach, implementation notes with code, risks and references.",
  },
  executive_brief: {
    label: "Executive brief",
    description: "Around 600 words: summary, key findings, recommendations and risks. Code only if essential.",
  },
  tutorial: {
    label: "Tutorial",
    description: "Prerequisites, a numbered step-by-step guide with code, common pitfalls and next steps.",
  },
};

export const STAGE_INFO: Record<StageName, { agent: string; role: string }> = {
  research: {
    agent: "Research Agent",
    role: "Searches the web and writes sourced notes",
  },
  coding: {
    agent: "Coding Agent",
    role: "Turns the findings into practical code examples",
  },
  synthesis: {
    agent: "Manager Agent",
    role: "Reviews everything and writes the final report",
  },
};

export function stageInfo(stage: string): { agent: string; role: string } {
  return (STAGE_INFO as Record<string, { agent: string; role: string } | undefined>)[stage] ?? {
    agent: stage,
    role: "",
  };
}

export const JOB_STATUS_LABEL: Record<JobStatus, string> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

export const STAGE_STATUS_LABEL: Record<StageStatus, string> = {
  pending: "Waiting",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

export interface ErrorPresentation {
  title: string;
  message: string;
  /** e.g. "Try again in about an hour." */
  hint: string | null;
}

const API_ERROR_TITLES: Record<string, string> = {
  hourly_limit: "Hourly limit reached",
  daily_limit: "Daily limit reached",
  global_daily_limit: "Daily capacity reached",
  server_busy: "The research queue is full",
  too_many_requests: "Too many requests",
  too_many_streams: "Too many open live views",
  not_configured: "Research is not available on this server",
  invalid_request: "Please check your request",
  invalid_topic: "Please check the topic",
  topic_too_long: "The topic is too long",
  instructions_too_long: "The instructions are too long",
  invalid_model: "That model is not available",
  invalid_idempotency_key: "Please try again",
  not_found: "Not found",
  forbidden: "Not allowed",
  already_finished: "This run has already finished",
  not_ready: "The result is not ready yet",
  payload_too_large: "The request is too large",
  network_error: "Can't reach the server",
};

/** User-facing title, message and retry hint for an API error. */
export function describeApiError(error: ApiError): ErrorPresentation {
  const title =
    API_ERROR_TITLES[error.code] ??
    (error.status >= 500 ? "The server ran into a problem" : "Something went wrong");
  const hint =
    error.retryAfterSeconds !== null && error.retryAfterSeconds > 0
      ? `Try again in ${formatRetryAfter(error.retryAfterSeconds)}.`
      : null;
  return { title, message: error.message, hint };
}

const JOB_ERROR_INFO: Record<string, { title: string; hint: string | null }> = {
  rate_limited: {
    title: "AI provider rate limit reached",
    hint: "Free-tier model quotas are shared by everyone using this instance and reset every minute.",
  },
  provider_unavailable: {
    title: "AI provider unavailable",
    hint: "The language-model provider rejected or could not serve the request. This is usually temporary.",
  },
  timeout: {
    title: "Time limit exceeded",
    hint: "Try the Quick depth or a narrower topic so the run finishes within the limit.",
  },
  cancelled: { title: "Run cancelled", hint: null },
  interrupted: {
    title: "Interrupted by a server restart",
    hint: "The server restarted while this run was in progress. Start it again to get a report.",
  },
  configuration: {
    title: "Server configuration problem",
    hint: "The operator of this instance needs to fix its configuration.",
  },
  workflow_error: { title: "The research run failed", hint: "Starting the run again often helps." },
  invalid_request: { title: "The request could not be processed", hint: null },
  internal_error: { title: "Unexpected server error", hint: "Please try again later." },
};

/** Presentation for a job-level `error.code` (see `jobs._error_for`). */
export function describeJobError(code: string, message: string): ErrorPresentation {
  const info = JOB_ERROR_INFO[code] ?? { title: "The research run failed", hint: null };
  return { title: info.title, message: message || "The run did not complete.", hint: info.hint };
}
