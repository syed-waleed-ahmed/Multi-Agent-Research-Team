import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { agentCard, expectAllAgents, startFromWorkspace } from "./helpers";

/**
 * Documentation screenshots (`npm run screenshots`). They are taken against the
 * deterministic E2E test engine, so the report content is test fixture data.
 */
const OUT = fileURLToPath(new URL("../../docs/screenshots/", import.meta.url));

test.use({ viewport: { width: 1440, height: 900 }, colorScheme: "light" });

test("landing page (light)", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: "View on GitHub" })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: `${OUT}landing.png` });
});

test("workspace with agents mid-run", async ({ page }) => {
  await startFromWorkspace(page, "How do vector databases power retrieval-augmented generation? [slow]");
  await expect(agentCard(page, "Research Agent")).toHaveAttribute("data-status", "completed", { timeout: 20_000 });
  await expect(agentCard(page, "Coding Agent")).toHaveAttribute("data-status", "running");
  await page.waitForTimeout(1200); // let the elapsed timer tick so the screenshot shows live timing
  await page.screenshot({ path: `${OUT}workspace-running.png` });
  await page.getByRole("button", { name: "Cancel run" }).click();
  await expect(page.getByTestId("job-status")).toHaveText("Cancelled");
});

test("completed report", async ({ page }) => {
  await startFromWorkspace(page, "Retrieval-augmented generation with vector databases");
  await expectAllAgents(page, "completed");
  const results = page.getByRole("region", { name: "Results" });
  await expect(page.getByRole("article", { name: "Report" })).toBeVisible();
  await results.evaluate((element) => element.scrollIntoView({ block: "start" }));
  await page.evaluate(() => window.scrollBy(0, -88));
  await page.screenshot({ path: `${OUT}report.png` });
});
