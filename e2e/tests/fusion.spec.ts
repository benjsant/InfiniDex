import { test, expect } from "@playwright/test";

test("fusion page selector loads", async ({ page }) => {
  await page.goto("/fusion");
  // The selector or a heading should be present
  await expect(page.locator("h1, [placeholder]").first()).toBeVisible({ timeout: 10_000 });
});

test("fusion detail — Bulbizarre/Salameche (1/4)", async ({ page }) => {
  await page.goto("/fusion/1/4");
  // h1 contains the fusion name (FR or EN)
  const h1 = page.locator("h1");
  await expect(h1).toBeVisible({ timeout: 10_000 });
  const name = await h1.innerText();
  // Name format is "Head/Body"
  expect(name).toMatch(/\//);
  // Type badges visible
  await expect(page.getByText(/Grass|Plante/i).first()).toBeVisible();
  await expect(page.getByText(/Fire|Feu/i).first()).toBeVisible();
});

test("fusion detail stats are numeric", async ({ page }) => {
  await page.goto("/fusion/1/4");
  // Wait for the page to load
  await page.waitForLoadState("domcontentloaded");
  // HP stat should be a visible number > 0
  // The page renders stats in a list; look for a value that is a digit
  await expect(page.locator("h1")).toBeVisible({ timeout: 10_000 });
  // BST badge or stat row — any 2+ digit number on the page
  const body = await page.textContent("body");
  expect(body).toMatch(/\d{2,}/);
});

test("fusion detail shows moveset tab", async ({ page }) => {
  await page.goto("/fusion/1/4");
  await expect(page.locator("h1")).toBeVisible({ timeout: 10_000 });
  // Moveset table or section
  await expect(page.getByText(/Capacités|Moveset|Move/i).first()).toBeVisible();
});

test("random fusion redirects to a valid fusion URL", async ({ page }) => {
  await page.goto("/fusion/random");
  // Should redirect to /fusion/<n>/<m>
  await page.waitForURL(/\/fusion\/\d+\/\d+/, { timeout: 15_000 });
  expect(page.url()).toMatch(/\/fusion\/\d+\/\d+/);
  await expect(page.locator("h1")).toBeVisible({ timeout: 10_000 });
});
