import { expect, type Page } from "@playwright/test";

export const JOB_URL = /\/research\/[0-9a-f]{32}$/;

export const AGENTS = ["Research Agent", "Coding Agent", "Manager Agent"] as const;

/** A topic that is unique per test run, so the server never returns an older active job. */
export function uniqueTopic(base: string): string {
  return `${base} (${Date.now().toString(36)})`;
}

/** Collect console errors and uncaught exceptions for the lifetime of the page. */
export function trackConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  return errors;
}

export function agentCard(page: Page, name: (typeof AGENTS)[number]) {
  return page.getByRole("article", { name });
}

export function jobStatus(page: Page) {
  return page.getByTestId("job-status");
}

/** Submit a topic from the workspace form and wait for the job page. */
export async function startFromWorkspace(page: Page, topic: string): Promise<void> {
  await page.goto("/research");
  await page.getByLabel("Research topic").fill(topic);
  await page.getByRole("button", { name: "Start research" }).click();
  await expect(page).toHaveURL(JOB_URL);
  await expect(page.getByRole("heading", { level: 1, name: topic })).toBeVisible();
}

export async function expectAllAgents(page: Page, status: string): Promise<void> {
  for (const name of AGENTS) {
    await expect(agentCard(page, name)).toHaveAttribute("data-status", status);
  }
}

/** True when the page can be scrolled sideways (a layout bug on small screens). */
export async function hasHorizontalOverflow(page: Page): Promise<boolean> {
  return page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
}
