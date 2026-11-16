import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, isAbortError, toApiError, type ApiError } from "../lib/api";
import type { MetaOut } from "../lib/types";
import { MetaContext, type MetaState } from "./metaContext";

/** After this long without an answer we tell the visitor the server is waking up. */
const SLOW_AFTER_MS = 3000;
/** Keep retrying a sleeping/booting instance for this long before giving up. */
const WAKE_BUDGET_MS = 90_000;

function waitFor(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const timer = window.setTimeout(resolve, ms);
    signal.addEventListener("abort", () => {
      window.clearTimeout(timer);
      resolve();
    });
  });
}

/** Gateways answer 502/503/504 (or nothing at all) while a free instance boots. */
function isWakingError(error: ApiError): boolean {
  return error.status === 0 || error.status === 502 || error.status === 503 || error.status === 504;
}

interface LoadState {
  meta: MetaOut | null;
  error: ApiError | null;
  wakingUp: boolean;
}

export function MetaProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<LoadState>({ meta: null, error: null, wakingUp: false });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const slowTimer = window.setTimeout(() => {
      setState((current) => (current.meta ? current : { ...current, wakingUp: true }));
    }, SLOW_AFTER_MS);
    const deadline = Date.now() + WAKE_BUDGET_MS;

    const load = async () => {
      let delay = 2000;
      for (;;) {
        try {
          const meta = await api.meta(controller.signal);
          setState({ meta, error: null, wakingUp: false });
          return;
        } catch (caught) {
          if (controller.signal.aborted || isAbortError(caught)) return;
          const error = toApiError(caught);
          if (!isWakingError(error) || Date.now() + delay > deadline) {
            setState({ meta: null, error, wakingUp: false });
            return;
          }
          setState((current) => ({ ...current, wakingUp: true }));
          await waitFor(delay, controller.signal);
          if (controller.signal.aborted) return;
          delay = Math.min(Math.round(delay * 1.5), 10_000);
        }
      }
    };
    void load().finally(() => window.clearTimeout(slowTimer));

    return () => {
      controller.abort();
      window.clearTimeout(slowTimer);
    };
  }, [attempt]);

  const retry = useCallback(() => {
    setState({ meta: null, error: null, wakingUp: false });
    setAttempt((value) => value + 1);
  }, []);

  const value = useMemo<MetaState>(() => ({ ...state, retry }), [state, retry]);

  return <MetaContext.Provider value={value}>{children}</MetaContext.Provider>;
}
