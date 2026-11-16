import { describe, expect, it } from "vitest";
import { HISTORY_KEY, MAX_HISTORY_ENTRIES, createHistoryStore, parseHistory, type HistoryEntry } from "./history";

const ID_A = "a".repeat(32);
const ID_B = "b".repeat(32);

function entry(id: string, overrides: Partial<HistoryEntry> = {}): HistoryEntry {
  return { id, topic: `Topic ${id.slice(0, 4)}`, created_at: "2026-11-15T10:00:00Z", owner_token: `token-${id.slice(0, 4)}`, ...overrides };
}

/** In-memory Storage implementation for tests. */
class MemoryStorage implements Storage {
  private data = new Map<string, string>();
  get length() {
    return this.data.size;
  }
  clear() {
    this.data.clear();
  }
  getItem(key: string) {
    return this.data.get(key) ?? null;
  }
  key(index: number) {
    return [...this.data.keys()][index] ?? null;
  }
  removeItem(key: string) {
    this.data.delete(key);
  }
  setItem(key: string, value: string) {
    this.data.set(key, value);
  }
}

describe("history store with working storage", () => {
  it("persists entries newest first and reloads them", () => {
    const storage = new MemoryStorage();
    const store = createHistoryStore(() => storage);
    store.upsert(entry(ID_A));
    store.upsert(entry(ID_B));
    expect(store.getSnapshot().map((item) => item.id)).toEqual([ID_B, ID_A]);
    expect(store.isPersistent()).toBe(true);

    const reloaded = createHistoryStore(() => storage);
    expect(reloaded.getSnapshot().map((item) => item.id)).toEqual([ID_B, ID_A]);
    expect(reloaded.getOwnerToken(ID_A)).toBe("token-aaaa");
  });

  it("never drops an owner token when the same job is returned again without one", () => {
    const store = createHistoryStore(() => new MemoryStorage());
    store.upsert(entry(ID_A, { owner_token: "secret" }));
    store.upsert(entry(ID_A, { owner_token: null, cached: true }));
    expect(store.getOwnerToken(ID_A)).toBe("secret");
    expect(store.get(ID_A)?.cached).toBe(true);
    expect(store.getSnapshot()).toHaveLength(1);
  });

  it("removes entries and notifies subscribers", () => {
    const store = createHistoryStore(() => new MemoryStorage());
    let notifications = 0;
    const unsubscribe = store.subscribe(() => {
      notifications += 1;
    });
    store.upsert(entry(ID_A));
    store.remove(ID_A);
    store.remove(ID_A); // no-op
    unsubscribe();
    expect(store.getSnapshot()).toEqual([]);
    expect(notifications).toBe(2);
  });

  it("caps the number of stored entries", () => {
    const store = createHistoryStore(() => new MemoryStorage());
    for (let i = 0; i < MAX_HISTORY_ENTRIES + 5; i += 1) {
      store.upsert(entry(i.toString(16).padStart(32, "0")));
    }
    expect(store.getSnapshot()).toHaveLength(MAX_HISTORY_ENTRIES);
  });
});

describe("history store with failing storage", () => {
  it("works in memory when accessing localStorage throws (e.g. blocked cookies)", () => {
    const store = createHistoryStore(() => {
      throw new DOMException("The operation is insecure.", "SecurityError");
    });
    expect(store.getSnapshot()).toEqual([]);
    store.upsert(entry(ID_A));
    expect(store.getSnapshot().map((item) => item.id)).toEqual([ID_A]);
    expect(store.getOwnerToken(ID_A)).toBe("token-aaaa");
    expect(store.isPersistent()).toBe(false);
  });

  it("keeps working when writes fail (quota exceeded)", () => {
    const storage = new MemoryStorage();
    storage.setItem = () => {
      throw new DOMException("Quota exceeded", "QuotaExceededError");
    };
    const store = createHistoryStore(() => storage);
    store.upsert(entry(ID_A));
    expect(store.getSnapshot()).toHaveLength(1);
    expect(store.isPersistent()).toBe(false);
  });

  it("works when storage is missing entirely", () => {
    const store = createHistoryStore(() => null);
    store.upsert(entry(ID_B));
    expect(store.get(ID_B)?.topic).toBe("Topic bbbb");
  });
});

describe("parseHistory", () => {
  it("ignores corrupt or foreign data", () => {
    expect(parseHistory("{not json")).toEqual([]);
    expect(parseHistory(JSON.stringify({ id: ID_A }))).toEqual([]);
    expect(parseHistory(null)).toEqual([]);
  });

  it("drops invalid entries and duplicates", () => {
    const raw = JSON.stringify([
      entry(ID_A),
      { id: "not-a-job-id", topic: "x", created_at: "2026-01-01" },
      { id: ID_B, topic: 42, created_at: "2026-01-01" },
      entry(ID_A, { topic: "duplicate" }),
      { id: ID_B, topic: "valid", created_at: "2026-01-01", owner_token: "" },
    ]);
    const parsed = parseHistory(raw);
    expect(parsed.map((item) => item.id)).toEqual([ID_A, ID_B]);
    expect(parsed[1]?.owner_token).toBeNull();
  });

  it("reads what a previous version of the store wrote", () => {
    const storage = new MemoryStorage();
    storage.setItem(HISTORY_KEY, JSON.stringify([entry(ID_A)]));
    expect(createHistoryStore(() => storage).get(ID_A)?.owner_token).toBe("token-aaaa");
  });
});
