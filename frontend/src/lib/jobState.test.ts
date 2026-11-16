import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import { buildTimeline, initialJobState, jobReducer, mergeEvents, parseEvent } from "./jobState";
import type { EventOut, JobDetail, JobOut, StageOut } from "./types";

function stage(name: string, status: StageOut["status"] = "pending"): StageOut {
  return {
    stage: name,
    agent: name,
    status,
    started_at: null,
    finished_at: null,
    attempts: 0,
    searches: 0,
    llm_calls: 0,
  };
}

function job(status: JobOut["status"], overrides: Partial<JobOut> = {}): JobOut {
  return {
    id: "f".repeat(32),
    status,
    topic: "Vector databases",
    options: { depth: "standard", report_style: "technical_report", model: "m", instructions: null },
    stages: [stage("research"), stage("coding"), stage("synthesis")],
    created_at: "2026-11-15T10:00:00.000000Z",
    started_at: null,
    finished_at: null,
    queue_position: null,
    error: null,
    cached: false,
    result_available: false,
    ...overrides,
  };
}

function event(id: number, type: string, data: Record<string, unknown> = {}, stageName: string | null = "research"): EventOut {
  return { id, type, stage: stageName, message: `${type} message`, data, timestamp: `2026-11-15T10:00:${String(id).padStart(2, "0")}.000Z` };
}

describe("jobReducer", () => {
  it("stores the job and its result from a detail snapshot", () => {
    const detail: JobDetail = { ...job("succeeded", { result_available: true }), result: null };
    const state = jobReducer(initialJobState, { type: "detail_loaded", detail });
    expect(state.job?.status).toBe("succeeded");
    expect(state.job).not.toHaveProperty("result");
    expect(state.loadError).toBeNull();
  });

  it("applies newer status snapshots", () => {
    let state = jobReducer(initialJobState, { type: "status_loaded", job: job("queued", { queue_position: 2 }) });
    state = jobReducer(state, { type: "status_loaded", job: job("running", { stages: [stage("research", "running"), stage("coding"), stage("synthesis")] }) });
    expect(state.job?.status).toBe("running");
    expect(state.job?.stages[0]?.status).toBe("running");
  });

  it("never moves a finished job back to an unfinished state", () => {
    let state = jobReducer(initialJobState, { type: "status_loaded", job: job("cancelled") });
    state = jobReducer(state, { type: "status_loaded", job: job("running") });
    expect(state.job?.status).toBe("cancelled");
  });

  it("keeps an already-loaded result when a later snapshot has none", () => {
    const result = { report_markdown: "# Report" } as JobDetail["result"];
    let state = jobReducer(initialJobState, { type: "detail_loaded", detail: { ...job("succeeded"), result } });
    state = jobReducer(state, { type: "status_loaded", job: job("succeeded") });
    expect(state.result).toBe(result);
  });

  it("records load and refresh errors separately and clears them on success", () => {
    const error = new ApiError(0, "network_error", "Could not reach the server.");
    let state = jobReducer(initialJobState, { type: "refresh_failed", error });
    expect(state.refreshError).toBe(error);
    state = jobReducer(state, { type: "status_loaded", job: job("running") });
    expect(state.refreshError).toBeNull();
    state = jobReducer(state, { type: "load_failed", error });
    expect(state.loadError).toBe(error);
  });

  it("de-duplicates and orders streamed events", () => {
    let state = jobReducer(initialJobState, { type: "events_received", events: [event(2, "search"), event(1, "queued")] });
    state = jobReducer(state, { type: "events_received", events: [event(2, "search"), event(3, "llm_call")] });
    expect(state.events.map((item) => item.id)).toEqual([1, 2, 3]);
  });

  it("returns the same state object when nothing changes", () => {
    const state = jobReducer(initialJobState, { type: "events_received", events: [event(1, "queued")] });
    expect(jobReducer(state, { type: "events_received", events: [event(1, "queued")] })).toBe(state);
    expect(jobReducer(state, { type: "connection_changed", connection: "connecting" })).toBe(state);
  });
});

describe("mergeEvents", () => {
  it("keeps the existing array when all incoming events are known", () => {
    const existing = [event(1, "queued")];
    expect(mergeEvents(existing, [event(1, "queued")])).toBe(existing);
  });
});

describe("parseEvent", () => {
  it("parses a valid SSE payload", () => {
    const parsed = parseEvent(
      JSON.stringify({ id: 5, type: "search", stage: "research", message: "Searched: overview", data: { query: "overview" }, timestamp: "2026-11-15T22:41:11.183904Z" }),
    );
    expect(parsed).toMatchObject({ id: 5, type: "search", data: { query: "overview" } });
  });

  it("rejects malformed payloads", () => {
    expect(parseEvent("not json")).toBeNull();
    expect(parseEvent(JSON.stringify({ id: "1", type: "search" }))).toBeNull();
    expect(parseEvent(JSON.stringify({ id: 1, type: "search" }))).toBeNull();
  });
});

describe("buildTimeline", () => {
  it("describes searches, retries, fallbacks and failures from real event data", () => {
    const items = buildTimeline([
      event(1, "queued", {}, null),
      event(2, "search", { query: "vector index types", results: 5, ok: true }),
      event(3, "search", { query: "hnsw", results: 0, ok: false }),
      event(4, "retry", { delay_seconds: 1.5, attempt: 1, max_retries: 3, rate_limited: true }),
      event(5, "provider_fallback", { from: "groq", to: "gemini", model: "gemini-2.5-flash" }),
      { ...event(6, "run_failed", { code: "rate_limited" }, null), message: "The AI provider's free-tier rate limit was reached." },
    ]);
    expect(items.map((item) => item.kind)).toEqual(["queued", "search", "search_failed", "retry", "fallback", "failed"]);
    expect(items[1]).toMatchObject({ title: "Searched “vector index types”", detail: "5 results" });
    expect(items[2]).toMatchObject({ tone: "warning", detail: "hnsw" });
    expect(items[3]?.detail).toBe("Rate limited by the provider · waiting 1.5s · retry 1 of 3");
    expect(items[4]?.detail).toBe("Now using gemini-2.5-flash");
    expect(items[5]).toMatchObject({ tone: "danger", detail: "The AI provider's free-tier rate limit was reached." });
  });

  it("folds consecutive model requests of the same stage", () => {
    const items = buildTimeline([
      event(1, "llm_call"),
      event(2, "llm_call"),
      event(3, "llm_call"),
      event(4, "search", { query: "q", results: 1, ok: true }),
      event(5, "llm_call"),
      event(6, "llm_call", {}, "coding"),
    ]);
    expect(items.map((item) => [item.kind, item.count])).toEqual([
      ["llm", 3],
      ["search", 1],
      ["llm", 1],
      ["llm", 1],
    ]);
    expect(items[0]?.title).toBe("3 model requests sent");
  });
});
