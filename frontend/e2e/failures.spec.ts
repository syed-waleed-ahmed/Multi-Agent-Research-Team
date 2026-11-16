import { expect, test } from "@playwright/test";
import { agentCard, jobStatus, startFromWorkspace, uniqueTopic } from "./helpers";

test("a provider outage ends the run with a clear error", async ({ page }) => {
  await startFromWorkspace(page, uniqueTopic("Edge caching strategies [provider-down]"));

  await expect(jobStatus(page)).toHaveText("Failed");
  const alert = page.getByRole("alert").filter({ hasText: "AI provider unavailable" });
  await expect(alert).toBeVisible();
  await expect(alert).toContainText("The AI provider is temporarily unavailable");
  await expect(agentCard(page, "Research Agent")).toHaveAttribute("data-status", "failed");
  await expect(agentCard(page, "Coding Agent")).toHaveAttribute("data-status", "pending");
  await expect(page.getByRole("list", { name: "Run events" })).toContainText("Run failed");
  await expect(page.getByRole("button", { name: "Try again with the same settings" })).toBeEnabled();
});

test("a provider rate limit shows the retry and a clear rate-limit message", async ({ page }) => {
  await startFromWorkspace(page, uniqueTopic("Kubernetes autoscaling [rate-limit]"));

  await expect(jobStatus(page)).toHaveText("Failed");
  const alert = page.getByRole("alert").filter({ hasText: "AI provider rate limit reached" });
  await expect(alert).toBeVisible();
  await expect(alert).toContainText("free-tier rate limit was reached");
  await expect(alert).toContainText("reset every minute");

  const timeline = page.getByRole("list", { name: "Run events" });
  await expect(timeline).toContainText("Provider rate limited; retrying in 1s");
  await expect(timeline).toContainText("Rate limited by the provider · waiting 1s · retry 1 of 1");
});

test("cancelling an active run stops it", async ({ page }) => {
  await startFromWorkspace(page, uniqueTopic("Long-running analysis of message queues [slow]"));

  await expect(agentCard(page, "Research Agent")).toHaveAttribute("data-status", "running");
  await expect(page.getByText("Live", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Cancel run" }).click();

  await expect(jobStatus(page)).toHaveText("Cancelled");
  await expect(agentCard(page, "Research Agent")).toHaveAttribute("data-status", "cancelled");
  await expect(agentCard(page, "Manager Agent")).toHaveAttribute("data-status", "pending");
  await expect(page.getByRole("alert").filter({ hasText: "This run was cancelled" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Cancel run|Cancelling/ })).toHaveCount(0);
});

test("the cancel button is only offered to the browser that started the run", async ({ page, browser }) => {
  await startFromWorkspace(page, uniqueTopic("Observability for serverless apps [slow]"));
  await expect(page.getByRole("button", { name: "Cancel run" })).toBeVisible();

  const other = await browser.newContext();
  const visitor = await other.newPage();
  await visitor.goto(page.url());
  await expect(visitor.getByTestId("job-status")).toHaveText(/Queued|Running/);
  await expect(visitor.getByRole("button", { name: "Cancel run" })).toHaveCount(0);
  await other.close();

  await page.getByRole("button", { name: "Cancel run" }).click();
  await expect(jobStatus(page)).toHaveText("Cancelled");
});

test("an exhausted daily quota shows the friendly limit message", async ({ page }) => {
  await page.route("**/api/v1/research", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await route.fulfill({
      status: 429,
      contentType: "application/json",
      headers: { "Retry-After": "86400" },
      body: JSON.stringify({
        error: {
          code: "daily_limit",
          message:
            "You have reached the daily limit of 10 research runs. This keeps the free service available for everyone.",
          request_id: "e2e-request-0001",
          retry_after_seconds: 86400,
        },
      }),
    });
  });

  await page.goto("/research");
  await page.getByLabel("Research topic").fill("Quota check topic");
  await page.getByRole("button", { name: "Start research" }).click();

  const alert = page.getByRole("alert").filter({ hasText: "Daily limit reached" });
  await expect(alert).toBeVisible();
  await expect(alert).toContainText("You have reached the daily limit of 10 research runs.");
  await expect(alert).toContainText("Try again in about 24 hours.");
  await expect(page).toHaveURL(/\/research$/);
  await expect(page.getByRole("button", { name: "Start research" })).toBeEnabled();
});

test("form validation explains a too-short topic without calling the API", async ({ page }) => {
  let posted = false;
  await page.route("**/api/v1/research", async (route) => {
    if (route.request().method() === "POST") posted = true;
    await route.fallback();
  });
  await page.goto("/research");
  await page.getByLabel("Research topic").fill("ab");
  await page.getByRole("button", { name: "Start research" }).click();
  await expect(page.getByText("Enter at least 3 characters.")).toBeVisible();
  await expect(page.getByLabel("Research topic")).toHaveAttribute("aria-invalid", "true");
  expect(posted).toBe(false);
});

test("an expired research link is handled gracefully and can be removed from history", async ({ page }) => {
  const missingId = "0123456789abcdef0123456789abcdef";
  await page.addInitScript((id) => {
    window.localStorage.setItem(
      "mart:research-history:v1",
      JSON.stringify([{ id, topic: "An old expired run", created_at: "2026-01-01T00:00:00Z", owner_token: null }]),
    );
  }, missingId);

  await page.goto(`/research/${missingId}`);
  await expect(page.getByRole("heading", { name: "This research is no longer available" })).toBeVisible();
  await page.getByRole("button", { name: "Remove from history" }).click();
  await expect(page).toHaveURL(/\/research$/);
  await expect(page.getByRole("region", { name: /Your recent research/ })).not.toContainText("An old expired run");
});

test("the app keeps working when localStorage is blocked", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      get() {
        throw new DOMException("The operation is insecure.", "SecurityError");
      },
    });
  });
  await startFromWorkspace(page, uniqueTopic("Blocked storage check"));
  await expect(jobStatus(page)).toHaveText("Completed");
  await expect(page.getByText("Browser storage is unavailable")).toBeVisible();
  await expect(page.getByRole("region", { name: /Your recent research/ })).toContainText("Blocked storage check");
});

test("unknown pages show a helpful 404", async ({ page }) => {
  await page.goto("/this-page-does-not-exist");
  await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();
  await page.getByRole("link", { name: "Start research" }).click();
  await expect(page).toHaveURL(/\/research$/);
});
