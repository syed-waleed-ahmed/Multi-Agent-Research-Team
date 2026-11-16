import { expect, test } from "@playwright/test";
import { expectAllAgents, hasHorizontalOverflow, startFromWorkspace, uniqueTopic } from "./helpers";

test.use({ viewport: { width: 360, height: 740 }, isMobile: true, hasTouch: true });

test("landing and navigation work at 360px without horizontal scrolling", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  expect(await hasHorizontalOverflow(page)).toBe(false);

  // Desktop navigation collapses into a menu.
  await expect(page.getByRole("navigation", { name: "Main" })).toBeHidden();
  await page.getByRole("button", { name: "Open menu" }).click();
  const mobileNav = page.getByRole("navigation", { name: "Mobile" });
  await expect(mobileNav).toBeVisible();
  await mobileNav.getByRole("link", { name: "About & docs" }).click();
  await expect(page).toHaveURL(/\/about$/);
  await expect(mobileNav).toBeHidden();
  expect(await hasHorizontalOverflow(page)).toBe(false);
});

test("a full run and its report fit a 360px screen", async ({ page }) => {
  await startFromWorkspace(page, uniqueTopic("Mobile layout check for a long research topic name"));
  expect(await hasHorizontalOverflow(page)).toBe(false);

  await expectAllAgents(page, "completed");
  await expect(page.getByRole("article", { name: "Report" })).toBeVisible();
  expect(await hasHorizontalOverflow(page)).toBe(false);

  await page.getByRole("tab", { name: /^Sources/ }).click();
  await expect(page.getByRole("tabpanel", { name: /^Sources/ })).toContainText("docs.example.org");
  expect(await hasHorizontalOverflow(page)).toBe(false);
});
