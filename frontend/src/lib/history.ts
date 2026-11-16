/**
 * "Your recent research": jobs started in this browser, kept in localStorage.
 *
 * The owner token (needed to cancel a job) is only ever returned once by the
 * API, so it is stored here. When storage is unavailable, entries live in
 * memory for the current tab so the workspace still works.
 */
import { browserStorage, isStorageAvailable, safeGet, safeSet, type StorageProvider } from "./storage";

export interface HistoryEntry {
  id: string;
  topic: string;
  created_at: string;
  /** Secret that allows cancelling the job; null when this browser did not create it. */
  owner_token: string | null;
  /** True when the server answered with a recent identical run instead of starting a new one. */
  cached?: boolean;
}

export const HISTORY_KEY = "mart:research-history:v1";
export const MAX_HISTORY_ENTRIES = 30;

const JOB_ID = /^[0-9a-f]{32}$/;

function sanitizeEntry(value: unknown): HistoryEntry | null {
  if (typeof value !== "object" || value === null) return null;
  const record = value as Record<string, unknown>;
  const { id, topic, created_at: createdAt, owner_token: token, cached } = record;
  if (typeof id !== "string" || !JOB_ID.test(id)) return null;
  if (typeof topic !== "string" || typeof createdAt !== "string") return null;
  return {
    id,
    topic: topic.slice(0, 2000),
    created_at: createdAt,
    owner_token: typeof token === "string" && token ? token : null,
    ...(cached === true ? { cached: true } : {}),
  };
}

/** Parse stored JSON defensively: corrupt or foreign data yields an empty list. */
export function parseHistory(raw: string | null): HistoryEntry[] {
  if (!raw) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return [];
  }
  if (!Array.isArray(parsed)) return [];
  const seen = new Set<string>();
  const entries: HistoryEntry[] = [];
  for (const item of parsed) {
    const entry = sanitizeEntry(item);
    if (entry && !seen.has(entry.id)) {
      seen.add(entry.id);
      entries.push(entry);
    }
  }
  return entries.slice(0, MAX_HISTORY_ENTRIES);
}

export interface HistoryStore {
  getSnapshot: () => readonly HistoryEntry[];
  subscribe: (listener: () => void) => () => void;
  /** Add or update an entry (moved to the top). An existing owner token is never dropped. */
  upsert: (entry: HistoryEntry) => void;
  remove: (id: string) => void;
  get: (id: string) => HistoryEntry | undefined;
  getOwnerToken: (id: string) => string | null;
  /** Whether entries survive a reload (false when localStorage is unavailable). */
  isPersistent: () => boolean;
}

export function createHistoryStore(provider: StorageProvider = browserStorage): HistoryStore {
  let entries: readonly HistoryEntry[] = parseHistory(safeGet(provider, HISTORY_KEY));
  let persistent = isStorageAvailable(provider);
  const listeners = new Set<() => void>();

  const emit = () => {
    for (const listener of listeners) listener();
  };

  const commit = (next: HistoryEntry[]) => {
    entries = next.slice(0, MAX_HISTORY_ENTRIES);
    persistent = safeSet(provider, HISTORY_KEY, JSON.stringify(entries));
    emit();
  };

  const onStorage = (event: StorageEvent) => {
    if (event.key !== HISTORY_KEY && event.key !== null) return;
    entries = parseHistory(safeGet(provider, HISTORY_KEY));
    emit();
  };

  return {
    getSnapshot: () => entries,

    subscribe(listener) {
      listeners.add(listener);
      if (listeners.size === 1 && typeof window !== "undefined") {
        window.addEventListener("storage", onStorage);
      }
      return () => {
        listeners.delete(listener);
        if (listeners.size === 0 && typeof window !== "undefined") {
          window.removeEventListener("storage", onStorage);
        }
      };
    },

    upsert(entry) {
      const existing = entries.find((item) => item.id === entry.id);
      const merged: HistoryEntry = {
        ...existing,
        ...entry,
        owner_token: entry.owner_token ?? existing?.owner_token ?? null,
      };
      if (!merged.cached) delete merged.cached;
      commit([merged, ...entries.filter((item) => item.id !== entry.id)]);
    },

    remove(id) {
      if (!entries.some((item) => item.id === id)) return;
      commit(entries.filter((item) => item.id !== id));
    },

    get: (id) => entries.find((item) => item.id === id),

    getOwnerToken: (id) => entries.find((item) => item.id === id)?.owner_token ?? null,

    isPersistent: () => persistent,
  };
}

export const historyStore = createHistoryStore();
