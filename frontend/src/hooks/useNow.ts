import { useEffect, useState } from "react";

/**
 * The current time, re-rendering every `intervalMs` while `active`.
 * Inactive callers get a frozen value, so finished timers stop ticking.
 */
export function useNow(intervalMs: number, active = true): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!active) return;
    const tick = () => setNow(Date.now());
    const first = window.setTimeout(tick, 0);
    const timer = window.setInterval(tick, intervalMs);
    return () => {
      window.clearTimeout(first);
      window.clearInterval(timer);
    };
  }, [intervalMs, active]);

  return now;
}
