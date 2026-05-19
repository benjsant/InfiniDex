import { test, expect } from "@playwright/test";

test("types page — chart loads with type labels", async ({ page }) => {
  await page.goto("/types");
  await expect(page.locator("h1")).toContainText(/Tableau|Types/i, { timeout: 10_000 });
  // Type chart table header contains "Normal" — target the visible th cell
  await expect(page.locator("table th").filter({ hasText: "Normal" }).first()).toBeVisible({
    timeout: 5_000,
  });
  // Also contains Feu / Fire labels
  await expect(page.locator("table").getByText(/Feu|Fire/).first()).toBeVisible();
});

test("items page loads and lists items", async ({ page }) => {
  await page.goto("/items");
  await expect(page.locator("h1")).toContainText(/Objets/i, { timeout: 10_000 });
  // Wait for client fetch: DNA Splicers or Heart Scale must appear
  await expect(
    page.getByText(/DNA Splicers|Heart Scale|Écaille Cœur/i).first()
  ).toBeVisible({ timeout: 15_000 });
});

test("moves page loads and lists moves", async ({ page }) => {
  await page.goto("/moves");
  await expect(page.locator("h1")).toContainText(/Capacités/i, { timeout: 10_000 });
  // Wait for table rows to appear after client fetch
  const rows = page.locator("table tbody tr");
  await expect(rows.first()).toBeVisible({ timeout: 15_000 });
  const count = await rows.count();
  expect(count).toBeGreaterThan(10);
});
