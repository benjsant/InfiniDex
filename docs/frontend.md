# Frontend

Next.js 15 (App Router) + TypeScript. Rendu SSR par défaut, déploiement en mode `output: "standalone"` dans Docker.

## Organisation

```
frontend/
  app/
    pokedex/            # liste paginée + fiche (onglets lazy)
    pokedex/[id]/       # fiche Pokémon (Stats · Capacités · Évolutions · Faiblesses · Fusion)
    fusion/             # sélecteur + bouton aléatoire
    fusion/[headId]/[bodyId]/  # résultat : sprite + stats + moveset
    ai/                 # chat IA plein écran
    moves/              # liste paginée (50/page) + recherche + filtre type/catégorie
    moves/[id]/         # fiche capacité (description, stats, type)
    moves/tutors/       # maîtres des capacités + Move Experts
    abilities/          # liste paginée (40/page) + détail inline
    abilities/[id]/     # fiche talent (description, notes IF-modified)
    types/              # tableau d'efficacité 18 × 18
    triple-fusions/     # 23 fusions triples légendaires
    creators/           # galerie créateurs de sprites (pagination 48/page)
    creators/[id]/      # galerie sprites d'un créateur
    api/[...path]/      # proxy catch-all → backend
    sprites-cdn/[...]/  # proxy catch-all → sidecar nginx (PNG)
  components/
    pokemon/            # EvolutionChain, MovesetTable, PokemonCard, StatBar, TypeBadge, WeaknessGrid
    fusion/             # FusionSelector (+ random), FusionSprite, FusionMovesetTable, CreatorModal
    ai/                 # AiChat (source badges, token counter), AiSuggestButton, PromptModal
    layout/             # Navbar (theme toggle), SearchBar, ErrorBoundary
  hooks/
    usePokemon.ts       # usePokemon, usePokemonList, usePokemonMoves, usePokemonEvolutions,
                        # usePokemonWeaknesses, usePokemonSearch, useTypes
    useFusion.ts        # useFusion, useFusionMoves, useFusionExpertMoves, useSprites
    useMoves.ts         # useMoves, useMove, useMovesByType
    useAiChat.ts        # gestion état SSE + streaming tokens + source/usage events
  lib/
    api.ts              # client fetch centralisé (toutes les fonctions API)
    constants.ts        # API_BASE_URL, TYPE_COLORS, METHOD_LABELS, basePokemonSprite()
    utils.ts            # cn(), formatters, primaryType(), secondaryType()
    theme.tsx           # ThemeProvider + useTheme hook (dark/light)
  types/
    api.d.ts            # miroir des schémas Pydantic (PokemonListItem, FusionResult, FusionInvolvingOut…)
```

## Pages

| Route                                  | Contenu                                                                       |
| -------------------------------------- | ----------------------------------------------------------------------------- |
| `/`                                    | Landing — grille des modules                                                  |
| `/pokedex`                             | Liste paginée (40/page) + recherche accent-insensitive + filtres type/légendaire |
| `/pokedex/[id]`                        | Fiche avec onglets : Stats · Capacités · Évolutions · Faiblesses · Fusion     |
| `/fusion`                              | Sélecteur head/body + bouton fusion aléatoire (🔀)                            |
| `/fusion/[headId]/[bodyId]`            | Résultat : double sprite + crédit artiste + stats + moveset + fusion IA       |
| `/ai`                                  | Chat IA plein écran avec suggestions, pastilles ⚙ outils, badges sources     |
| `/moves`                               | Liste paginée (50/page) + recherche + filtre type/catégorie                   |
| `/moves/[id]`                          | Fiche capacité : type, catégorie, puissance, PP, description FR/EN            |
| `/moves/tutors`                        | Tuteurs classiques groupés par lieu + Move Experts groupés par île            |
| `/abilities`                           | Liste paginée (40/page) + panneau détail inline + lien fiche complète         |
| `/abilities/[id]`                      | Fiche talent : description FR/EN, badge "Modifié IF", notes                  |
| `/types`                               | Grille d'efficacité 18 × 18 types Gen 7                                       |
| `/triple-fusions`                      | 23 fusions triples légendaires avec stats et faiblesses                       |
| `/creators`                            | Galerie paginée des créateurs de sprites (recherche)                          |
| `/creators/[id]`                       | Grille de tous les sprites d'un créateur, cliquables vers la fusion           |

## Proxy Next.js

Tous les appels réseau du navigateur passent par Next :

- `GET /api/pokemon/1` → route handler → `fetch(BACKEND_INTERNAL_URL + "/pokemon/1")`
- `GET /sprites-cdn/CustomBattlers/1.1.png` → route handler → sidecar nginx

Deux bénéfices :

1. **Zéro fuite d'URL backend** dans le bundle client. Le navigateur ne voit que `/api/*`.
2. **Config runtime** : `BACKEND_INTERNAL_URL` est lu à chaque requête (pas d'env bakée au build), on peut changer la cible sans rebuild.

!!! note "Pourquoi pas `next.config.ts` rewrites ?"
    Next.js standalone fige les destinations de rewrite dans `.next/required-server-files.json` au build. Les route handlers, eux, évaluent `process.env` à chaque requête — c'est ce qu'on veut.

## Stratégie de cache React Query

Toutes les données Pokémon sont statiques entre deux déploiements. Tous les hooks appliquent `staleTime: Infinity` — aucun refetch en arrière-plan après le premier chargement.

Les requêtes de détail sont **déclenchées à la demande** :

- **Onglets Pokédex** : `usePokemonMoves`, `usePokemonEvolutions`, `usePokemonWeaknesses`, `getFusionsInvolving` n'envoient leur requête que lorsque l'onglet correspondant est actif.
- **Dropdown FusionSelector** : `usePokemonList` n'est activé qu'à l'ouverture du dropdown.

## Hooks & fonctions API clés

| Hook / Fonction API | Fichier | Déclenché quand |
|---------------------|---------|-----------------|
| `usePokemon(id)` | usePokemon.ts | toujours (fiche ouverte) |
| `usePokemonMoves(id, opts)` | usePokemon.ts | onglet "Capacités" actif |
| `usePokemonEvolutions(id, opts)` | usePokemon.ts | onglet "Évolutions" actif |
| `usePokemonWeaknesses(id, opts)` | usePokemon.ts | onglet "Faiblesses" actif |
| `getFusionsInvolving(id, 24)` | api.ts | onglet "Fusion" actif |
| `getRandomFusion()` | api.ts | clic bouton Shuffle |
| `usePokemonList(params, opts)` | usePokemon.ts | dropdown ouvert |
| `useFusion(hId, bId)` | useFusion.ts | toujours (page fusion) |
| `useAiChat()` | useAiChat.ts | message envoyé |

Les hooks sont typés à partir de `types/api.d.ts` — tout changement de schéma backend casse la compilation (fail-fast).

## Composants clés

### FusionSelector

Sélecteur head/body avec recherche intégrée. Lit `?head=ID` et `?body=ID` depuis les search params au montage pour pré-sélectionner un Pokémon.

Inclut un filtre de jeu (`GameFilter = "kanto" | "hoenn" | "all"`) et un **bouton fusion aléatoire** (icône Shuffle) qui appelle `GET /fusion/random` et redirige directement vers la page résultat.

### FusionMovesetTable

Tableau du moveset d'une fusion, groupé par méthode d'apprentissage. Chaque ligne affiche une pastille d'origine :

- **H** (indigo) — capacité apprise par le Pokémon tête uniquement
- **B** (violet) — capacité apprise par le Pokémon corps uniquement
- **H+B** (dégradé) — apprise par les deux

### AiChat

Chat IA avec streaming SSE. Gère quatre types d'événements :

- `tool_call` → pastille ⚙ affichée avant la réponse (transparence des outils)
- `token` → chunk accumulé dans la bulle de réponse
- `source` → badges colorés DB/Wiki/Web sous la réponse
- `usage` → compteur de tokens affiché à côté des sources

Le composant expose un bouton 👁 (Eye) qui ouvre `PromptModal` — transparency layer affichant le system prompt complet, la liste des outils disponibles et la politique de contexte.

### FusionSprite

Sprite de fusion extrait d'un spritesheet 1920×2784 (20 colonnes × 29 lignes de 96×96px) hébergé par Infinite Fusion. Rendu par `background-position` CSS — aucun téléchargement d'image individuelle.

## Design system IF

### Thème sombre / clair

Le site supporte un toggle dark/light persistant dans `localStorage`. Implémenté via :

- **CSS variables** : 16 tokens dans `globals.css` via `@theme` (Tailwind v4), overridés dans `[data-theme="light"]`
- **ThemeProvider** (`lib/theme.tsx`) : contexte React + `useTheme()` hook
- **Anti-flash script** : script inline dans `<head>` qui lit `localStorage` avant hydration React
- **Toggle** : bouton ☀/🌙 dans la Navbar

Tokens principaux (dark → light) :

| Token | Sombre | Clair |
|-------|--------|-------|
| `--color-if-bg` | `#090c1a` | `#f0f2ff` |
| `--color-if-card` | `#111428` | `#ffffff` |
| `--color-if-text` | `#e1e4ff` | `#1a1c35` |
| `--color-if-muted` | `#6b7199` | `#5a5e80` |
| `--color-if-accent` | `#e8b84b` | `#e8b84b` |

### Composants visuels

- `TypeBadge` : fond coloré par type + `box-shadow` glow avec la couleur du type.
- `PokemonCard` : gradient `linear-gradient` du type primaire.
- `StatBar` : dégradé horizontal avec couleur selon la valeur (vert ≥ 100, jaune ≥ 60, rouge sinon).
- `.if-panel` / `.if-panel-hi` : classes utilitaires pour les cartes avec border et fond tokenisés.
- `.if-glow-hover` : glow gold au survol.
- Grid texture en `background-image` (adaptée en mode clair).

### Responsive

Stratégie mobile-first :

- **Navbar** : hamburger `md:hidden` ouvre un drawer full-width sur mobile.
- **Tables** : colonnes secondaires masquées via `hidden sm:table-cell`.
- **Panels** : `flex-col md:flex-row` — empilés sur mobile, côte à côte sur desktop.
- **Grilles** : `grid-cols-2 sm:grid-cols-3 md:grid-cols-4` pour les cartes Pokémon.

## i18n

Le projet est bilingue EN/FR côté données (colonnes `name_en` / `name_fr`). L'UI affiche en priorité le nom français. L'assistant IA répond toujours en français (règle dans le system prompt).

## Build & Dev

```bash
# Tout via Docker
docker compose up -d --build frontend

# Rebuild après changement de dépendances npm
docker run --rm -v ./frontend:/app -w /app node:22-alpine npm install --package-lock-only
docker compose up -d --build frontend
```

## Voir aussi

- [Architecture](architecture.md) — flux de requêtes proxy + flux SSE IA.
- [API backend](api.md) — endpoints consommés.
