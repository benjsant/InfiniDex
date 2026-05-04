import { test, expect } from "@playwright/test";

test("pokédex charge les cartes Pokémon", async ({ page }) => {
  await page.goto("/pokedex");
  await expect(page.getByRole("heading", { name: "Pokédex" })).toBeVisible();
  // Au moins une carte présente (lien vers /pokedex/<id>)
  await expect(page.locator("a[href^='/pokedex/']").first()).toBeVisible({ timeout: 15_000 });
});

test("filtre légendaires réduit le nombre de résultats", async ({ page }) => {
  await page.goto("/pokedex");
  // Attendre le chargement initial
  await expect(page.locator("a[href^='/pokedex/']").first()).toBeVisible({ timeout: 15_000 });
  const totalBefore = await page.locator("a[href^='/pokedex/']").count();

  await page.getByRole("button", { name: /Légendaires/ }).click();
  // Après filtre, moins de Pokémon (33 légendaires vs 501+)
  await page.waitForTimeout(500);
  const totalAfter = await page.locator("a[href^='/pokedex/']").count();
  expect(totalAfter).toBeLessThan(totalBefore);
});

test("page détail Pokémon accessible depuis la liste", async ({ page }) => {
  await page.goto("/pokedex");
  await expect(page.locator("a[href^='/pokedex/']").first()).toBeVisible({ timeout: 15_000 });
  await page.locator("a[href^='/pokedex/']").first().click();
  // La page détail affiche au moins les stats
  await expect(page).toHaveURL(/\/pokedex\/\d+/);
  await expect(page.locator("text=PV").or(page.locator("text=HP"))).toBeVisible({ timeout: 10_000 });
});
