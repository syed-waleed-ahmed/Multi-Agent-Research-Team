import { expect, test } from "@playwright/test";
import { agentCard, expectAllAgents, jobStatus, startFromWorkspace, uniqueTopic } from "./helpers";

test("a second run waits in the queue with its real position and can be cancelled before it starts", async ({
  page,
  request,
}) => {
  // Occupy the single worker of the test server with a slow run started through the API.
  const response = await request.post("/api/v1/research", {
    data: { topic: uniqueTopic("Queue blocker [slow]"), depth: "quick", report_style: "tutorial" },
  });
  expect(response.status()).toBe(202);
  const blocker = (await response.json()) as { id: string; owner_token: string };

  try {
    await startFromWorkspace(page, uniqueTopic("Queued research on CRDTs"));
    await expect(jobStatus(page)).toHaveText("Queued");
    const queued = page.getByRole("status").filter({ hasText: "Waiting in the queue" }).first();
    await expect(queued).toContainText("number 1 in line");

    await page.getByRole("button", { name: "Cancel run" }).click();
    await expect(jobStatus(page)).toHaveText("Cancelled");
    await expect(page.getByRole("list", { name: "Run events" })).toContainText("Cancelled before it started");
    await expect(agentCard(page, "Research Agent")).toContainText("Not run");
  } finally {
    await request.post(`/api/v1/research/${blocker.id}/cancel`, { headers: { "X-Owner-Token": blocker.owner_token } });
  }
});

test("a slow first response shows the honest wake-up notice", async ({ page }) => {
  await page.route("**/api/v1/meta", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 4500));
    await route.continue();
  });
  await page.goto("/");
  const notice = page.getByRole("status").filter({ hasText: "Waking up the server" });
  await expect(notice).toBeVisible({ timeout: 4000 });
  await expect(notice).toContainText("free instances sleep when idle; this can take up to a minute");
  await expect(notice).toBeHidden({ timeout: 15_000 });
  await expect(page.getByRole("link", { name: "View on GitHub" })).toBeVisible();
});

test("progress still arrives by polling when the event stream is refused", async ({ page }) => {
  await page.route(
    (url) => url.pathname.endsWith("/events"),
    (route) =>
      route.fulfill({
        status: 429,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "too_many_streams",
            message: "Too many open progress streams.",
            request_id: null,
            retry_after_seconds: 30,
          },
        }),
      }),
  );
  await startFromWorkspace(page, uniqueTopic("Polling fallback check [slow]"));
  await expect(page.getByText("Live stream unavailable, checking every few seconds")).toBeVisible();
  await expect(agentCard(page, "Research Agent")).toHaveAttribute("data-status", /running|completed/);
  await expectAllAgents(page, "completed");
  await expect(jobStatus(page)).toHaveText("Completed");
  await expect(page.getByRole("article", { name: "Report" })).toBeVisible();
});

test("the print layout contains only the report and its sources", async ({ page }) => {
  await startFromWorkspace(page, uniqueTopic("Print layout check"));
  await expect(page.getByRole("article", { name: "Report" })).toBeVisible();

  await page.emulateMedia({ media: "print" });
  await expect(page.getByRole("banner")).toBeHidden();
  await expect(page.getByRole("contentinfo")).toBeHidden();
  await expect(agentCard(page, "Research Agent")).toBeHidden();
  await expect(page.getByRole("heading", { name: "Activity" })).toBeHidden();
  await expect(page.getByRole("button", { name: "Copy report" })).toBeHidden();
  await expect(page.getByRole("complementary", { name: "Quota and history" })).toBeHidden();

  await expect(page.locator("#result-panel-report")).toBeVisible();
  await expect(page.locator("#result-panel-sources")).toBeVisible();
  await expect(page.locator("#result-panel-sources")).toContainText("Official documentation");
  await expect(page.locator("#result-panel-notes")).toBeHidden();
  await expect(page.locator("#result-panel-methodology")).toBeHidden();
});

test("keyboard users can skip straight to the content", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Skip to content" });
  await expect(skip).toBeFocused();
  await expect(skip).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
});
