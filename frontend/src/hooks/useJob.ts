import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { api, isAbortError, toApiError } from "../lib/api";
import {
  SNAPSHOT_EVENTS,
  initialJobState,
  jobReducer,
  parseEvent,
  type ConnectionState,
  type JobState,
} from "../lib/jobState";
import { isTerminal, type EventOut, type JobDetail, type JobOut } from "../lib/types";

/** Reconciliation poll interval (the stream is the fast path). */
const POLL_MS = 3000;
/** Minimum spacing of event-triggered snapshot refreshes (protects the API rate limit). */
const MIN_REFRESH_GAP_MS = 1000;
/** How long to wait before re-opening a stream the server refused while the job is active. */
const REOPEN_STREAM_MS = 10_000;
/** For a finished job the stream only replays its event log, so it is retried a few times at most. */
const MAX_REPLAY_ATTEMPTS = 2;
const REPLAY_RETRY_MS = 3000;
/** Events arriving in a burst are applied together. */
const EVENT_BATCH_MS = 60;

export interface UseJobResult {
  state: JobState;
  /** Try loading again after a load error. */
  reload: () => void;
  /** Apply a snapshot obtained elsewhere (e.g. the cancel response) and reconcile. */
  applySnapshot: (job: JobOut) => void;
}

/**
 * Follow one job live: loads the job, subscribes to its Server-Sent Events,
 * and polls `/status` as a fallback. Mount with `key={jobId}` so state resets
 * per job.
 */
export function useJob(jobId: string): UseJobResult {
  const [state, dispatch] = useReducer(jobReducer, initialJobState);
  const [loadKey, setLoadKey] = useState(0);
  const refreshRef = useRef<((detail?: boolean) => void) | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    let stopped = false;
    let terminal = false;
    let succeeded = false;
    let haveResult = false;
    let source: EventSource | null = null;
    let streamOpen = false;
    let streamEnded = false;
    let replayAttempts = 0;
    let lastEventId = 0;
    let buffer: EventOut[] = [];
    let inFlight = false;
    let pending = false;
    let wantDetail = false;
    let lastRefreshAt = 0;
    let pollTimer: number | undefined;
    let refreshTimer: number | undefined;
    let reopenTimer: number | undefined;
    let retryTimer: number | undefined;
    let flushTimer: number | undefined;

    const setConnection = (connection: ConnectionState) => dispatch({ type: "connection_changed", connection });

    const flushEvents = () => {
      window.clearTimeout(flushTimer);
      flushTimer = undefined;
      if (buffer.length === 0) return;
      dispatch({ type: "events_received", events: buffer });
      buffer = [];
    };

    const stopPolling = () => {
      window.clearInterval(pollTimer);
      window.clearTimeout(refreshTimer);
      pollTimer = refreshTimer = undefined;
    };

    const closeStream = () => {
      source?.close();
      source = null;
      streamOpen = false;
      window.clearTimeout(reopenTimer);
      reopenTimer = undefined;
    };

    // Assigned below; referenced by scheduleReopen before the stream exists.
    let openStream: () => void = () => undefined;

    /** Re-open the stream later: indefinitely while the job is active, a few times to replay a finished job. */
    const scheduleReopen = () => {
      if (stopped || streamEnded) return;
      if (terminal) {
        if (replayAttempts >= MAX_REPLAY_ATTEMPTS) return;
        replayAttempts += 1;
      }
      window.clearTimeout(reopenTimer);
      reopenTimer = window.setTimeout(() => openStream(), terminal ? REPLAY_RETRY_MS : REOPEN_STREAM_MS);
    };

    const onSnapshot = (job: JobOut, detail: JobDetail | null) => {
      if (detail) {
        if (detail.result) haveResult = true;
        dispatch({ type: "detail_loaded", detail });
      } else {
        dispatch({ type: "status_loaded", job });
      }
      if (!isTerminal(job.status)) return;
      terminal = true;
      succeeded = job.status === "succeeded";
      stopPolling();
      if (succeeded && !haveResult) {
        // The result is only included in the full job detail.
        wantDetail = true;
        pending = true;
      }
      if (source && !streamOpen) {
        // The stream is stuck reconnecting while the job is already over: stop it and replay later.
        closeStream();
        scheduleReopen();
      }
      if (!source && streamEnded) setConnection("closed");
    };

    const refresh = async (detail = false): Promise<void> => {
      if (detail) wantDetail = true;
      if (inFlight) {
        pending = true;
        return;
      }
      inFlight = true;
      window.clearTimeout(retryTimer);
      try {
        do {
          pending = false;
          const useDetail = wantDetail;
          wantDetail = false;
          lastRefreshAt = Date.now();
          if (useDetail) {
            const job = await api.getJob(jobId, signal);
            if (stopped) return;
            onSnapshot(job, job);
          } else {
            const job = await api.getStatus(jobId, signal);
            if (stopped) return;
            onSnapshot(job, null);
          }
        } while (pending && !stopped);
      } catch (caught) {
        if (stopped || isAbortError(caught)) return;
        const error = toApiError(caught);
        if (error.status === 404) {
          // Deleted (expired) while being viewed.
          stopPolling();
          streamEnded = true;
          closeStream();
          dispatch({ type: "load_failed", error });
          return;
        }
        dispatch({ type: "refresh_failed", error });
        if (terminal && succeeded && !haveResult) {
          // Polling has stopped, so retry fetching the result explicitly.
          retryTimer = window.setTimeout(() => void refresh(true), POLL_MS);
        }
      } finally {
        inFlight = false;
      }
    };

    const scheduleRefresh = () => {
      if (terminal || refreshTimer !== undefined) return;
      const wait = Math.max(150, MIN_REFRESH_GAP_MS - (Date.now() - lastRefreshAt));
      refreshTimer = window.setTimeout(() => {
        refreshTimer = undefined;
        void refresh();
      }, wait);
    };

    openStream = () => {
      if (stopped || streamEnded) return;
      closeStream();
      const stream = new EventSource(api.eventsUrl(jobId, lastEventId));
      source = stream;

      stream.onopen = () => {
        streamOpen = true;
        setConnection("live");
      };

      stream.onmessage = (message: MessageEvent<string>) => {
        const event = parseEvent(message.data);
        if (!event) return;
        lastEventId = Math.max(lastEventId, event.id);
        buffer.push(event);
        flushTimer ??= window.setTimeout(flushEvents, EVENT_BATCH_MS);
        if (SNAPSHOT_EVENTS.has(event.type)) scheduleRefresh();
      };

      stream.addEventListener("end", () => {
        streamEnded = true;
        closeStream();
        flushEvents();
        setConnection("closed");
        if (!terminal || (succeeded && !haveResult)) void refresh(true);
      });

      stream.onerror = () => {
        if (stopped || streamEnded || source !== stream) return;
        streamOpen = false;
        if (terminal || stream.readyState === EventSource.CLOSED) {
          // Refused by the server (e.g. too many open streams), or only needed for a replay:
          // rely on status polling and try the stream again later.
          closeStream();
          setConnection(terminal ? "closed" : "polling");
          scheduleReopen();
        } else {
          // The browser reconnects by itself, resuming after Last-Event-ID.
          setConnection("reconnecting");
        }
        if (!terminal) void refresh();
      };
    };

    const start = async () => {
      let detail: JobDetail;
      try {
        detail = await api.getJob(jobId, signal);
      } catch (caught) {
        if (stopped || isAbortError(caught)) return;
        dispatch({ type: "load_failed", error: toApiError(caught) });
        return;
      }
      if (stopped) return;
      lastRefreshAt = Date.now();
      onSnapshot(detail, detail);
      // Finished jobs still get one pass over the stream: it replays the full
      // event log (for the activity timeline) and ends immediately.
      openStream();
      if (!terminal) {
        pollTimer = window.setInterval(() => {
          if (!document.hidden) void refresh();
        }, POLL_MS);
      }
    };

    const onVisible = () => {
      if (!document.hidden && !terminal) void refresh();
    };

    refreshRef.current = (detail?: boolean) => void refresh(detail);
    document.addEventListener("visibilitychange", onVisible);
    void start();

    return () => {
      stopped = true;
      controller.abort();
      closeStream();
      stopPolling();
      window.clearTimeout(retryTimer);
      window.clearTimeout(flushTimer);
      document.removeEventListener("visibilitychange", onVisible);
      refreshRef.current = null;
    };
  }, [jobId, loadKey]);

  const reload = useCallback(() => {
    dispatch({ type: "reset" });
    setLoadKey((value) => value + 1);
  }, []);

  const applySnapshot = useCallback((job: JobOut) => {
    dispatch({ type: "status_loaded", job });
    refreshRef.current?.();
  }, []);

  return { state, reload, applySnapshot };
}
