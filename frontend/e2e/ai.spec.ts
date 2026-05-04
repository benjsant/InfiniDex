import { test, expect } from "@playwright/test";

test("page IA charge avec les suggestions", async ({ page }) => {
  await page.goto("/ai");
  // Les suggestions de départ sont affichées
  await expect(page.locator("text=Meilleure fusion Dracaufeu")).toBeVisible({ timeout: 10_000 });
  // Le champ de saisie est présent et actif
  const input = page.getByPlaceholder("Pose ta question…");
  await expect(input).toBeVisible();
  await expect(input).toBeEnabled();
});

test("saisie de texte dans le chat fonctionne", async ({ page }) => {
  await page.goto("/ai");
  const input = page.getByPlaceholder("Pose ta question…");
  await input.fill("Où trouver Pikachu ?");
  await expect(input).toHaveValue("Où trouver Pikachu ?");
  // Le bouton Envoyer devient actif
  await expect(page.getByRole("button", { name: "Envoyer" })).toBeEnabled();
});
