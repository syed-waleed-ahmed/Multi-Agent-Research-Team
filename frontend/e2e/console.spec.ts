import { expect, test } from "@playwright/test";
import { expectAllAgents, trackConsoleErrors } from "./helpers";

test("main pages load without console errors (light and dark)", async ({ page, request }) => {
  // A finished job to visit, created through the public API.
  const response = await request.post("/api/v1/research", {
    data: { topic: `Console check ${Date.now().toString(36)}`, depth: "quick", report_style: "executive_brief" },
  });
  expect(response.status()).toBe(202);
  const job = (await response.json()) as { id: string };

  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    const errors = trackConsoleErrors(page);

    await page.goto("/");
    await expect(page.getByRole("link", { name: "View on GitHub" })).toBeVisible();

    await page.goto("/research");
    await expect(page.getByRole("heading", { name: "New research" })).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Model" })).toBeVisible();

    await page.goto("/about");
    await expect(page.getByRole("heading", { name: "Architecture" })).toBeVisible();

    await page.goto(`/research/${job.id}`);
    await expectAllAgents(page, "completed");
    await expect(page.getByRole("article", { name: "Report" })).toBeVisible();

    await page.goto("/not-a-page");
    await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();

    expect(errors, `console errors in ${colorScheme} mode`).toEqual([]);
    page.removeAllListeners("console");
    page.removeAllListeners("pageerror");
  }
});
