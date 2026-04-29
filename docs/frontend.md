# Frontend

Next.js 15 (App Router) + TypeScript. Rendu SSR par défaut, déploiement en mode `output: "standalone"` dans Docker.

## Organisation

```
frontend/
  app/
    (routes pages)
    pokedex/            # liste + fiche avec onglets lazy
    fusion/             # sélecteur + résultat
    ai/                 # chat IA plein écran
    moves/              # liste référentielle
    types/              # liste référentielle
    abilities/          # liste référentielle
    api/[...path]/      # proxy catch-all → backend
    sprites-cdn/[...]/  # proxy catch-all → sidecar nginx (PNG)
  components/
    pokemon/            # EvolutionChain, MovesetTable, PokemonCard, StatBar, TypeBadge, WeaknessGrid
    fusion/             # FusionSelector, FusionSprite, FusionMovesetTable
    ai/                 # AiChat, AiSuggestButton
    layout/             # Navbar, SearchBar
  hooks/
    usePokemon.ts       # usePokemon, usePokemonList, usePokemonMoves, usePokemonEvolutions,
                        # usePokemonWeaknesses, usePokemonSearch, useTypes
    useFusion.ts        # useFusion, useFusionMoves, useFusionExpertMoves, useSprites
    useMoves.ts         # useMoves, useMove, useMovesByType
    useAiChat.ts        # gestion état SSE + streaming tokens
  lib/
    api.ts              # client fetch centralisé (toutes les fonctions API)
    constants.ts        # API_BASE_URL, TYPE_COLORS, METHOD_LABELS, basePokemonSprite()
    utils.ts            # cn(), formatters, primaryType(), secondaryType()
  types/
    api.d.ts            # miroir des schémas Pydantic (PokemonListItem, FusionResult, SpriteOut…)
```

## Pages

| Route                                  | Contenu                                                                   |
| -------------------------------------- | ------------------------------------------------------------------------- |
| `/`                                    | Landing                                                                   |
| `/pokedex`                             | Liste paginée (40/page) + recherche accent-insensitive + filtre par type  |
| `/pokedex/[id]`                        | Fiche avec onglets : Stats · Capacités · Évolutions · Faiblesses · Fusion |
| `/fusion`                              | Sélecteur head/body (pré-sélection via `?head=ID&?body=ID`)               |
| `/fusion/[headId]/[bodyId]`            | Résultat : double sprite + crédit artiste + stats + moveset + fusion IA   |
| `/ai`                                  | Chat IA plein écran avec suggestions et historique                        |
| `/moves`                               | Liste + recherche + filtre par type                                       |
| `/types`                               | Grille des 18 types + matchups                                            |
| `/abilities`                           | Liste + recherche                                                         |

## Proxy Next.js

Tous les appels réseau du navigateur passent par Next :

- `GET /api/pokemon/1` → route handler → `fetch(BACKEND_INTERNAL_URL + "/pokemon/1")`
- `GET /sprites-cdn/CustomBattlers/1.1.png` → route handler → sidecar nginx

Deux bénéfices :

1. **Zéro fuite d'URL backend** dans le bundle client. Le navigateur ne voit que `/api/*`.
2. **Config runtime** : `BACKEND_INTERNAL_URL` est lu à chaque requête (pas d'env bakée au build), on peut changer la cible sans rebuild.

Implémentation : [frontend/app/api/[...path]/route.ts](https://github.com/benjsant/FusionDex-IA/blob/main/frontend/app/api/%5B...path%5D/route.ts) et [frontend/app/sprites-cdn/[...path]/route.ts](https://github.com/benjsant/FusionDex-IA/blob/main/frontend/app/sprites-cdn/%5B...path%5D/route.ts).

!!! note "Pourquoi pas `next.config.ts` rewrites ?"
    Next.js standalone fige les destinations de rewrite dans `.next/required-server-files.json` au build. Les route handlers, eux, évaluent `process.env` à chaque requête — c'est ce qu'on veut.

## Stratégie de cache React Query

Toutes les données Pokémon sont statiques entre deux déploiements. Tous les hooks appliquent `staleTime: Infinity` — aucun refetch en arrière-plan après le premier chargement.

Les requêtes de détail sont **déclenchées à la demande** :

- **Onglets Pokédex** : `usePokemonMoves`, `usePokemonEvolutions`, `usePokemonWeaknesses` n'envoient leur requête que lorsque l'onglet correspondant est actif (`enabled: activeTab === "moves"`). Économie de 3 requêtes par première visite.
- **Dropdown FusionSelector** : `usePokemonList` n'est activé qu'à l'ouverture du dropdown (`enabled: open`).

## Hooks

| Hook | Fichier | Déclenché quand |
|------|---------|-----------------|
| `usePokemon(id)` | usePokemon.ts | toujours (fiche ouverte) |
| `usePokemonMoves(id, opts)` | usePokemon.ts | onglet "Capacités" actif |
| `usePokemonEvolutions(id, opts)` | usePokemon.ts | onglet "Évolutions" actif |
| `usePokemonWeaknesses(id, opts)` | usePokemon.ts | onglet "Faiblesses" actif |
| `usePokemonList(params, opts)` | usePokemon.ts | dropdown ouvert |
| `usePokemonSearch(q)` | usePokemon.ts | `q.length >= 2` |
| `useFusion(hId, bId)` | useFusion.ts | toujours (page fusion) |
| `useFusionMoves(hId, bId)` | useFusion.ts | toujours (page fusion) |
| `useFusionExpertMoves(hId, bId)` | useFusion.ts | toujours (page fusion) |
| `useSprites(hId, bId)` | useFusion.ts | toujours (page fusion) |
| `useAiChat()` | useAiChat.ts | message envoyé |

Les hooks sont typés à partir de `types/api.d.ts` — tout changement de schéma backend casse la compilation (fail-fast).

## Composants clés

### FusionSelector

Sélecteur head/body avec recherche intégrée. Lit `?head=ID` et `?body=ID` depuis les search params au montage pour pré-sélectionner un Pokémon (utilisé par les liens "Fusionner en tant que Tête" de la fiche Pokédex).

### FusionMovesetTable

Tableau du moveset d'une fusion, groupé par méthode d'apprentissage (niveau, reproduction, donneur, CT, donneur expert). Chaque ligne affiche une pastille d'origine :

- **H** (indigo) — capacité apprise par le Pokémon tête uniquement
- **B** (violet) — capacité apprise par le Pokémon corps uniquement
- **H+B** (dégradé) — apprise par les deux

### AiChat

Chat IA avec streaming SSE. Gère deux types d'événements :

- `tool_call` → pastille ⚙ affichée avant la réponse (transparence des outils invoqués)
- `token` → chunk accumulé dans la bulle de réponse avec `scrollIntoView` progressif

Le scroll distingue l'ajout d'un nouveau message (smooth) de l'arrivée d'un token (instant) via `prevMessageCountRef` — évite le jitter visuel pendant le streaming.

### FusionSprite

Sprite de fusion extrait d'un spritesheet 1920×2784 (20 colonnes × 29 lignes de 96×96px) hébergé par Infinite Fusion. Rendu par `background-position` CSS — aucun téléchargement d'image individuelle.

## i18n

Le projet est bilingue EN/FR côté données (colonnes `name_en` / `name_fr`). L'UI affiche en priorité le nom français quand disponible, avec le nom anglais entre parenthèses. L'assistant IA répond toujours en français (règle dans le system prompt).

## Dev

```bash
cd frontend
npm install
npm run dev    # http://localhost:3000
```

Pour lancer avec le backend dockerisé :

```bash
docker compose up -d            # lance tout
# Le frontend est sur http://localhost:53000
```

## Build

```bash
docker compose build frontend
```

Le Dockerfile multi-stage n'a **aucun** `ARG` pointant vers le backend : tout passe par les env runtime (`BACKEND_INTERNAL_URL`, `SPRITES_INTERNAL_URL`).

## Voir aussi

- [Architecture](architecture.md) — flux de requêtes proxy + flux SSE IA.
- [API backend](api.md) — endpoints consommés.
