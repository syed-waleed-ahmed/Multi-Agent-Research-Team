/**
 * Server-clock estimate. Stage timestamps come from the server, so elapsed times
 * are computed against the server's clock (estimated from the HTTP `Date`
 * header) instead of trusting the visitor's possibly-skewed local clock.
 */

let offsetMs = 0;
let calibrated = false;

/** Parse an ISO-8601 timestamp, tolerating microsecond precision ("...11.177208Z"). */
export function parseServerDate(value: string | null | undefined): number | null {
  if (!value) return null;
  const normalized = value.replace(/(\.\d{3})\d+/, "$1");
  const time = Date.parse(normalized);
  return Number.isNaN(time) ? null : time;
}

/**
 * Update the offset from a response `Date` header. The header has one-second
 * resolution, so small differences are ignored to keep timers from jittering.
 */
export function recordServerDate(header: string | null, sentAt: number, receivedAt: number): void {
  if (!header) return;
  const serverTime = Date.parse(header);
  if (Number.isNaN(serverTime)) return;
  // The header is truncated to whole seconds: add half a second as the expected value.
  const raw = serverTime + 500 - (sentAt + receivedAt) / 2;
  // Within the header's precision the clocks agree; don't introduce artificial skew.
  const estimate = Math.abs(raw) < 1500 ? 0 : raw;
  if (!calibrated || Math.abs(estimate - offsetMs) > 2000) {
    offsetMs = estimate;
    calibrated = true;
  }
}

/** Current time on the server's clock (milliseconds since the epoch). */
export function serverNow(localNow: number = Date.now()): number {
  return localNow + offsetMs;
}

/** Test helper: forget the calibration. */
export function resetServerClock(): void {
  offsetMs = 0;
  calibrated = false;
}
