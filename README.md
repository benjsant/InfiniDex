# FusionDex-IA

Pokédex complet pour [Pokémon Infinite Fusion](https://infinitefusion.fandom.com/) — 572 Pokémon (501 Kanto + 71 Hoenn), 168 000+ fusions calculées, movepools, types, triple-fusions, Move Experts, maîtres des capacités, galerie des créateurs de sprites, et un **assistant IA agentique** à 9 outils.

📖 **[Documentation complète →](https://benjsant.github.io/FusionDex-IA/)**

---

## Stack

| Couche     | Stack                                                    | État      |
| ---------- | -------------------------------------------------------- | --------- |
| ETL        | Python 3.12 + `uv` + MediaWiki API + PokeAPI             | ✅ stable |
| Base       | PostgreSQL 16 (relationnelle + `INTEGER[]`)              | ✅ stable |
| Backend    | FastAPI + SQLAlchemy 2 + Pydantic — 48 endpoints         | ✅ stable |
| Frontend   | Next.js 15 App Router + TypeScript — 14 pages            | ✅ stable |
| IA         | Agent tool-calling DeepSeek / OpenRouter / Ollama local  | ✅ stable |
| Infra      | Docker Compose (dev + prod), proxy Next.js, CI GitHub    | ✅ stable |

---

## Lancer en local

Pré-requis : **Docker + Docker Compose**.

```bash
git clone https://github.com/benjsant/FusionDex-IA.git
cd FusionDex-IA

cp .env.example .env
# Optionnel : renseigner DEEPSEEK_API_KEY ou OPENROUTER_API_KEY pour l'IA

docker compose up -d
```

| Service | URL locale |
|---------|-----------|
| Frontend | http://localhost:53000 |
| API + Swagger | http://localhost:58000/docs |
| Sprites (debug) | http://localhost:58080/sprites/ |

> **Premier démarrage (~15 min).** Le conteneur `etl` se lance automatiquement et peuple la base : 572 Pokémon, 676 capacités, 168 000+ sprites. Le backend attend la fin de l'ETL avant de démarrer.

### Assistant IA

Trois providers supportés, sélectionnés automatiquement à runtime :

| Provider | Variable | Notes |
|----------|----------|-------|
| **DeepSeek** | `DEEPSEEK_API_KEY` | Priorité 1 — qualité maximale |
| **OpenRouter** | `OPENROUTER_API_KEY` | Priorité 2 — tier gratuit disponible |
| **Ollama local** | `OLLAMA_URL` | Priorité 3 — sans clé, `docker compose --profile ollama up` |

Sans provider → `POST /ai/ask` retourne `503` avec les instructions de configuration.

---

## Fonctionnalités

| Page | Description |
| ---- | ----------- |
| `/` | Accueil |
| `/pokedex` | Liste paginée (40/page) + recherche + filtre par type + filtre Kanto/Hoenn |
| `/pokedex/[id]` | Fiche complète : stats, capacités, évolutions, faiblesses, onglet Fusion |
| `/fusion` | Sélecteur head/body + filtre Kanto/Hoenn/Tous + pré-sélection via URL |
| `/fusion/[h]/[b]` | Sprites custom + normal/inversé, stats fusionnées, moveset, Move Expert moves |
| `/moves` | Table des 676 capacités + recherche + filtre type + filtre catégorie |
| `/moves/[id]` | Fiche capacité : type, puissance, précision, TM, tuteurs, description EN/FR |
| `/moves/tutors` | 41 tuteurs classiques groupés par lieu + Move Experts par île |
| `/types` | Grille des 26 types (18 standard + 8 triple-fusion) avec matchups complets |
| `/abilities` | 178 talents + recherche |
| `/abilities/[id]` | Fiche talent : description EN/FR |
| `/triple-fusions` | 23 fusions triples — sprites, composants, stats, faiblesses |
| `/creators` | Galerie des 7 126 créateurs de sprites — recherche + modal sprites |
| `/ai` | Chat IA streaming — agent à 9 outils avec transparence des appels en temps réel |

---

## Données

```
572 Pokémon · 676 capacités · 178 talents · 26 types · 70 objets
168 154 fusion_sprites · 7 126 créateurs · 23 triple_fusions
45 063 pokemon_move · 1 634 pokemon_location (55 gift · 25 trade)
121 TMs · 115 tm_locations · 65 move_expert_moves · 41 move_tutors
```

---

## Agent IA — cascade à 9 outils

```
Question utilisateur
  │
  ├─ get_pokemon            → stats, types, talents d'un Pokémon
  ├─ get_fusion             → stats et moveset d'une fusion head/body
  ├─ get_triple_fusion      → infos sur les 23 fusions triples
  ├─ search_move            → détail d'une capacité (TM, lieux, prix)
  ├─ get_item               → infos sur un objet
  ├─ get_move_tutors        → tuteurs qui enseignent une capacité + prix
  ├─ search_pokemon_locations → où trouver un Pokémon (gift, trade, légendaires…)
  ├─ search_wiki            → wiki Infinite Fusion (mécanique, quête, lore)
  └─ search_web             → DuckDuckGo (dernier recours)
       │
       └─ fail-closed : "Je n'ai pas trouvé cette information."
       │
       └─ PII redactor (avant envoi au LLM)
```

Réponses streamées via SSE. Chaque appel d'outil est affiché en temps réel dans l'interface.

---

## Architecture

```
ETL (Python/uv)
  └── PostgreSQL 16
        └── FastAPI (SQLAlchemy 2)
              └── proxy Next.js 15  ←→  navigateur
                    └── /ai/ask  →  agent tool-calling (DeepSeek / OpenRouter / Ollama)
```

Voir la [documentation complète](https://benjsant.github.io/FusionDex-IA/) pour les diagrammes détaillés, la référence API et le guide de développement.

---

## CI

| Workflow | Déclencheur | Contenu |
|----------|-------------|---------|
| `backend-ci` | Push/PR sur `backend/` | Import check + tests DB-free + 148 tests pytest contre PostgreSQL réel |
| `docs` | Push sur `main` (docs/) | Build MkDocs → déploiement GitHub Pages |

---

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md) — setup local, conventions de commits, checklist PR.

## Licence

[MIT](LICENSE)
