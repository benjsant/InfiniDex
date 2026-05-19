import { test, expect } from "@playwright/test";

test("homepage loads with title and stats", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("InfiniDex");
  // Stats counters (Pokémon, fusions, sprites) — at least one numeric value visible
  const stats = page.locator("span.font-mono");
  await expect(stats.first()).toBeVisible({ timeout: 10_000 });
  const text = await stats.first().innerText();
  expect(parseInt(text.replace(/\s/g, ""), 10)).toBeGreaterThan(0);
});

test("homepage navbar links are present after hydration", async ({ page }) => {
  await page.goto("/");
  // Multiple "Pokédex" links on page (nav + feature card) — nav link is the shortest
  await expect(page.locator("nav a[href='/pokedex']").first()).toBeVisible({ timeout: 10_000 });
  // "Fusion" is a dropdown trigger in the nav
  await expect(page.locator("nav").getByText("Fusion").first()).toBeVisible({ timeout: 5_000 });
});
