# PLAN_FRONTEND.md — InfiniDex Next.js Frontend

## Décision : Tailwind CSS + shadcn/ui (pas MUI)

### Pourquoi pas MUI

| Critère | MUI | Tailwind + shadcn/ui |
|---|---|---|
| Design game-style Pokédex | ❌ Très corporate, difficile à surcharger | ✅ Utility-first, contrôle total |
| Type badges colorés (Feu, Eau…) | ❌ Palette Material imposée | ✅ Classes arbitraires `bg-[#F08030]` |
| Poids bundle | ❌ ~300 KB tree-shaken | ✅ ~10 KB CSS + zero-runtime |
| Sprites pixel-art intégrés | ❌ Conflits avec sx/styled | ✅ Natif avec `next/image` |
| Animations hover cards | ❌ Verbeux avec sx | ✅ `hover:scale-105 transition` |
| shadcn/ui | N/A | ✅ Copier-coller composants accessibles basés Radix |

**Verdict : Tailwind CSS v4 + shadcn/ui.** MUI est parfait pour dashboards B2B, pas pour un Pokédex stylisé.

---

## Stack Frontend

```
Next.js 15 (App Router)
Tailwind CSS v4
shadcn/ui (Dialog, Tooltip, Badge, Select, Tabs, Skeleton, Input)
TanStack Query v5   — data fetching / cache
Zustand             — state global (filtres, historique AI)
next/image          — sprites optimisés
Framer Motion       — animations (optionnel, léger)
```

---

## Architecture des dossiers

```
frontend/
├── app/
│   ├── layout.tsx              # RootLayout + QueryProvider + ThemeProvider
│   ├── page.tsx                # Accueil — hero + recherche rapide
│   ├── pokedex/
│   │   ├── page.tsx            # Liste paginée des 501 Pokémon
│   │   └── [id]/
│   │       └── page.tsx        # Détail Pokémon (stats, moves, evols)
│   ├── fusion/
│   │   ├── page.tsx            # Sélecteur de fusion (head + body)
│   │   └── [headId]/[bodyId]/
│   │       └── page.tsx        # Résultat fusion (stats calculées, sprite)
│   ├── moves/
│   │   └── page.tsx            # Liste capacités avec filtres
│   ├── abilities/
│   │   └── page.tsx            # Liste talents
│   └── ai/
│       └── page.tsx            # Chat DeepSeek — assistant Pokédex
├── components/
│   ├── pokemon/
│   │   ├── PokemonCard.tsx     # Card liste (sprite + types + stats mini)
│   │   ├── PokemonDetail.tsx   # Fiche complète
│   │   ├── StatBar.tsx         # Barre de stat colorée
│   │   ├── TypeBadge.tsx       # Badge type coloré
│   │   ├── MovesetTable.tsx    # Tableau capacités avec méthode/niveau
│   │   ├── EvolutionChain.tsx  # Arbre d'évolutions IF
│   │   └── AbilityTag.tsx      # Talent avec tooltip description
│   ├── fusion/
│   │   ├── FusionSelector.tsx  # Deux PokemonSearchCombobox
│   │   ├── FusionResult.tsx    # Stats fusionnées + sprite
│   │   └── FusionFormula.tsx   # Affiche la formule de calcul
│   ├── ai/
│   │   ├── AiChat.tsx          # Interface chat DeepSeek
│   │   ├── ChatMessage.tsx     # Bulle message user/assistant
│   │   └── AiSuggestButton.tsx # "Demander à l'IA" depuis fiche Pokémon
│   ├── layout/
│   │   ├── Navbar.tsx
│   │   ├── Sidebar.tsx
│   │   └── SearchBar.tsx       # Recherche globale (EN+FR, accents)
│   └── ui/                     # Composants shadcn (auto-générés)
├── lib/
│   ├── api.ts                  # fetch wrappers → FastAPI
│   ├── constants.ts            # TYPE_COLORS, STAT_COLORS, API_BASE_URL
│   └── utils.ts                # cn(), formatStatName(), etc.
├── hooks/
│   ├── usePokemon.ts           # useQuery → GET /pokemon/:id
│   ├── useFusion.ts            # useQuery → GET /fusion/:head/:body
│   ├── useMoves.ts             # useQuery → GET /moves
│   └── useAiChat.ts            # useMutation → POST /ai/ask (streaming)
├── types/
│   └── api.d.ts                # Types mirroir des schemas Pydantic
├── public/
│   └── sprites/                # Sprites statiques (montés via volume Docker)
├── next.config.ts
├── tailwind.config.ts
└── package.json
```

---

## Pages et fonctionnalités

### 1. `/pokedex` — Liste

- Grille responsive de `PokemonCard` (sprite + nom EN/FR + types)
- Filtres : Type, Génération, Recherche textuelle (EN ou FR, accents ignorés)
- Pagination infinie (IntersectionObserver) ou bouton "Charger plus"
- Skeleton loading pendant fetch
- URL params synchronisés (`?type=Feu&q=bulba`) pour partage de lien

### 2. `/pokedex/[id]` — Fiche Pokémon

Tabs : **Stats** | **Capacités** | **Évolutions** | **Fusions** | **IA**

**Tab Stats**
- Sprite officiel + sprite fusion exemples
- `StatBar` pour les 6 stats (HP, Atk, Def, SpA, SpD, Spe) — couleur selon valeur
- IF ID + National ID
- TypeBadge(s) avec flag `if_override` → tooltip "Modifié dans IF"
- Talent(s) avec flag `if_swapped` → tooltip "Talent modifié dans IF"

**Tab Capacités**
- Tableau groupé par méthode : Montée de niveau | CT | Reproduction | Donneur
- Colonne : Niveau | Nom EN/FR | Type | Catégorie | Puissance | Précision
- Source badge : `base` (Pokepedia) vs `infinite_fusion` (wiki IF)

**Tab Évolutions**
- Arbre graphique simple : A → B (condition) → C
- Badge "IF uniquement" si `if_override = true`
- Conditions : niveau, objet, échange, etc.

**Tab Fusions**
- Quick-link "Voir en tant que Head avec…" + searchbox body
- Quick-link "Voir en tant que Body avec…" + searchbox head

**Tab IA**
- Zone chat inline — `AiSuggestButton` avec contexte pré-rempli du Pokémon

### 3. `/fusion/[headId]/[bodyId]` — Résultat fusion

- Sprite `{headId}.{bodyId}.png` (servi depuis `/sprites/`)
- Stats calculées avec formule :
  - Physique (HP/Atk/Def/Spe) = `floor(Body×2/3 + Head×1/3)`
  - Spécial (SpA/SpD) = `floor(Head×2/3 + Body×1/3)`
- Types : type1 = Head, type2 = Body (ou override IF)
- Talents : Head talent caché + Body talent normal
- Bouton "Inverser head/body"
- Bouton "Demander à l'IA une stratégie pour cette fusion"

### 4. `/moves` — Capacités

- Tableau complet avec filtres Type + Catégorie + Recherche
- Colonnes : Nom EN | Nom FR | Type | Cat. | Puissance | Précision | PP
- Clic → drawer latéral avec description complète EN/FR + liste Pokémon qui apprennent

### 5. `/ai` — Assistant DeepSeek

- Chat libre
- Contexte système : "Tu es un expert Pokémon Infinite Fusion..."
- Suggestions rapides : "Meilleure fusion Dracaufeu ?", "Quelle équipe pour un run ?", etc.
- Historique session (Zustand, non persisté)
- Streaming tokens (SSE ou chunked response)

---

## Constantes couleurs des types

```ts
// lib/constants.ts
export const TYPE_COLORS: Record<string, string> = {
  Normal:   "#A8A878", Feu:      "#F08030", Eau:      "#6890F0",
  Électrik: "#F8D030", Plante:   "#78C850", Glace:    "#98D8D8",
  Combat:   "#C03028", Poison:   "#A040A0", Sol:      "#E0C068",
  Vol:      "#A890F0", Psy:      "#F85888", Insecte:  "#A8B820",
  Roche:    "#B8A038", Spectre:  "#705898", Dragon:   "#7038F8",
  Ténèbres: "#705848", Acier:    "#B8B8D0", Fée:      "#EE99AC",
  // IF-only (triple fusions)
  Feu_Eau:  "#CF6020", Psy_Fée:  "#DD88CC",
  // ... autres combinaisons IF
};
```

---

## API Calls — lib/api.ts

```ts
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Pokemon
export const getPokemonList  = (params) => fetch(`${BASE}/pokemon?${params}`);
export const getPokemon      = (id)     => fetch(`${BASE}/pokemon/${id}`);
export const searchPokemon   = (q)      => fetch(`${BASE}/pokemon/search?q=${q}`);

// Fusion (computed endpoint)
export const getFusion       = (h, b)   => fetch(`${BASE}/fusion/${h}/${b}`);

// Moves
export const getMoves        = ()       => fetch(`${BASE}/moves`);
export const getMove         = (id)     => fetch(`${BASE}/moves/${id}`);
export const getMovesByType  = (type)   => fetch(`${BASE}/moves/by-type/${type}`);

// Types
export const getTypes        = ()       => fetch(`${BASE}/types`);
export const getTypeAffinities = (atk, def) =>
  fetch(`${BASE}/types/affinities/by-name?attacking=${atk}&defending=${def}`);

// AI
export const askAi = (message, context) =>
  fetch(`${BASE}/ai/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, context }),
  });
```

---

## Endpoints Backend manquants à créer

Ces routes n'existent pas encore dans `backend/routes/` et sont nécessaires au frontend :

| Endpoint | Description |
|---|---|
| `GET /moves` | Liste toutes les capacités |
| `GET /moves/{id}` | Détail capacité |
| `GET /moves/search?q=` | Recherche accent-insensitive EN+FR |
| `GET /moves/by-type/{type}` | Capacités par type |
| `GET /abilities` | Liste tous les talents |
| `GET /abilities/{id}` | Détail talent |
| `GET /types` | Liste des 27 types IF |
| `GET /types/affinities` | Efficacités offensives/défensives |
| `GET /pokemon/{id}/moves` | Moveset complet d'un Pokémon |
| `GET /pokemon/{id}/evolutions` | Chaîne d'évolutions IF |
| `GET /fusion/{head_id}/{body_id}` | Stats/types/sprites calculés |
| `POST /ai/ask` | Requête DeepSeek (streaming) |

---

## Étapes d'implémentation

### Phase 1 — Setup (1 session)
- [ ] `npx create-next-app@latest frontend --ts --app --tailwind`
- [ ] Installer shadcn/ui : `npx shadcn@latest init`
- [ ] Installer : `@tanstack/react-query`, `zustand`, `framer-motion`
- [ ] Créer `lib/api.ts`, `lib/constants.ts`, `types/api.d.ts`
- [ ] Configurer `NEXT_PUBLIC_API_URL` dans `.env.local`

### Phase 2 — Composants de base (1 session)
- [ ] `TypeBadge` avec `TYPE_COLORS`
- [ ] `StatBar` couleur selon valeur (vert > 100, jaune > 60, rouge < 60)
- [ ] `PokemonCard` (sprite + nom + types)
- [ ] `SearchBar` avec debounce 300ms

### Phase 3 — Pages Pokédex (1-2 sessions)
- [ ] `/pokedex` avec filtres + pagination
- [ ] `/pokedex/[id]` avec 5 tabs

### Phase 4 — Fusion (1 session)
- [ ] `FusionSelector` double combobox
- [ ] `/fusion/[headId]/[bodyId]` avec calcul stats

### Phase 5 — Moves + Types (1 session)
- [ ] `/moves` tableau filtrable
- [ ] Type chart (heatmap efficacités)

### Phase 6 — IA (1 session)
- [ ] `/ai` chat DeepSeek avec streaming
- [ ] `AiSuggestButton` intégré dans fiche Pokémon

### Phase 7 — Polish (1 session)
- [ ] Dark mode (Tailwind `dark:`)
- [ ] Responsive mobile
- [ ] Loading skeletons
- [ ] Error boundaries

---

## Docker — Dockerfile.frontend

```dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

Ajout dans `docker-compose.yml` :
```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: ../docker/Dockerfile.frontend
  ports:
    - "3000:3000"
  environment:
    - NEXT_PUBLIC_API_URL=http://backend:8000
  depends_on:
    - backend
```

---

## Note sur les sprites

Les sprites sont stockés localement dans `data/sprites/` et montés en volume.  
Deux options :
1. **Volume Docker** → `next/image` avec `remotePatterns` ou serveur statique nginx
2. **API backend** → `GET /sprites/{head_id}/{body_id}` stream le fichier PNG

Recommandation : **nginx statique** sur port 8080 monté sur `data/sprites/` — plus simple et performant que faire passer les images par FastAPI.
