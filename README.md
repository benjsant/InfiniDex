# InfiniDex

Pokédex complet pour [Pokémon Infinite Fusion](https://infinitefusion.fandom.com/) — 572 Pokémon (501 Kanto + 71 Hoenn), 168 000+ fusions calculées, movepools, types, triple-fusions, Move Experts, maîtres des capacités, galerie des créateurs de sprites, et un **assistant IA agentique** à 9 outils.

📖 **[Documentation complète →](https://benjsant.github.io/InfiniDex/)**

---

## Stack

| Couche     | Stack                                                       | État      |
| ---------- | ----------------------------------------------------------- | --------- |
| ETL        | Python 3.12 + `uv` + MediaWiki API + PokeAPI + Prefect 3    | ✅ stable |
| Base       | PostgreSQL 16 (relationnelle + `INTEGER[]`)                 | ✅ stable |
| Backend    | FastAPI + SQLAlchemy 2 + Pydantic — 54 endpoints            | ✅ stable |
| Frontend   | Next.js 15 App Router + TypeScript + PWA — 23 pages         | ✅ stable |
| IA         | Agent tool-calling — DeepSeek / OpenRouter / Ollama         | ✅ stable |
| Infra      | Docker Compose (5 profils) + 4 lanes CI GitHub Actions      | ✅ stable |

---

## Notable engineering choices

Choix d'archi que je voulais documenter pour les recruteurs IA / data eng qui ouvrent ce repo :

- **Agent LLM multi-provider, pas de LangChain.** Abstraction `select_provider()` qui choisit à runtime entre DeepSeek, OpenRouter et Ollama. Pas de vendor lock-in, et le code est inspectable de bout en bout — du system prompt jusqu'au parsing des `tool_calls`.
- **Cascade de sources fail-closed.** L'agent priorise toujours la DB structurée (9 outils SQL/HTTP), puis le wiki Infinite Fusion, puis le web en dernier recours. Si tout échoue → réponse explicite *"je n'ai pas trouvé"*, jamais d'hallucination silencieuse.
- **PII redactor en pré-traitement.** Tous les messages partant vers le LLM passent par [`pii_redactor.py`](backend/services/pii_redactor.py) qui supprime emails, numéros, Discord tags, etc.
- **SSE streaming + transparence agent.** Le frontend reçoit chaque `tool_call` en temps réel via Server-Sent Events. `GET /ai/prompt` expose le system prompt complet pour l'audit utilisateur.
- **ETL Prefect 3 self-hosté.** Deux watchers daily (Pokédex + sprites custom) qui alertent Discord quand le wiki Infinite Fusion ou le repo `pif-downloadables` change. Drift snapshot dans `audit_db.py` (3 niveaux : compile + tests unit + diff vs run précédent).
- **Cache-aware backend.** `_pokemon_cache` warm au startup (572 entrées) + `_fusion_cache` borné à 4096. ~80 % des appels API ne touchent jamais la DB.
- **Discipline d'audit.** 14 rounds d'audit + 4 PR de dedup (~333 LOC nettes supprimées, 9 modules partagés extraits). CI à 4 lanes path-filtered.

---

## Lancer en local

Pré-requis : **Docker + Docker Compose**.

```bash
git clone https://github.com/benjsant/InfiniDex.git
cd InfiniDex

cp .env.example .env
# Optionnel : renseigner DEEPSEEK_API_KEY ou OPENROUTER_API_KEY pour l'IA
# Optionnel : renseigner DISCORD_WEBHOOK_URL pour les alertes watcher

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

### Watchers Prefect (optionnel)

Deux flows quotidiens qui détectent les ajouts upstream et postent sur Discord :

```bash
docker compose --profile prefect up -d
docker compose --profile prefect exec prefect-worker \
  prefect work-pool create infinidex-pool --type process --skip-if-exists
docker compose --profile prefect exec prefect-worker \
  prefect --no-prompt deploy --all
```

UI Prefect : http://localhost:54200 — cron `06:00 Paris` (pokedex) + `07:00 Paris` (sprites).

---

## Fonctionnalités

| Page | Description |
| ---- | ----------- |
| `/` | Accueil |
| `/pokedex` | Liste paginée (40/page) + recherche + filtre par type + filtre Kanto/Hoenn |
| `/pokedex/[id]` | Fiche complète : stats, capacités, évolutions, faiblesses, onglet Fusion |
| `/pokedex/favorites` | Pokémon favoris (stockés localStorage) |
| `/fusion` | Sélecteur head/body + filtre Kanto/Hoenn/Tous + pré-sélection via URL |
| `/fusion/[h]/[b]` | Sprites custom + normal/inversé, stats fusionnées, moveset, Move Expert moves |
| `/fusion/[headId]` | Toutes les fusions d'un Pokémon en tête |
| `/fusion/body/[bodyId]` | Toutes les fusions d'un Pokémon en corps |
| `/fusion/compare` | Comparateur 2 fusions côte à côte |
| `/fusion/history` | Historique des fusions visitées |
| `/fusion/random` | Fusion aléatoire |
| `/fusion/top` | Top 50 fusions par BST |
| `/moves` | Table des 676 capacités + recherche + filtre type + filtre catégorie |
| `/moves/[id]` | Fiche capacité : type, puissance, précision, TM, tuteurs, description EN/FR |
| `/moves/tutors` | 41 tuteurs classiques groupés par lieu + Move Experts par île |
| `/types` | Grille des 27 types (18 standard + 9 triple-fusion) avec matchups complets |
| `/abilities` | 178 talents + recherche |
| `/abilities/[id]` | Fiche talent : description EN/FR |
| `/items` | Objets du jeu (fusion / evolution / valuable) avec lieux d'obtention |
| `/triple-fusions` | 23 fusions triples — sprites, composants, stats, faiblesses |
| `/creators` | Galerie des 7 126 créateurs de sprites — recherche + modal sprites |
| `/creators/[id]` | Fiche créateur — tous ses sprites |
| `/ai` | Chat IA streaming — agent à 9 outils avec transparence des appels en temps réel |
| `/about` | À propos du projet |

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
  ├─ PII redactor (avant envoi au LLM)
  │
  ├─ get_pokemon              → stats, types, talents d'un Pokémon
  ├─ get_fusion               → stats et moveset d'une fusion head/body
  ├─ get_triple_fusion        → infos sur les 23 fusions triples
  ├─ search_move              → détail d'une capacité (TM, lieux, prix)
  ├─ get_item                 → infos sur un objet
  ├─ get_move_tutors          → tuteurs qui enseignent une capacité + prix
  ├─ search_pokemon_locations → où trouver un Pokémon (gift, trade, légendaires…)
  ├─ search_wiki              → wiki Infinite Fusion (mécanique, quête, lore)
  └─ search_web               → DuckDuckGo (dernier recours)
       │
       └─ fail-closed : "Je n'ai pas trouvé cette information."
```

Réponses streamées via SSE. Chaque appel d'outil est affiché en temps réel dans l'interface.

---

## Architecture

```
ETL (Python/uv + Prefect)
  └── PostgreSQL 16
        └── FastAPI (SQLAlchemy 2 + cache mémoire)
              └── proxy Next.js 15  ←→  navigateur
                    └── /ai/ask  →  agent tool-calling (DeepSeek / OpenRouter / Ollama)
```

Voir la [documentation complète](https://benjsant.github.io/InfiniDex/) pour les diagrammes détaillés, la référence API et le guide de développement.

---

## CI

| Workflow | Déclencheur | Contenu |
|----------|-------------|---------|
| `backend-ci` | Push/PR sur `backend/` | Import check + tests DB-free + pytest contre PostgreSQL réel |
| `frontend-ci` | Push/PR sur `frontend/` | TypeScript typecheck + `next build` |
| `etl-ci` | Push/PR sur `etl/` | Compile gate (`compileall`) + tests parsers wiki |
| `docs` | Push sur `main` (docs/) | Build MkDocs → déploiement GitHub Pages |

Les 4 lanes sont **path-filtered** : un PR qui ne touche que le backend ne déclenche que `backend-ci`.

---

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md) — setup local, conventions de commits, checklist PR.

## Licence

[MIT](LICENSE)
