import { parseServerDate } from "./clock";

/** "1.2s", "42s", "3m 05s", "1h 02m". */
export function formatDuration(totalSeconds: number): string {
  if (!Number.isFinite(totalSeconds) || totalSeconds < 0) return "0s";
  if (totalSeconds < 10) return `${(Math.floor(totalSeconds * 10) / 10).toFixed(1)}s`;
  const seconds = Math.floor(totalSeconds);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${String(seconds % 60).padStart(2, "0")}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${String(minutes % 60).padStart(2, "0")}m`;
}

/** Whole-second elapsed timer for live displays: "0:07", "2:15", "1:02:03". */
export function formatClock(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = String(seconds % 60).padStart(2, "0");
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${s}` : `${m}:${s}`;
}

/** Human retry hint for a `retry_after_seconds` value: "about 2 minutes". */
export function formatRetryAfter(seconds: number): string {
  if (seconds < 60) return seconds <= 1 ? "a moment" : `${seconds} seconds`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return minutes === 1 ? "about a minute" : `about ${minutes} minutes`;
  const hours = Math.round(minutes / 60);
  return hours === 1 ? "about an hour" : `about ${hours} hours`;
}

const timeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

const dateFormatter = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });

export function formatTime(iso: string | null): string {
  const time = parseServerDate(iso);
  return time === null ? "" : timeFormatter.format(time);
}

export function formatDateTime(iso: string | null): string {
  const time = parseServerDate(iso);
  return time === null ? "" : dateTimeFormatter.format(time);
}

/** Dates from search results come in many shapes ("2026-03-01", "3 days ago"); show them as given when unparseable. */
export function formatPublished(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
    const [y, m, d] = trimmed.split("-").map(Number) as [number, number, number];
    return dateFormatter.format(new Date(y, m - 1, d));
  }
  return trimmed || null;
}

const relativeFormatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

/** "5 minutes ago", "yesterday". `now` is passed in so callers control re-rendering. */
export function formatRelative(iso: string, now: number): string {
  const time = parseServerDate(iso);
  if (time === null) return "";
  const diffSeconds = Math.round((time - now) / 1000);
  const abs = Math.abs(diffSeconds);
  if (abs < 45) return "just now";
  if (abs < 3600) return relativeFormatter.format(Math.round(diffSeconds / 60), "minute");
  if (abs < 86400) return relativeFormatter.format(Math.round(diffSeconds / 3600), "hour");
  if (abs < 86400 * 30) return relativeFormatter.format(Math.round(diffSeconds / 86400), "day");
  return dateFormatter.format(time);
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat().format(value);
}

/** Host name without "www." for display, or null for invalid URLs. */
export function domainOf(url: string): string | null {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

/** Only http(s) URLs may be rendered as links. */
export function safeHttpUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

/**
 * Canonical URL form used by the backend's citation check
 * (`search.normalize_url`): lower-case host without "www.", no trailing slash,
 * no fragment, query kept.
 */
export function normalizeUrl(value: string): string {
  try {
    const url = new URL(value.trim());
    const host = url.hostname.toLowerCase().replace(/^www\./, "");
    const path = url.pathname.replace(/\/+$/, "") || "/";
    return `${host}${path}${url.search}`;
  } catch {
    return value.trim();
  }
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${formatNumber(count)} ${count === 1 ? singular : plural}`;
}
