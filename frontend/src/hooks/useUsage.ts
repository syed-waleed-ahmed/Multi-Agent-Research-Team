import { useCallback, useEffect, useState } from "react";
import { api, isAbortError, toApiError, type ApiError } from "../lib/api";
import type { UsageOut } from "../lib/types";

export interface UsageState {
  usage: UsageOut | null;
  error: ApiError | null;
  refresh: () => void;
}

/** The visitor's remaining quota (`GET /api/v1/usage`). */
export function useUsage(): UsageState {
  const [usage, setUsage] = useState<UsageOut | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    api
      .usage(controller.signal)
      .then((value) => {
        setUsage(value);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (!isAbortError(caught)) setError(toApiError(caught));
      });
    return () => controller.abort();
  }, [version]);

  const refresh = useCallback(() => setVersion((value) => value + 1), []);

  return { usage, error, refresh };
}
