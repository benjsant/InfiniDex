# Architecture

Vue d'ensemble des couches du projet et de la façon dont elles communiquent.

## Schéma global

```mermaid
flowchart LR
    subgraph Sources
        A[PokeAPI]
        B[Wiki Infinite Fusion]
        C[Poképédia]
        D[PokeAPI sprites repo]
    end

    subgraph ETL["ETL (Python + uv)"]
        E[load_db.py<br/>orchestration]
        F[fix_*.py<br/>corrections canoniques]
    end

    subgraph DB[(PostgreSQL 16)]
        G[pokemon, move, type,<br/>ability, evolution…]
        H[fusion_sprite,<br/>triple_fusion]
        I[move_expert_move]
    end

    subgraph Backend["FastAPI"]
        J[routes/]
        K[services/]
        L[schemas/]
        IA[ai_service<br/>agent loop + SSE]
    end

    subgraph Frontend["Next.js 15 App Router"]
        M[pages /pokedex /fusion /ai…]
        N[proxy /api/* /sprites-cdn/*]
    end

    LLM[LLM externe<br/>DeepSeek / Ollama]
    WikiIF[Wiki IF<br/>MediaWiki API]
    Sprites[Sidecar nginx<br/>sprites PNG]

    A --> E
    B --> E
    C --> E
    D --> Sprites
    E --> DB
    F --> DB
    DB --> K
    K --> J
    J --> L
    L --> N
    IA --> LLM
    IA --> WikiIF
    IA --> DB
    J --> IA
    Sprites --> N
    N --> M
```

## Services Docker

Quatre services de run (`db`, `backend`, `sprites`, `frontend`) sur le réseau interne Docker, plus un service optionnel `docs` sous profil Compose. Seul le frontend est exposé publiquement en prod.

| Service    | Port interne | Port hôte (dev) | Rôle                                | Profil   |
| ---------- | ------------ | --------------- | ----------------------------------- | -------- |
| `db`       | 5432         | 55432           | PostgreSQL 16                       | défaut   |
| `backend`  | 8000         | 58000           | FastAPI                             | défaut   |
| `sprites`  | 80           | 58080           | nginx statique pour sprites PNG     | défaut   |
| `frontend` | 3000         | 53000           | Next.js (standalone)                | défaut   |
| `docs`     | 58100        | 58100           | MkDocs Material (cette doc)         | `docs`   |

Le service `docs` ne démarre **pas** avec `docker compose up` — il faut le profil explicite :

```bash
docker compose --profile docs up docs
```

Les ports hôte suivent une convention **préfixe 5** pour éviter les collisions avec d'autres projets locaux.

!!! tip "Override prod"
    `docker-compose.prod.yml` remet `ports: !reset []` sur db/backend/sprites — plus rien n'est exposé sauf le frontend. Le navigateur passe toujours par le proxy Next.js.

## Flux de requêtes

### En dev

```
Navigateur → http://localhost:53000/pokedex
           → Next.js SSR → fetch http://localhost:53000/api/pokemon/
           → Route handler Next.js (/app/api/[...path]/route.ts)
           → fetch http://backend:8000/pokemon/ (réseau Docker interne)
           → FastAPI → SQLAlchemy → Postgres
           ← JSON
```

### En prod

Identique, sauf que `http://backend:8000` n'est joignable que depuis le conteneur `frontend`. Le navigateur ne voit jamais l'URL réelle du backend, uniquement `/api/*` sur le domaine public.

### Flux IA (SSE)

```
Navigateur → POST /api/ai/ask  {"message": "...", "context": "..."}
           → proxy Next.js
           → FastAPI /ai/ask → stream_ai_response()
               ├─ itération 1 : LLM → tool_call get_pokemon
               │    yield ToolCallEvent {"type":"tool_call","name":"get_pokemon"}
               │    dispatch_tool() → DB query → résultat JSON
               ├─ itération 2 : LLM → réponse textuelle
               │    yield TokenEvent {"type":"token","chunk":"…"} × N
               └─ fin de stream
           → SSE data: {"type":"token","chunk":"..."}\n\n
           → AiChat.tsx accumule les chunks → affichage progressif
```

Le SSE stream émet deux types d'événements distincts :

- `{"type": "tool_call", "name": "get_pokemon"}` — affiché comme pastille ⚙ dans l'UI
- `{"type": "token", "chunk": "..."}` — accumulé dans la bulle de réponse

## Architecture IA agentique

L'assistant IA est un **agent tool-calling** — il ne génère pas de réponse directement mais invoque des outils structurés pour chercher l'information, puis synthétise.

### System prompt

Stocké dans [`backend/prompts/system.md`](https://github.com/benjsant/FusionDex-IA/blob/main/backend/prompts/system.md) — fichier Markdown chargé au démarrage via `pathlib`. Écrit en anglais (meilleure instruction-following), avec règle explicite de répondre en français. Mis à jour sans redéploiement (hot-reload au prochain démarrage du conteneur).

### Boucle agent (`ai_service.py`)

```
messages = [system, ...history, user]
for iteration in range(MAX_ITERATIONS=5):
    response = LLM(messages, tools=TOOL_SPECS)
    if response.tool_calls:
        yield ToolCallEvent pour chaque tool
        résultats = dispatch_tool(tool, args)
        messages.append(tool_results)
    else:
        yield TokenEvent(response.content ou FAILURE_MESSAGE)
        return
yield TokenEvent(FAILURE_MESSAGE)  # circuit breaker
```

**Fail-closed** : si MAX_ITERATIONS est atteint sans réponse, ou si la réponse est vide → `"Je n'ai pas trouvé cette information."` — jamais d'invention.

### Outils disponibles

| Tool | Source | Description |
|------|--------|-------------|
| `get_pokemon` | DB | Fiche complète (stats, types, talents) par nom ou ID |
| `get_fusion` | DB | Stats, types et moveset d'une fusion head/body |
| `search_move` | DB | Recherche de capacité par nom (EN ou FR) |
| `get_item` | DB | Fiche item par nom |
| `get_move_tutors` | DB | NPCs enseignant une capacité + prix |
| `search_wiki` | Wiki IF (HTTP) | Résumé de page wiki avec cache TTL 10 min |

### Cache et performances

- **`StaticCacheMiddleware`** : ajoute `Cache-Control: public, max-age=3600` sur tous les `GET 200` sauf `/ai/*` et `/health` — les clients et CDN peuvent mettre en cache les données statiques.
- **Wiki TTL cache** : dict in-process `{query → (timestamp, result)}`, TTL 600s, clé normalisée. Évite de re-fetcher le wiki sur des questions similaires.
- **`staleTime: Infinity`** côté React Query : les données Pokémon ne changent pas entre deux déploiements — aucun refetch en arrière-plan.

### Provider pluggable

Interface `LLMProvider` abstraite — sélection runtime :

1. `DEEPSEEK_API_KEY` défini → DeepSeek (API compatible OpenAI)
2. `OLLAMA_URL` défini → Ollama local
3. Aucun → `503` avec instructions de configuration

## Pourquoi ce découpage ?

- **ETL séparé du backend** : le pipeline de données tourne en one-shot (ou via Prefect plus tard), indépendamment du serveur web. Pas de couplage.
- **Sprites servis par nginx plutôt que FastAPI** : 166k fichiers PNG statiques, nginx est 10× plus efficace que Python pour ça.
- **Proxy Next.js plutôt qu'appels directs au backend** : masque les URLs internes, évite CORS côté navigateur, permet de changer la cible backend sans rebuild frontend (env runtime).
- **`INTEGER[]` PostgreSQL pour Move Experts** : contraintes multi-valeurs (required_pokemon_ids, etc.) naturellement représentées sans table de jonction supplémentaire.
- **System prompt externe** : `prompts/system.md` versionné séparément du code, éditable sans toucher à Python.

## Références

- [backend/main.py](https://github.com/benjsant/FusionDex-IA/blob/main/backend/main.py) — wiring FastAPI + CORS + StaticCacheMiddleware
- [backend/services/ai_service.py](https://github.com/benjsant/FusionDex-IA/blob/main/backend/services/ai_service.py) — boucle agent + SSE
- [backend/services/tools/](https://github.com/benjsant/FusionDex-IA/blob/main/backend/services/tools/) — db_tools, wiki_tool, dispatch
- [backend/prompts/system.md](https://github.com/benjsant/FusionDex-IA/blob/main/backend/prompts/system.md) — system prompt
- [docker-compose.yml](https://github.com/benjsant/FusionDex-IA/blob/main/docker-compose.yml) — services dev
- [docker-compose.prod.yml](https://github.com/benjsant/FusionDex-IA/blob/main/docker-compose.prod.yml) — override prod
- [frontend/app/api/[...path]/route.ts](https://github.com/benjsant/FusionDex-IA/blob/main/frontend/app/api/%5B...path%5D/route.ts) — proxy catch-all
- [Référence routes](reference/routes.md) — endpoints FastAPI auto-documentés.
