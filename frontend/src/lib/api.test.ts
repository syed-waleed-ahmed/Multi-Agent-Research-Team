import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, errorFromResponse, parseErrorBody } from "./api";
import { describeApiError } from "./labels";

function jsonResponse(body: unknown, status: number, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("parseErrorBody", () => {
  it("accepts the documented error envelope", () => {
    expect(
      parseErrorBody({
        error: { code: "daily_limit", message: "Limit reached.", request_id: "abc12345", retry_after_seconds: 60 },
      }),
    ).toEqual({ code: "daily_limit", message: "Limit reached.", request_id: "abc12345", retry_after_seconds: 60 });
  });

  it("rejects bodies that do not match the contract", () => {
    expect(parseErrorBody(null)).toBeNull();
    expect(parseErrorBody({ detail: "Not Found" })).toBeNull();
    expect(parseErrorBody({ error: { code: 42, message: "x" } })).toBeNull();
    expect(parseErrorBody({ error: { code: "x", message: "" } })).toBeNull();
  });
});

describe("errorFromResponse", () => {
  it("keeps the server's code, message, request id and retry timing", async () => {
    const error = await errorFromResponse(
      jsonResponse(
        {
          error: {
            code: "hourly_limit",
            message: "You can start 5 research runs per hour. Please try again later.",
            request_id: "req-1234567",
            retry_after_seconds: 3600,
          },
        },
        429,
      ),
    );
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(429);
    expect(error.code).toBe("hourly_limit");
    expect(error.message).toBe("You can start 5 research runs per hour. Please try again later.");
    expect(error.requestId).toBe("req-1234567");
    expect(error.retryAfterSeconds).toBe(3600);
    expect(error.isTransient).toBe(true);
  });

  it("falls back to the Retry-After header when the body has no retry value", async () => {
    const error = await errorFromResponse(
      jsonResponse(
        { error: { code: "too_many_requests", message: "Too many requests.", request_id: null, retry_after_seconds: null } },
        429,
        { "Retry-After": "30" },
      ),
    );
    expect(error.retryAfterSeconds).toBe(30);
  });

  it("produces a friendly error for non-JSON gateway pages", async () => {
    const error = await errorFromResponse(
      new Response("<html><body>Bad Gateway</body></html>", { status: 502, headers: { "Content-Type": "text/html" } }),
    );
    expect(error.status).toBe(502);
    expect(error.code).toBe("http_502");
    expect(error.message).toMatch(/starting or temporarily unreachable/);
    expect(error.message).not.toContain("<html>");
  });

  it("handles empty bodies", async () => {
    const error = await errorFromResponse(new Response(null, { status: 404 }));
    expect(error.code).toBe("http_404");
    expect(error.message).toBe("The requested resource was not found.");
  });
});

describe("api client", () => {
  it("maps network failures to a network_error ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(api.meta()).rejects.toMatchObject({ status: 0, code: "network_error" });
  });

  it("sends the Idempotency-Key and reports whether a new job was created", async () => {
    const job = { id: "a".repeat(32), owner_token: "secret" };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(job, 202));
    vi.stubGlobal("fetch", fetchMock);

    const result = await api.createResearch(
      { topic: "Vector databases", depth: "quick", report_style: "tutorial" },
      "key-12345678",
    );

    expect(result.created).toBe(true);
    expect(result.job.owner_token).toBe("secret");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/research");
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>)["Idempotency-Key"]).toBe("key-12345678");
    expect(JSON.parse(init.body as string)).toEqual({ topic: "Vector databases", depth: "quick", report_style: "tutorial" });
  });

  it("treats a 200 response as an existing or cached job", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ id: "b".repeat(32), cached: true, owner_token: null }, 200)));
    const result = await api.createResearch({ topic: "abc", depth: "standard", report_style: "technical_report" }, "key-87654321");
    expect(result.created).toBe(false);
    expect(result.job.cached).toBe(true);
  });

  it("throws the parsed envelope for quota errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            error: {
              code: "daily_limit",
              message: "You have reached the daily limit of 10 research runs.",
              request_id: "r-12345678",
              retry_after_seconds: 86400,
            },
          },
          429,
        ),
      ),
    );
    const error = await api
      .createResearch({ topic: "abc", depth: "standard", report_style: "technical_report" }, "key-11112222")
      .catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    const presentation = describeApiError(error as ApiError);
    expect(presentation.title).toBe("Daily limit reached");
    expect(presentation.message).toContain("daily limit of 10");
    expect(presentation.hint).toBe("Try again in about 24 hours.");
  });

  it("sends the owner token when cancelling", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: "c".repeat(32), status: "running" }, 202));
    vi.stubGlobal("fetch", fetchMock);
    await api.cancel("c".repeat(32), "owner-secret");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(`/api/v1/research/${"c".repeat(32)}/cancel`);
    expect((init.headers as Record<string, string>)["X-Owner-Token"]).toBe("owner-secret");
  });

  it("builds download and event URLs", () => {
    expect(api.downloadUrl("d".repeat(32), "md")).toBe(`/api/v1/research/${"d".repeat(32)}/download?format=md`);
    expect(api.eventsUrl("d".repeat(32), 0)).toBe(`/api/v1/research/${"d".repeat(32)}/events`);
    expect(api.eventsUrl("d".repeat(32), 12)).toBe(`/api/v1/research/${"d".repeat(32)}/events?after=12`);
  });
});
