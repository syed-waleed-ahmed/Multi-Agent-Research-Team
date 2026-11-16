/**
 * TypeScript mirror of the backend API contract
 * (`src/research_team/web/schemas.py`). Datetimes are ISO-8601 strings in UTC.
 */

export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export type StageStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export type Depth = "quick" | "standard" | "deep";

export type ReportStyle = "technical_report" | "executive_brief" | "tutorial";

/** Pipeline stages in execution order (`progress.STAGES`). */
export type StageName = "research" | "coding" | "synthesis";

export const STAGE_ORDER: readonly StageName[] = ["research", "coding", "synthesis"];

// --------------------------------------------------------------------------
// Requests
// --------------------------------------------------------------------------
export interface ResearchCreate {
  topic: string;
  instructions?: string | null;
  depth: Depth;
  report_style: ReportStyle;
  model?: string | null;
}

// --------------------------------------------------------------------------
// Responses
// --------------------------------------------------------------------------
export interface ErrorBody {
  code: string;
  message: string;
  request_id: string | null;
  retry_after_seconds: number | null;
}

export interface ErrorResponse {
  error: ErrorBody;
}

export interface StageOut {
  /** research | coding | synthesis */
  stage: string;
  /** Display name of the agent running this stage. */
  agent: string;
  status: StageStatus;
  started_at: string | null;
  finished_at: string | null;
  attempts: number;
  searches: number;
  llm_calls: number;
}

export interface JobOptions {
  depth: Depth;
  report_style: ReportStyle;
  model: string;
  instructions: string | null;
}

export interface JobError {
  code: string;
  message: string;
}

export interface JobOut {
  id: string;
  status: JobStatus;
  topic: string;
  options: JobOptions;
  stages: StageOut[];
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  /** 1-based position while queued; null otherwise. */
  queue_position: number | null;
  error: JobError | null;
  /** True when served from a recent identical run (only on creation responses). */
  cached: boolean;
  result_available: boolean;
}

export interface JobCreated extends JobOut {
  /** Secret required to cancel the job. Returned once; null for existing jobs. */
  owner_token: string | null;
}

export interface SourceOut {
  title: string;
  url: string;
  snippet: string;
  published: string | null;
  provider: string;
  query: string;
}

export interface CitationCheckOut {
  /** Report links found in retrieved search results. */
  matched: string[];
  /** Report links NOT found in search results; treat as unverified. */
  unmatched: string[];
}

export interface ResultOut {
  job_id: string;
  topic: string;
  report_markdown: string;
  document_markdown: string;
  research_notes: string;
  code_examples: string;
  methodology_markdown: string;
  sources: SourceOut[];
  citation_check: CitationCheckOut;
  search_queries: string[];
  model: string;
  provider: string;
  duration_seconds: number;
  token_usage: Record<string, unknown>;
  truncated: boolean;
  created_at: string;
}

export interface JobDetail extends JobOut {
  result: ResultOut | null;
}

/** Event types emitted by the engine (`progress.EventType`) plus job-runner events. */
export type KnownEventType =
  | "queued"
  | "run_started"
  | "stage_started"
  | "stage_completed"
  | "stage_failed"
  | "llm_call"
  | "search"
  | "retry"
  | "provider_fallback"
  | "run_completed"
  | "run_failed"
  | "run_cancelled";

export interface EventOut {
  id: number;
  /** One of {@link KnownEventType}; unknown future types are displayed generically. */
  type: string;
  stage: string | null;
  message: string;
  data: Record<string, unknown>;
  timestamp: string;
}

/** Payload of the final named SSE event `end`. */
export interface StreamEnd {
  status: JobStatus;
}

export interface HealthOut {
  status: string;
  version: string;
}

export interface LimitsOut {
  max_topic_chars: number;
  max_instructions_chars: number;
  jobs_per_ip_per_hour: number;
  jobs_per_ip_per_day: number;
  global_jobs_per_day: number;
  job_timeout_seconds: number;
  max_concurrent_jobs: number;
}

export interface ModelOut {
  id: string;
  provider: string;
  default: boolean;
}

export interface MetaOut {
  version: string;
  repository_url: string;
  models: ModelOut[];
  search_providers: string[];
  depths: Depth[];
  report_styles: ReportStyle[];
  limits: LimitsOut;
  /** "persistent" or "ephemeral" storage. */
  persistence: string;
  /** Whether interactive docs are served at /api/docs. */
  api_docs: boolean;
}

export interface UsageOut {
  jobs_today: number;
  jobs_per_ip_per_day: number;
  global_jobs_today: number;
  global_jobs_per_day: number;
  active_jobs: number;
  max_concurrent_jobs: number;
  queued_jobs: number;
  max_queued_jobs: number;
}

export const TERMINAL_STATUSES: ReadonlySet<JobStatus> = new Set([
  "succeeded",
  "failed",
  "cancelled",
]);

export function isTerminal(status: JobStatus): boolean {
  return TERMINAL_STATUSES.has(status);
}

export function isActive(status: JobStatus): boolean {
  return status === "queued" || status === "running";
}
