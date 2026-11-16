import { expect, test } from "@playwright/test";
import { JOB_URL, agentCard, expectAllAgents, jobStatus, trackConsoleErrors, uniqueTopic } from "./helpers";

test("full journey: landing → live agents → report, sources, copy and download", async ({ page, context, baseURL }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"], { origin: baseURL });
  const errors = trackConsoleErrors(page);
  const topic = uniqueTopic("Vector databases for retrieval-augmented generation");

  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Research any topic with a team of AI agents" })).toBeVisible();
  await page.getByLabel("Research topic").fill(topic);
  await page.getByRole("button", { name: "Start research" }).click();

  // The landing page hands the topic to the workspace, which submits it.
  await expect(page).toHaveURL(JOB_URL);
  await expect(page.getByRole("heading", { level: 1, name: topic })).toBeVisible();

  // The three agents progress to completed, driven by real backend data.
  await expectAllAgents(page, "completed");
  await expect(jobStatus(page)).toHaveText("Completed");
  const research = agentCard(page, "Research Agent");
  await expect(research.getByText("Web searches").locator("xpath=following-sibling::dd")).toHaveText("2");
  await expect(research.getByText("Took")).toBeVisible();

  // Activity timeline lists the real events.
  const timeline = page.getByRole("list", { name: "Run events" });
  await expect(timeline).toContainText("Searched “overview”");
  await expect(timeline).toContainText("Searched “best practices”");
  await expect(timeline).toContainText("Report ready");

  // The report renders with GFM, highlighting and safe links.
  const report = page.getByRole("article", { name: "Report" });
  await expect(report.getByRole("heading", { name: "Executive Summary" })).toBeVisible();
  await expect(report.locator("code.hljs.language-python")).toBeVisible();
  await expect(report.getByRole("link", { name: "the docs" })).toHaveAttribute("rel", "noopener noreferrer nofollow");
  await expect(report.getByRole("link", { name: "the docs" })).toHaveAttribute("target", "_blank");

  // Citation check flags the link that search never returned.
  const citation = page.getByTestId("citation-panel");
  await expect(citation).toContainText("1 of 2 links in the report were found");
  await expect(citation).toContainText("Not found in retrieved search results — verify before relying on them");
  await expect(citation.getByRole("link", { name: "https://unverified.example.net/page" })).toBeVisible();

  await expect(page.getByText("Groq", { exact: false }).first()).toBeVisible();
  await expect(page.getByTestId("ephemeral-notice")).toContainText("may be cleared when the server restarts");

  // Sources tab.
  await page.getByRole("tab", { name: /^Sources/ }).click();
  const sources = page.getByRole("tabpanel", { name: /^Sources/ });
  await expect(sources.getByRole("link", { name: /Official documentation/ })).toBeVisible();
  await expect(sources).toContainText("docs.example.org");
  await expect(sources).toContainText("Found by the query “overview”");
  await expect(sources).toContainText("An authoritative overview of the topic.");
  await expect(sources).toContainText("Cited in report");

  // The other agent outputs.
  await page.getByRole("tab", { name: "Research notes" }).click();
  await expect(page.getByRole("tabpanel", { name: "Research notes" })).toContainText("Research notes.");
  await page.getByRole("tab", { name: "Code examples" }).click();
  await expect(page.getByRole("tabpanel", { name: "Code examples" }).locator("code.hljs")).toContainText("print('hello')");
  await page.getByRole("tab", { name: "Methodology" }).click();
  await expect(page.getByRole("tabpanel", { name: "Methodology" })).toContainText("Search queries executed");

  // Keyboard navigation between tabs.
  await page.getByRole("tab", { name: "Methodology" }).press("Home");
  await expect(page.getByRole("tab", { name: "Report" })).toBeFocused();
  await expect(page.getByRole("tab", { name: "Report" })).toHaveAttribute("aria-selected", "true");

  // Copy the report.
  await page.getByRole("button", { name: "Copy report" }).click();
  await expect(page.getByRole("button", { name: "Copied" })).toBeVisible();
  const clipboard = await page.evaluate(() => navigator.clipboard.readText());
  expect(clipboard).toContain("## Executive Summary");
  expect(clipboard).toContain("https://docs.example.org/guide");

  // Download Markdown and JSON.
  const markdown = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download Markdown" }).click();
  expect((await markdown).suggestedFilename()).toMatch(/^research-.+\.md$/);
  const json = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download JSON" }).click();
  expect((await json).suggestedFilename()).toMatch(/\.json$/);

  // The run is remembered in this browser and can be reopened.
  const jobUrl = page.url();
  await page.getByRole("link", { name: "New research" }).first().click();
  await expect(page).toHaveURL(/\/research$/);
  const history = page.getByRole("region", { name: /Your recent research/ });
  await history.getByRole("link", { name: new RegExp(topic.replace(/[()]/g, "\\$&")) }).click();
  await expect(page).toHaveURL(jobUrl);
  await expect(page.getByRole("article", { name: "Report" })).toBeVisible();

  expect(errors).toEqual([]);
});

test("theme toggle persists the choice across reloads", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/about");
  await expect(page.locator("html")).not.toHaveClass(/dark/);
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.reload();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await expect(page.getByRole("button", { name: "Switch to light theme" })).toBeVisible();
});
