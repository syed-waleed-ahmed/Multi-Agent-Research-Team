/**
 * State of one research job as seen by the browser.
 *
 * Two inputs feed it:
 * - snapshots from `GET /research/{id}` and `/status` — authoritative for job
 *   and stage status, timestamps and counters;
 * - the Server-Sent Events log — the real sequence of engine events, used for
 *   the activity timeline and to trigger an immediate snapshot refresh.
 */
import type { ApiError } from "./api";
import type { EventOut, JobDetail, JobOut, ResultOut } from "./types";
import { isTerminal } from "./types";

/** Live-update channel state, shown honestly in the UI. */
export type ConnectionState =
  /** Opening the event stream for the first time. */
  | "connecting"
  /** Event stream open. */
  | "live"
  /** Stream dropped; the browser is reconnecting (status polling continues). */
  | "reconnecting"
  /** Stream unavailable; relying on periodic status polling only. */
  | "polling"
  /** Nothing left to stream (the job finished). */
  | "closed";

export interface JobState {
  job: JobOut | null;
  result: ResultOut | null;
  events: EventOut[];
  connection: ConnectionState;
  /** Error that prevented loading the job at all (e.g. 404). */
  loadError: ApiError | null;
  /** Most recent failed refresh while a job is displayed (cleared on success). */
  refreshError: ApiError | null;
}

export type JobAction =
  | { type: "reset" }
  | { type: "detail_loaded"; detail: JobDetail }
  | { type: "status_loaded"; job: JobOut }
  | { type: "events_received"; events: EventOut[] }
  | { type: "connection_changed"; connection: ConnectionState }
  | { type: "load_failed"; error: ApiError }
  | { type: "refresh_failed"; error: ApiError };

export const MAX_EVENTS = 1000;

export const initialJobState: JobState = {
  job: null,
  result: null,
  events: [],
  connection: "connecting",
  loadError: null,
  refreshError: null,
};

function withoutResult(detail: JobDetail): JobOut {
  const { result: _result, ...job } = detail;
  return job;
}

/**
 * Accept a new snapshot unless it would move a finished job back to an
 * unfinished state (a late response racing the final one).
 */
function acceptSnapshot(current: JobOut | null, next: JobOut): boolean {
  if (!current || current.id !== next.id) return true;
  return !(isTerminal(current.status) && !isTerminal(next.status));
}

/** Merge new events into a sorted, de-duplicated log. */
export function mergeEvents(existing: EventOut[], incoming: EventOut[]): EventOut[] {
  if (incoming.length === 0) return existing;
  const byId = new Map<number, EventOut>();
  for (const event of existing) byId.set(event.id, event);
  let changed = false;
  for (const event of incoming) {
    if (!byId.has(event.id)) {
      byId.set(event.id, event);
      changed = true;
    }
  }
  if (!changed) return existing;
  const merged = [...byId.values()].sort((a, b) => a.id - b.id);
  return merged.length > MAX_EVENTS ? merged.slice(merged.length - MAX_EVENTS) : merged;
}

export function jobReducer(state: JobState, action: JobAction): JobState {
  switch (action.type) {
    case "reset":
      return initialJobState;
    case "detail_loaded": {
      const job = withoutResult(action.detail);
      if (!acceptSnapshot(state.job, job)) return state;
      return {
        ...state,
        job,
        result: action.detail.result ?? state.result,
        loadError: null,
        refreshError: null,
      };
    }
    case "status_loaded":
      if (!acceptSnapshot(state.job, action.job)) return state;
      return { ...state, job: action.job, loadError: null, refreshError: null };
    case "events_received": {
      const events = mergeEvents(state.events, action.events);
      return events === state.events ? state : { ...state, events };
    }
    case "connection_changed":
      return state.connection === action.connection
        ? state
        : { ...state, connection: action.connection };
    case "load_failed":
      return { ...state, loadError: action.error };
    case "refresh_failed":
      return { ...state, refreshError: action.error };
    default:
      return state;
  }
}

/** Parse one SSE `message` payload; returns null for anything malformed. */
export function parseEvent(raw: string): EventOut | null {
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof value !== "object" || value === null) return null;
  const event = value as Partial<EventOut>;
  if (typeof event.id !== "number" || typeof event.type !== "string") return null;
  if (typeof event.timestamp !== "string") return null;
  return {
    id: event.id,
    type: event.type,
    stage: typeof event.stage === "string" ? event.stage : null,
    message: typeof event.message === "string" ? event.message : "",
    data: typeof event.data === "object" && event.data !== null ? event.data : {},
    timestamp: event.timestamp,
  };
}

/** Events that change stage status or counters: refresh the snapshot promptly. */
export const SNAPSHOT_EVENTS: ReadonlySet<string> = new Set([
  "run_started",
  "stage_started",
  "stage_completed",
  "stage_failed",
  "search",
  "llm_call",
  "provider_fallback",
  "run_completed",
  "run_failed",
  "run_cancelled",
]);

// --------------------------------------------------------------------------
// Activity timeline
// --------------------------------------------------------------------------
export type TimelineTone = "neutral" | "info" | "success" | "warning" | "danger";

export type TimelineKind =
  | "queued"
  | "run"
  | "stage_started"
  | "stage_completed"
  | "stage_failed"
  | "llm"
  | "search"
  | "search_failed"
  | "retry"
  | "fallback"
  | "completed"
  | "failed"
  | "cancelled"
  | "other";

export interface TimelineItem {
  /** Stable key (id of the first underlying event). */
  key: number;
  kind: TimelineKind;
  tone: TimelineTone;
  stage: string | null;
  title: string;
  detail: string | null;
  timestamp: string;
  /** Number of consecutive identical events folded into this item (model requests). */
  count: number;
}

function str(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function num(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function describe(event: EventOut): Omit<TimelineItem, "key" | "count" | "timestamp" | "stage"> {
  const { data } = event;
  switch (event.type) {
    case "queued":
      return { kind: "queued", tone: "neutral", title: "Queued", detail: event.message || null };
    case "run_started": {
      const model = str(data.model);
      const provider = str(data.provider);
      return {
        kind: "run",
        tone: "info",
        title: "Run started",
        detail: model ? `Model ${model}${provider ? ` via ${provider}` : ""}` : null,
      };
    }
    case "stage_started": {
      const attempt = num(data.attempt);
      return {
        kind: "stage_started",
        tone: "info",
        title: event.message || "Stage started",
        detail: attempt && attempt > 1 ? `Attempt ${attempt}` : null,
      };
    }
    case "stage_completed": {
      const duration = num(data.duration_seconds);
      return {
        kind: "stage_completed",
        tone: "success",
        title: event.message || "Stage finished",
        detail: duration !== null && !event.message.includes(" in ") ? `Took ${duration}s` : null,
      };
    }
    case "stage_failed":
      return { kind: "stage_failed", tone: "danger", title: event.message || "Stage stopped", detail: null };
    case "llm_call":
      return { kind: "llm", tone: "neutral", title: "Model request sent", detail: null };
    case "search": {
      const query = str(data.query);
      const results = num(data.results);
      if (data.ok === false) {
        return { kind: "search_failed", tone: "warning", title: "Web search failed", detail: query };
      }
      return {
        kind: "search",
        tone: "neutral",
        title: query ? `Searched “${query}”` : event.message || "Web search",
        detail: results !== null ? `${results} result${results === 1 ? "" : "s"}` : null,
      };
    }
    case "retry": {
      const delay = num(data.delay_seconds);
      const attempt = num(data.attempt);
      const max = num(data.max_retries);
      const parts = [
        data.rate_limited === true ? "Rate limited by the provider" : null,
        delay !== null ? `waiting ${delay}s` : null,
        attempt !== null && max !== null ? `retry ${attempt} of ${max}` : null,
      ].filter(Boolean);
      return {
        kind: "retry",
        tone: "warning",
        title: event.message || "Retrying",
        detail: parts.length ? parts.join(" · ") : null,
      };
    }
    case "provider_fallback":
      return {
        kind: "fallback",
        tone: "warning",
        title: event.message || "Switched to a fallback provider",
        detail: str(data.model) ? `Now using ${String(data.model)}` : null,
      };
    case "run_completed":
      return { kind: "completed", tone: "success", title: event.message || "Report ready", detail: null };
    case "run_failed":
      return { kind: "failed", tone: "danger", title: "Run failed", detail: event.message || null };
    case "run_cancelled":
      return { kind: "cancelled", tone: "neutral", title: "Run cancelled", detail: event.message || null };
    default:
      return { kind: "other", tone: "neutral", title: event.message || event.type, detail: null };
  }
}

/** Turn the raw event log into timeline items, folding consecutive model requests. */
export function buildTimeline(events: readonly EventOut[]): TimelineItem[] {
  const items: TimelineItem[] = [];
  for (const event of events) {
    const last = items.at(-1);
    if (event.type === "llm_call" && last?.kind === "llm" && last.stage === event.stage) {
      last.count += 1;
      last.title = `${last.count} model requests sent`;
      continue;
    }
    items.push({ ...describe(event), key: event.id, count: 1, stage: event.stage, timestamp: event.timestamp });
  }
  return items;
}
