import { describe, expect, it } from "vitest";
import { parseServerDate } from "./clock";
import { domainOf, formatClock, formatDuration, formatRetryAfter, normalizeUrl, safeHttpUrl } from "./format";

describe("format helpers", () => {
  it("parses server timestamps with microseconds", () => {
    expect(parseServerDate("2026-11-15T22:41:11.177208Z")).toBe(Date.UTC(2026, 10, 15, 22, 41, 11, 177));
    expect(parseServerDate(null)).toBeNull();
    expect(parseServerDate("garbage")).toBeNull();
  });

  it("formats durations and live clocks", () => {
    expect(formatDuration(1.24)).toBe("1.2s");
    expect(formatDuration(42.5)).toBe("42s");
    expect(formatDuration(185)).toBe("3m 05s");
    expect(formatClock(64.9)).toBe("1:04");
    expect(formatClock(3723)).toBe("1:02:03");
  });

  it("describes retry delays in words", () => {
    expect(formatRetryAfter(30)).toBe("30 seconds");
    expect(formatRetryAfter(120)).toBe("about 2 minutes");
    expect(formatRetryAfter(3600)).toBe("about an hour");
    expect(formatRetryAfter(86400)).toBe("about 24 hours");
  });

  it("accepts only http(s) URLs", () => {
    expect(safeHttpUrl("https://example.com/a")).toBe("https://example.com/a");
    expect(safeHttpUrl("javascript:alert(1)")).toBeNull();
    expect(safeHttpUrl("data:text/html,hi")).toBeNull();
    expect(safeHttpUrl("/relative")).toBeNull();
  });

  it("normalizes URLs like the backend citation check", () => {
    expect(normalizeUrl("https://WWW.Example.com/Path/")).toBe("example.com/Path");
    expect(normalizeUrl("http://example.com")).toBe("example.com/");
    expect(normalizeUrl("https://example.com/a?b=1#frag")).toBe("example.com/a?b=1");
    expect(domainOf("https://www.docs.example.org/x")).toBe("docs.example.org");
  });
});
