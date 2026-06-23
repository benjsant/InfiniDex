# Captures d'écran

Aperçu visuel de toutes les pages de InfiniDex. Captures générées automatiquement via Playwright (`docker compose --profile screenshots run --rm screenshots`).

---

## Mode sombre (défaut)

### Accueil

![Homepage desktop](imgs/homepage-desktop.webp)

---

### Pokédex

![Pokédex liste](imgs/pokedex-list.webp)

![Fiche Pokémon](imgs/pokedex-detail.webp)

---

### Calculateur de fusion

![Sélecteur de fusion](imgs/fusion-selector.webp)

---

### Résultat de fusion

![Résultat fusion](imgs/fusion-result.webp)

---

### Comparateur de fusions

![Comparateur](imgs/fusion-compare.webp)

---

### Top fusions

![Top fusions par BST](imgs/fusion-top.webp)

---

### Triple fusions

![Triple fusions](imgs/triple-fusions.webp)

---

### Table des types

![Table d'efficacité des types](imgs/types-chart.webp)

---

### Assistant IA

![Assistant IA](imgs/ai-chat.webp)

---

### Capacités

![Liste des capacités](imgs/moves-list.webp)

---

### Tuteurs de capacités

![Tuteurs](imgs/moves-tutors.webp)

---

### Talents

![Talents](imgs/abilities-list.webp)

---

### Objets

![Objets](imgs/items-list.webp)

---

### Créateurs de sprites

![Galerie créateurs](imgs/creators-gallery.webp)

---

### Recherche globale

![Recherche globale](imgs/search-overlay.webp)

---

### Carousel de sprites

![Carousel sprites créateurs](imgs/fusion-sprite-carousel.webp)

---

### Historique des fusions

![Historique](imgs/fusion-history.webp)

---

### Favoris Pokédex

![Favoris Pokédex](imgs/pokedex-favorites.webp)

---

## Mode clair

Le mode clair est activé via le bouton ☀️ dans la navbar. Le thème est persisté dans `localStorage`.

=== "Accueil"
    ![Accueil mode clair](imgs/theme-light-homepage.webp)

=== "Pokédex"
    ![Pokédex mode clair](imgs/theme-light-pokedex.webp)

=== "Fusion"
    ![Fusion mode clair](imgs/theme-light-fusion.webp)

=== "Table des types"
    ![Types mode clair](imgs/theme-light-types.webp)

---

## Mobile (390 × 844)

=== "Accueil"
    ![Mobile accueil](imgs/mobile-homepage.webp)

=== "Pokédex"
    ![Mobile pokédex](imgs/mobile-pokedex.webp)

=== "Fusion"
    ![Mobile fusion](imgs/mobile-fusion.webp)

=== "Types"
    ![Mobile types interactif](imgs/mobile-types.webp)

=== "IA"
    ![Mobile IA](imgs/mobile-ai.webp)

=== "Navbar drawer"
    ![Mobile navbar](imgs/mobile-navbar.webp)

=== "Mode clair"
    ![Mobile mode clair](imgs/mobile-theme-light.webp)

---

## Régénérer les captures

```bash
docker compose --profile screenshots run --rm screenshots
```

Les images sont produites par défaut dans `../infinidex-assets/screenshots/` (dossier sibling du repo, hors versionning Git) puis copiées dans `docs/imgs/` :

```bash
# Copie rapide après régénération
for src in ../infinidex-assets/screenshots/*.webp; do
  name=$(basename "$src")
  # Voir scripts/screenshots.mjs pour la correspondance complète
done
```

!!! tip "Personnaliser le dossier de sortie"
    Override possible via `SCREENSHOTS_OUT_DIR=/chemin/voulu node scripts/screenshots.mjs`.

!!! tip "Script de copie"
    Le mapping complet entre noms de fichiers et `docs/imgs/` est défini dans `scripts/screenshots.mjs`.
