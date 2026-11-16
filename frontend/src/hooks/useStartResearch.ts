import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { api, toApiError, type ApiError } from "../lib/api";
import { historyStore } from "../lib/history";
import { newIdempotencyKey } from "../lib/ids";
import type { ResearchCreate } from "../lib/types";

export interface StartResearch {
  start: (request: ResearchCreate) => Promise<void>;
  submitting: boolean;
  error: ApiError | null;
  clearError: () => void;
}

/**
 * Submit a research job, remember it (with its one-time owner token) and open
 * its live view. Retrying the same request after a failure reuses the same
 * Idempotency-Key, so a request that reached the server is never duplicated.
 */
export function useStartResearch(onStarted?: () => void): StartResearch {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const inFlight = useRef(false);
  const pendingKey = useRef<{ payload: string; key: string } | null>(null);

  const start = useCallback(
    async (request: ResearchCreate) => {
      if (inFlight.current) return;
      inFlight.current = true;
      setSubmitting(true);
      setError(null);
      const payload = JSON.stringify(request);
      if (pendingKey.current?.payload !== payload) {
        pendingKey.current = { payload, key: newIdempotencyKey() };
      }
      try {
        const { job } = await api.createResearch(request, pendingKey.current.key);
        pendingKey.current = null;
        historyStore.upsert({
          id: job.id,
          topic: job.topic,
          created_at: job.created_at,
          owner_token: job.owner_token,
          cached: job.cached,
        });
        onStarted?.();
        void navigate(`/research/${job.id}`);
      } catch (caught) {
        setError(toApiError(caught));
      } finally {
        inFlight.current = false;
        setSubmitting(false);
      }
    },
    [navigate, onStarted],
  );

  const clearError = useCallback(() => setError(null), []);

  return { start, submitting, error, clearError };
}
