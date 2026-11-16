/**
 * localStorage access that never throws. Storage can be unavailable (privacy
 * modes, disabled cookies, sandboxed frames) or full; the app keeps working
 * and simply does not persist.
 */

export type StorageProvider = () => Storage | null | undefined;

export const browserStorage: StorageProvider = () => window.localStorage;

export function safeGet(provider: StorageProvider, key: string): string | null {
  try {
    return provider()?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

/** Returns false when the value could not be stored. */
export function safeSet(provider: StorageProvider, key: string, value: string): boolean {
  try {
    const storage = provider();
    if (!storage) return false;
    storage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

export function safeRemove(provider: StorageProvider, key: string): void {
  try {
    provider()?.removeItem(key);
  } catch {
    // Nothing to do: the value simply stays (or never existed).
  }
}

/** True when values can be written and read back. */
export function isStorageAvailable(provider: StorageProvider): boolean {
  const probe = "mart:probe";
  if (!safeSet(provider, probe, probe)) return false;
  const ok = safeGet(provider, probe) === probe;
  safeRemove(provider, probe);
  return ok;
}
