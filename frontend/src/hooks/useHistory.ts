import { useSyncExternalStore } from "react";
import { historyStore, type HistoryEntry } from "../lib/history";

/** Research started in this browser, newest first. */
export function useHistory(): readonly HistoryEntry[] {
  return useSyncExternalStore(historyStore.subscribe, historyStore.getSnapshot, historyStore.getSnapshot);
}
