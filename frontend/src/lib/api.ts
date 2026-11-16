/**
 * Typed client for the backend HTTP API.
 *
 * Calls are same-origin by default (the FastAPI app serves this build). For
 * split hosting set `VITE_API_BASE_URL` (e.g. `https://api.example.com`) at
 * build time; the backend must then list this site in `CORS_ORIGINS`.
 */
import { recordServerDate } from "./clock";
import type {
  ErrorBody,
  HealthOut,
  JobCreated,
  JobDetail,
  JobOut,
  MetaOut,
  ResearchCreate,
  UsageOut,
} from "./types";

function normalizeBase(value: string | undefined): string {
  const base = (value ?? "").trim();
  return base.endsWith("/") ? base.slice(0, -1) : base;
}

export const API_BASE = normalizeBase(import.meta.env.VITE_API_BASE_URL);

/** Absolute or same-origin URL for an API path such as `/api/v1/meta`. */
export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

/** An error from the API (or the network), always carrying a user-safe message. */
export class ApiError extends Error {
  /** HTTP status; 0 when the server could not be reached. */
  readonly status: number;
  /** Stable machine-readable code, e.g. `daily_limit` or `network_error`. */
  readonly code: string;
  readonly requestId: string | null;
  readonly retryAfterSeconds: number | null;

  constructor(
    status: number,
    code: string,
    message: string,
    options: { requestId?: string | null; retryAfterSeconds?: number | null } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = options.requestId ?? null;
    this.retryAfterSeconds = options.retryAfterSeconds ?? null;
  }

  /** True for failures where retrying later may succeed (network, 5xx, rate limits). */
  get isTransient(): boolean {
    return this.status === 0 || this.status === 429 || this.status >= 500;
  }
}

const FALLBACK_MESSAGES: Record<number, string> = {
  400: "The request was not accepted by the server.",
  403: "You are not allowed to do that.",
  404: "The requested resource was not found.",
  409: "That action is not possible right now.",
  413: "The request is too large.",
  422: "Some of the information you entered is not valid.",
  429: "Too many requests. Please wait a moment and try again.",
  500: "The server ran into an unexpected problem.",
  502: "The server is starting or temporarily unreachable. Please try again shortly.",
  503: "The service is temporarily unavailable. Please try again shortly.",
  504: "The server took too long to respond. Please try again.",
};

export const NETWORK_ERROR_MESSAGE =
  "Could not reach the server. Check your connection and try again.";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseRetryAfterHeader(value: string | null): number | null {
  if (!value) return null;
  const seconds = Number(value);
  if (Number.isFinite(seconds) && seconds >= 0) return Math.round(seconds);
  const date = Date.parse(value);
  if (Number.isNaN(date)) return null;
  return Math.max(0, Math.round((date - Date.now()) / 1000));
}

/**
 * Extract the `{"error": {...}}` envelope from a JSON body, if present.
 * Returns null for anything that does not match the contract.
 */
export function parseErrorBody(body: unknown): ErrorBody | null {
  if (!isRecord(body) || !isRecord(body.error)) return null;
  const { code, message, request_id: requestId, retry_after_seconds: retry } = body.error;
  if (typeof code !== "string" || typeof message !== "string" || !code || !message) return null;
  return {
    code,
    message,
    request_id: typeof requestId === "string" ? requestId : null,
    retry_after_seconds: typeof retry === "number" && Number.isFinite(retry) ? retry : null,
  };
}

/** Convert a non-OK response into an {@link ApiError}; never throws. */
export async function errorFromResponse(response: Response): Promise<ApiError> {
  let body: unknown;
  try {
    const text = await response.text();
    body = text ? (JSON.parse(text) as unknown) : null;
  } catch {
    body = null; // HTML error pages from proxies, empty bodies, ...
  }
  const envelope = parseErrorBody(body);
  const headerRetry = parseRetryAfterHeader(response.headers.get("Retry-After"));
  const requestId = response.headers.get("X-Request-ID");
  if (envelope) {
    return new ApiError(response.status, envelope.code, envelope.message, {
      requestId: envelope.request_id ?? requestId,
      retryAfterSeconds: envelope.retry_after_seconds ?? headerRetry,
    });
  }
  const message =
    FALLBACK_MESSAGES[response.status] ??
    (response.status >= 500
      ? "The server ran into an unexpected problem."
      : "The request could not be completed.");
  return new ApiError(response.status, `http_${response.status}`, message, {
    requestId,
    retryAfterSeconds: headerRetry,
  });
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

interface RequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

interface ApiResponse<T> {
  data: T;
  status: number;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
  const headers: Record<string, string> = { Accept: "application/json", ...options.headers };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const sentAt = Date.now();
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
      credentials: "same-origin",
    });
  } catch (error) {
    if (isAbortError(error)) throw error;
    throw new ApiError(0, "network_error", NETWORK_ERROR_MESSAGE);
  }
  recordServerDate(response.headers.get("Date"), sentAt, Date.now());
  if (!response.ok) throw await errorFromResponse(response);
  try {
    return { data: (await response.json()) as T, status: response.status };
  } catch (error) {
    if (isAbortError(error)) throw error;
    throw new ApiError(response.status, "invalid_response", "The server sent an unexpected response.");
  }
}

export interface CreateResearchResult {
  job: JobCreated;
  /** True for a newly accepted job (202); false when an existing or cached job was returned (200). */
  created: boolean;
}

const jobPath = (id: string) => `/api/v1/research/${encodeURIComponent(id)}`;

export const api = {
  health: (signal?: AbortSignal) => request<HealthOut>("/api/health", { signal }).then((r) => r.data),

  meta: (signal?: AbortSignal) => request<MetaOut>("/api/v1/meta", { signal }).then((r) => r.data),

  usage: (signal?: AbortSignal) => request<UsageOut>("/api/v1/usage", { signal }).then((r) => r.data),

  async createResearch(
    body: ResearchCreate,
    idempotencyKey: string,
    signal?: AbortSignal,
  ): Promise<CreateResearchResult> {
    const { data, status } = await request<JobCreated>("/api/v1/research", {
      method: "POST",
      body,
      headers: { "Idempotency-Key": idempotencyKey },
      signal,
    });
    return { job: data, created: status === 202 };
  },

  getJob: (id: string, signal?: AbortSignal) =>
    request<JobDetail>(jobPath(id), { signal }).then((r) => r.data),

  getStatus: (id: string, signal?: AbortSignal) =>
    request<JobOut>(`${jobPath(id)}/status`, { signal }).then((r) => r.data),

  cancel: (id: string, ownerToken: string, signal?: AbortSignal) =>
    request<JobOut>(`${jobPath(id)}/cancel`, {
      method: "POST",
      headers: { "X-Owner-Token": ownerToken },
      signal,
    }).then((r) => r.data),

  downloadUrl: (id: string, format: "md" | "json") =>
    apiUrl(`${jobPath(id)}/download?format=${format}`),

  eventsUrl: (id: string, after: number) =>
    apiUrl(`${jobPath(id)}/events${after > 0 ? `?after=${after}` : ""}`),
};

/** Normalize anything thrown by the client into an {@link ApiError}. */
export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  return new ApiError(0, "unknown_error", "Something went wrong. Please try again.");
}
