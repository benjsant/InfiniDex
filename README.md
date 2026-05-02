# FusionDex-IA

Pokédex complet pour [Pokémon Infinite Fusion](https://infinitefusion.fandom.com/) — 572 Pokémon (501 base + 71 formes), ~176 000 fusions, movepools, types, triple-fusions, Move Experts, maîtres des capacités, et un assistant IA agentique spécialisé.

---

## Stack et état

| Couche     | Stack                                                | État          |
| ---------- | ---------------------------------------------------- | ------------- |
| ETL        | Python 3.12 + `uv` + MediaWiki + PokeAPI             | stable        |
| Base       | PostgreSQL 16 (relationnelle + `INTEGER[]`)          | stable        |
| Backend    | FastAPI + SQLAlchemy 2 + Pydantic (41 endpoints)     | stable        |
| Frontend   | Next.js 15 App Router + TypeScript                   | stable        |
| IA         | Agent tool-calling DeepSeek/Ollama — 7 outils        | en cours      |
| Infra      | Docker Compose (dev + prod), proxy Next.js           | stable        |

---

## Lancer en local

Pré-requis : Docker + Docker Compose.

```bash
# Cloner le dépôt
git clone https://github.com/benjsant/FusionDex-IA.git
cd FusionDex-IA

# Copier et remplir les variables d'environnement
cp .env.example .env
# Éditer .env — renseigner DEEPSEEK_API_KEY si vous voulez l'IA

# Démarrer tous les services (db, backend, sprites, frontend)
docker compose up -d

# Frontend : http://localhost:53000
# API Swagger : http://localhost:58000/docs
```

Pour la documentation MkDocs :

```bash
docker compose --profile docs up docs
# Docs : http://localhost:58100
```

---

## Fonctionnalités

| Page                   | Description                                                                   |
| ---------------------- | ----------------------------------------------------------------------------- |
| `/pokedex`             | Liste paginée (40/page) + recherche + filtre par type                         |
| `/pokedex/[id]`        | Fiche complète : stats, capacités, évolutions, faiblesses, fusion             |
| `/fusion`              | Sélecteur head/body avec filtre Kanto/Hoenn/Tous + pré-sélection via URL      |
| `/fusion/[h]/[b]`      | Résultat : sprites, stats, moveset, Move Expert moves, assistant IA           |
| `/moves`               | Liste référentielle des 676 capacités + recherche + filtre par type           |
| `/moves/tutors`        | Maîtres des capacités (41 tuteurs classiques) + Move Experts par île          |
| `/types`               | Grille des 27 types (18 standard + 9 triple-fusion) + matchups                |
| `/abilities`           | Liste des 178 talents + recherche                                             |
| `/triple-fusions`      | 23 fusions triples disponibles dans le jeu                                    |
| `/ai`                  | Chat IA plein écran — agent agentique avec transparence des outils invoqués   |

---

## Données

- 572 Pokémon · 676 moves · 178 abilities · 27 types · 70 items
- 166 090 fusion_sprites · 7 081 créateurs · 23 triple_fusions
- 40 067 pokemon_move · 1 634 pokemon_location (dont 55 gift, 25 trade)
- 121 TMs · 65 move_expert_moves · 41 move_tutors

---

## Architecture rapide

```
ETL (Python) → PostgreSQL 16 → FastAPI → proxy Next.js → navigateur
                                   ↑
                             agent IA (tool-calling)
                             DB + Wiki IF + web
```

Documentation complète dans [`docs/`](docs/) (MkDocs Material) :

- [Architecture](docs/architecture.md) — flux de requêtes, services Docker, boucle agent IA
- [API backend](docs/api.md) — référence des 41 endpoints
- [Base de données](docs/database.md) — schéma, tables, volumes de données
- [Frontend](docs/frontend.md) — pages, composants, hooks, design system
- [Roadmap](ROADMAP.md) — état d'avancement et prochaines étapes
