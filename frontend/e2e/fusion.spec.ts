import { test, expect } from "@playwright/test";

test("page fusion charge les sélecteurs", async ({ page }) => {
  await page.goto("/fusion");
  await expect(page.getByRole("heading", { name: /Fusion/i })).toBeVisible();
  // Deux sélecteurs (tête + corps) présents
  await expect(page.locator("input[placeholder]").first()).toBeVisible({ timeout: 10_000 });
});

test("url directe fusion/1/4 affiche les stats de fusion", async ({ page }) => {
  await page.goto("/fusion/1/4");
  // Bulbizarre (1) × Salamèche (4) — vérifie qu'on a des stats
  await expect(page.locator("text=PV").or(page.locator("text=HP"))).toBeVisible({ timeout: 15_000 });
  // La page doit contenir un lien retour ou un élément de types
  await expect(page.locator("text=Feu").or(page.locator("text=Fire")).or(page.locator("text=Plante"))).toBeVisible({ timeout: 10_000 });
});
