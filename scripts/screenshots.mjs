/**
 * FusionDex — captures d'écran automatiques pour la documentation.
 *
 * Prérequis : npx playwright install chromium
 * Lancement  : node scripts/screenshots.mjs
 *
 * Sortie     : screenshots/{nom}.png  (desktop 1280×800)
 *              screenshots/mobile_{nom}.png  (mobile 390×844)
 */

import { chromium } from "playwright";
import { mkdir } from "fs/promises";
import { existsSync } from "fs";

const BASE_URL = process.env.FUSIONDEX_URL ?? "http://localhost:53000";
const OUT_DIR  = new URL("../screenshots/", import.meta.url).pathname;

const DESKTOP = { width: 1280, height: 800 };
const MOBILE  = { width: 390,  height: 844 };

// ── Pages à capturer ─────────────────────────────────────────────────────────

const PAGES = [
  // Core
  { name: "01_accueil",            path: "/",                   wait: "networkidle" },
  { name: "02_pokedex",            path: "/pokedex",            wait: "networkidle" },
  { name: "03_pokedex_fiche",      path: "/pokedex/1",          wait: "networkidle" },
  { name: "04_fusion_calculateur", path: "/fusion",             wait: "networkidle" },
  { name: "05_fusion_resultat",    path: "/fusion/1/4",         wait: "networkidle" },
  { name: "06_fusion_comparateur", path: "/fusion/compare",     wait: "networkidle" },
  { name: "07_fusion_top",         path: "/fusion/top",         wait: "networkidle" },
  { name: "08_triple_fusions",     path: "/triple-fusions",     wait: "networkidle" },
  { name: "09_types_desktop",      path: "/types",              wait: "networkidle" },
  { name: "10_ia_chat",            path: "/ai",                 wait: "networkidle" },
  // Contenu
  { name: "11_capacites",          path: "/moves",              wait: "networkidle" },
  { name: "12_tuteurs",            path: "/moves/tutors",       wait: "networkidle" },
  { name: "13_talents",            path: "/abilities",          wait: "networkidle" },
  { name: "14_objets",             path: "/items",              wait: "networkidle" },
  { name: "15_createurs",          path: "/creators",           wait: "networkidle" },
  { name: "16_historique",         path: "/fusion/history",     wait: "networkidle" },
  { name: "17_favoris_pokedex",    path: "/pokedex/favorites",  wait: "networkidle" },
];

// ── Actions interactives ──────────────────────────────────────────────────────

async function captureSearchOpen(page, name) {
  // Ouvrir la recherche globale via le bouton loupe (GlobalSearch)
  // Le composant utilise un <button> avec Cmd+K hint ou une icône Search
  const searchBtn = page.locator("nav").getByRole("button").filter({ hasText: "" }).last();
  try {
    await searchBtn.click({ timeout: 5000 });
  } catch {
    // Fallback: clic sur n'importe quel bouton de la navbar qui n'est pas le menu
    const navBtns = page.locator("nav button");
    const count = await navBtns.count();
    for (let i = 0; i < count; i++) {
      try { await navBtns.nth(i).click({ timeout: 1000 }); break; } catch { /* try next */ }
    }
  }
  await page.waitForTimeout(600);
  // Taper dans le champ qui vient d'apparaître
  try {
    await page.keyboard.type("char");
    await page.waitForTimeout(800);
  } catch { /* ignore */ }
  await page.screenshot({ path: `${OUT_DIR}${name}.png`, fullPage: false });
}

async function setTheme(page, theme) {
  // Force le thème via localStorage + attribut HTML (bypass React)
  await page.evaluate((t) => {
    localStorage.setItem("theme", t);
    document.documentElement.setAttribute("data-theme", t === "light" ? "light" : "");
  }, theme);
  await page.waitForTimeout(200);
}

async function captureModeLight(page, name) {
  await setTheme(page, "light");
  await page.screenshot({ path: `${OUT_DIR}${name}.png`, fullPage: false });
  await setTheme(page, "dark");
}

async function captureCarousel(page, name) {
  // Sur la page fusion/1/4, scroller jusqu'au carousel de sprites
  const carousel = page.locator('[data-carousel], .carousel, img[alt*="sprite"]').first();
  try {
    await carousel.scrollIntoViewIfNeeded();
  } catch { /* ignore */ }
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT_DIR}${name}.png`, fullPage: false });
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function shot(page, name, { fullPage = true } = {}) {
  await page.screenshot({ path: `${OUT_DIR}${name}.png`, fullPage });
  console.log(`  ✓  ${name}.png`);
}

async function goto(page, path, waitUntil = "networkidle") {
  // /types charge une table 18×18 lourde — timeout étendu
  const timeout = path === "/types" ? 60_000 : 30_000;
  await page.goto(`${BASE_URL}${path}`, { waitUntil, timeout });
  await page.waitForTimeout(600);
}

// ── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  await mkdir(OUT_DIR, { recursive: true });

  const browser = await chromium.launch();
  let ok = 0, fail = 0;

  // ── Desktop ────────────────────────────────────────────────────────────────
  console.log("\n📐 Desktop (1280×800)\n");
  const desktop = await browser.newContext({ viewport: DESKTOP });
  const dp = await desktop.newPage();

  for (const { name, path, wait } of PAGES) {
    try {
      await goto(dp, path, wait);
      await shot(dp, name);
      ok++;
    } catch (err) {
      console.error(`  ✗  ${name} — ${err.message.split("\n")[0]}`);
      fail++;
    }
  }

  // Captures interactives desktop
  try {
    await goto(dp, "/");
    await captureSearchOpen(dp, "18_recherche_globale");
    console.log("  ✓  18_recherche_globale.png"); ok++;
  } catch (err) { console.error(`  ✗  18_recherche_globale — ${err.message.split("\n")[0]}`); fail++; }

  // Captures mode clair sur plusieurs pages
  const LIGHT_PAGES = [
    { name: "19_mode_clair_pokedex",  path: "/pokedex" },
    { name: "19b_mode_clair_accueil", path: "/" },
    { name: "19c_mode_clair_fusion",  path: "/fusion/1/4" },
    { name: "19d_mode_clair_types",   path: "/types" },
  ];
  for (const { name, path } of LIGHT_PAGES) {
    try {
      await goto(dp, path);
      await captureModeLight(dp, name);
      console.log(`  ✓  ${name}.png`); ok++;
    } catch (err) { console.error(`  ✗  ${name} — ${err.message.split("\n")[0]}`); fail++; }
  }

  try {
    await goto(dp, "/fusion/1/4", "load");
    await dp.waitForTimeout(1500);
    await captureCarousel(dp, "20_carousel_sprites");
    console.log("  ✓  20_carousel_sprites.png"); ok++;
  } catch (err) { console.error(`  ✗  20_carousel_sprites — ${err.message.split("\n")[0]}`); fail++; }

  await desktop.close();

  // ── Mobile ─────────────────────────────────────────────────────────────────
  console.log("\n📱 Mobile (390×844)\n");
  const mobile = await browser.newContext({ viewport: MOBILE });
  const mp = await mobile.newPage();

  const MOBILE_PAGES = [
    { name: "mobile_01_accueil",         path: "/" },
    { name: "mobile_02_pokedex",         path: "/pokedex" },
    { name: "mobile_03_fusion_resultat", path: "/fusion/1/4" },
    { name: "mobile_04_types",           path: "/types" },
    { name: "mobile_05_ia",              path: "/ai" },
  ];

  for (const { name, path } of MOBILE_PAGES) {
    try {
      await goto(mp, path);
      await shot(mp, name, { fullPage: false });
      ok++;
    } catch (err) {
      console.error(`  ✗  ${name} — ${err.message.split("\n")[0]}`);
      fail++;
    }
  }

  // Navbar mobile (hamburger ouvert)
  try {
    await goto(mp, "/");
    await mp.locator('[aria-label="Menu"]').click();
    await mp.waitForTimeout(400);
    await mp.screenshot({ path: `${OUT_DIR}mobile_06_navbar_drawer.png`, fullPage: false });
    console.log("  ✓  mobile_06_navbar_drawer.png"); ok++;
  } catch (err) { console.error(`  ✗  mobile_06_navbar_drawer — ${err.message.split("\n")[0]}`); fail++; }

  // Mode clair mobile
  try {
    await goto(mp, "/pokedex");
    await setTheme(mp, "light");
    await mp.screenshot({ path: `${OUT_DIR}mobile_07_mode_clair.png`, fullPage: false });
    await setTheme(mp, "dark");
    console.log("  ✓  mobile_07_mode_clair.png"); ok++;
  } catch (err) { console.error(`  ✗  mobile_07_mode_clair — ${err.message.split("\n")[0]}`); fail++; }

  await mobile.close();
  await browser.close();

  console.log(`\n✅ ${ok} captures réussies${fail ? ` — ⚠️  ${fail} échouées` : ""}`);
  console.log(`📁 Dossier : ${OUT_DIR}\n`);
}

main().catch((err) => { console.error(err); process.exit(1); });
