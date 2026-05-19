import { test, expect } from "@playwright/test";

test("pokédex list loads and shows Pokémon", async ({ page }) => {
  await page.goto("/pokedex");
  await expect(page.locator("h1")).toContainText("Pokédex");
  // Wait for first-generation starters — proves data fetched and rendered
  await expect(page.getByText(/Bulbasaur|Bulbizarre/i).first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/Charmander|Salamèche/i).first()).toBeVisible();
  // At least a full page of cards (PAGE_SIZE = 40)
  const cards = page.locator("a[href^='/pokedex/']");
  await expect(cards.count()).resolves.toBeGreaterThanOrEqual(40);
});

test("pokédex search filters results", async ({ page }) => {
  await page.goto("/pokedex");
  // Wait for initial data before searching
  await expect(page.getByText(/Bulbasaur|Bulbizarre/i).first()).toBeVisible({ timeout: 15_000 });

  const input = page.getByPlaceholder(/Bulbasaur|Rechercher/i);
  await input.fill("Charizard");

  // After search, Bulbasaur should disappear and only Charizard-related entries remain
  await expect(page.getByText(/Bulbasaur|Bulbizarre/i).first()).not.toBeVisible({
    timeout: 5_000,
  });
  await expect(page.getByText(/Dracaufeu|Charizard/i).first()).toBeVisible();
});

test("pokédex detail page — Charizard", async ({ page }) => {
  await page.goto("/pokedex/6");
  const heading = page.locator("h1, h2").filter({ hasText: /Charizard|Dracaufeu/i });
  await expect(heading.first()).toBeVisible({ timeout: 15_000 });
  // Fire type badge must be present
  await expect(page.getByText(/Feu|Fire/i).first()).toBeVisible();
});
