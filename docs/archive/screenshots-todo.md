# Captures d'écran à effectuer — MkDocs

Dossier cible : `docs/imgs/`  
Résolution desktop : **1440 × 900** — Mobile : **390 × 844** (iPhone 14)  
Format : PNG, nommage kebab-case strict.

---

## 1. Navigation

| Fichier | Route | État à capturer |
|---------|-------|-----------------|
| `navbar-desktop.png` | N'importe quelle page | Navbar complète — logo, 9 liens, lien actif en doré, bouton recherche Ctrl+K |
| `navbar-mobile-closed.png` | N'importe quelle page | Logo + icône hamburger visible, 390px |
| `navbar-mobile-open.png` | N'importe quelle page | Drawer ouvert, tous les liens en colonne |
| `search-overlay-results.png` | N'importe quelle page | Overlay ouvert, requête "pika" → résultats Pokémon + Capacités + Talents |

---

## 2. Homepage

| Fichier | Route | État |
|---------|-------|------|
| `homepage-desktop.png` | `/` | Grille des 8 cartes de navigation, titre gradient visible |
| `homepage-mobile.png` | `/` | Cartes en 2 colonnes, 390px |

---

## 3. Pokédex

| Fichier | Route | État |
|---------|-------|------|
| `pokedex-list.png` | `/pokedex` | Grille par défaut, filtre "IF Kanto" actif, 6 colonnes |
| `pokedex-type-filter.png` | `/pokedex` | Dropdown type ouvert sur "Fire", résultats filtrés visibles |
| `pokedex-search.png` | `/pokedex` | Recherche "charizard" → 1 résultat affiché |
| `pokedex-mobile.png` | `/pokedex` | 2 colonnes de cartes, 390px |
| `pokedex-detail-header.png` | `/pokedex/6` | Header Charizard — sprite, types, talent, ID |
| `pokedex-detail-stats.png` | `/pokedex/6` | Onglet Stats — 6 barres avec valeurs et couleurs |
| `pokedex-detail-moves.png` | `/pokedex/6` | Onglet Capacités — table avec colonnes Type, Cat., Puiss. |
| `pokedex-detail-weaknesses.png` | `/pokedex/6` | Onglet Faiblesses — grille ×2 / ×½ / ×0 |
| `pokedex-detail-evolutions.png` | `/pokedex/4` | Onglet Évolutions — chaîne Charmander → Charmeleon → Charizard |
| `pokedex-detail-fusion-tab.png` | `/pokedex/25` | Onglet Fusion — sprites customs + fusions impliquant ce Pokémon |

---

## 4. Fusion

| Fichier | Route | État |
|---------|-------|------|
| `fusion-selector-empty.png` | `/fusion` | Deux sélecteurs vides, bouton "Sélectionne deux Pokémon" désactivé |
| `fusion-selector-dropdown.png` | `/fusion` | Dropdown gauche ouvert, recherche "bulb" → résultats filtrés |
| `fusion-selector-both-selected.png` | `/fusion` | Pikachu (head) + Charizard (body) sélectionnés, bouton "Fusionner" activé |
| `fusion-result-sprites.png` | `/fusion/25/6` | Deux sprites côte à côte (normal + inversé), créateurs visibles |
| `fusion-result-stats.png` | `/fusion/25/6` | Bloc statistiques — barres fusionnées avec formule |
| `fusion-result-moves.png` | `/fusion/25/6` | Tableau moveset fusionné avec source Head/Body |

---

## 5. Capacités & Tuteurs

| Fichier | Route | État |
|---------|-------|------|
| `moves-list.png` | `/moves` | Table complète — colonnes Capacité, Type, Cat., Puiss., Préc., PP |
| `moves-type-filter.png` | `/moves` | Filtre type "Fire" actif, résultats filtrés |
| `moves-search.png` | `/moves` | Recherche "flare" → résultats matchants |
| `tutors-classic.png` | `/moves/tutors` | Section tuteurs classiques — groupes par lieu avec prix |
| `tutors-experts.png` | `/moves/tutors` | Section Move Experts par île — colonnes Capacité, Pokémon requis, Types |

---

## 6. Types

| Fichier | Route | État |
|---------|-------|------|
| `types-chart-full.png` | `/types` | Tableau complet — en-têtes colorés, cellules ×2 / ×½ / ×0, scrollable |
| `types-chart-if-types.png` | `/types` | Zoom sur les 9 types Triple Fusion (IDs 37-44) en bas du tableau |

---

## 7. Talents

| Fichier | Route | État |
|---------|-------|------|
| `abilities-list.png` | `/abilities` | Liste gauche + panneau détail droit — layout split desktop |
| `abilities-search.png` | `/abilities` | Recherche "static" → talent Statik sélectionné, description visible |
| `abilities-if-badge.png` | `/abilities` | Panneau détail avec badge doré "Modifié dans IF" et notes |

---

## 8. Triple Fusions

| Fichier | Route | État |
|---------|-------|------|
| `triple-fusions-spoiler.png` | `/triple-fusions` | Écran d'avertissement spoiler, bouton "J'accepte" visible |
| `triple-fusions-list.png` | `/triple-fusions` | Liste dévoilée — groupes "Trios légendaires", "Starters Gén. 1", accordéons fermés |
| `triple-fusion-expanded.png` | `/triple-fusions` | Zapmolcuno déplié — sprite + composants + stats + faiblesses |
| `triple-fusion-if-type-badge.png` | `/triple-fusions` | Badge type IF (gradient indigo/violet) à côté d'un badge type normal |

---

## 9. Galerie Créateurs

| Fichier | Route | État |
|---------|-------|------|
| `creators-gallery.png` | `/creators` | Grille 6 colonnes chargée — cartes avec nom + compte sprites |
| `creators-search.png` | `/creators` | Recherche "luki" → cartes filtrées |
| `creators-modal.png` | `/creators` | Modal ouvert — sprites d'un créateur en grille 4-6 colonnes |
| `creators-pagination.png` | `/creators` | Bas de page — boutons "← Précédent", "Page 2", "Suivant →" |
| `creators-mobile.png` | `/creators` | Grille 2 colonnes, 390px |

---

## 10. Assistant IA

| Fichier | Route | État |
|---------|-------|------|
| `ai-empty.png` | `/ai` | État vide — provider affiché, 4 suggestions cliquables, champ de saisie |
| `ai-streaming.png` | `/ai` | Réponse en cours — bulle assistant avec texte en train d'arriver |
| `ai-tool-call.png` | `/ai` | Badge outil visible ("Base de données", "Wiki IF") au-dessus d'une réponse |
| `ai-response-stats.png` | `/ai` | Réponse complète sur "Pikachu × Charizard" — stats formatées en tableau markdown |
| `ai-no-provider.png` | `/ai` | Bannière amber "Aucun provider IA configuré" avec instructions |
| `ai-mobile.png` | `/ai` | Chat sur 390px — bulles pleine largeur, input en bas |

---

## Récapitulatif

| Section | Captures desktop | Captures mobile | Total |
|---------|-----------------|-----------------|-------|
| Navigation | 2 | 2 | 4 |
| Homepage | 1 | 1 | 2 |
| Pokédex | 8 | 1 | 9 |
| Fusion | 6 | — | 6 |
| Capacités & Tuteurs | 5 | — | 5 |
| Types | 2 | — | 2 |
| Talents | 3 | — | 3 |
| Triple Fusions | 4 | — | 4 |
| Galerie Créateurs | 4 | 1 | 5 |
| Assistant IA | 5 | 1 | 6 |
| **Total** | **40** | **6** | **46** |

---

## Comment les faire

### Manuellement (recommandé pour qualité)
1. `docker compose up -d` → ouvrir http://localhost:53000
2. Browser à 1440px (desktop) ou 390px (mobile via DevTools)
3. Screenshot via DevTools → **Capture node** ou extension [GoFullPage](https://gofullpage.com/)
4. Déposer dans `docs/imgs/`

### Semi-automatisé (Playwright)
```bash
cd frontend
npx playwright install chromium
npx playwright screenshot --browser chromium http://localhost:53000/pokedex docs/imgs/pokedex-list.png --viewport-size 1440,900
```

Ou générer un script `scripts/take-screenshots.ts` avec la liste complète (à demander à Claude).
