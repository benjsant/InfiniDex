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

Le service `docs` ne démarre **pas** avec `docker compose up` - il faut le profil explicite :

```bash
docker compose --profile docs up docs
```

Les ports hôte suivent une convention **préfixe 5** pour éviter les collisions avec d'autres projets locaux.

!!! tip "Override prod"
    `docker-compose.prod.yml` remet `ports: !reset []` sur db/backend/sprites - plus rien n'est exposé sauf le frontend. Le navigateur passe toujours par le proxy Next.js.

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

### Flux requête Pokémon (exemple `/pokedex/[id]`)

```mermaid
sequenceDiagram
    autonumber
    participant Br as Navigateur
    participant Nx as Next.js SSR
    participant Px as Proxy /api/*
    participant FA as FastAPI
    participant PG as PostgreSQL

    Br  ->>  Nx : GET /pokedex/25
    Nx  ->>  Px : fetch /api/pokemon/25
    Px  ->>  FA : GET /pokemon/25 (réseau Docker)
    FA  ->>  PG : SELECT pokemon + types + abilities\n+ evolutions + locations
    PG  -->> FA : JSON rows
    FA  -->> Px : PokemonDetail JSON
    Px  -->> Nx : JSON
    Nx  -->> Br : HTML (SSR hydraté)

    note over Br,Nx: React Query staleTime=Infinity\n→ aucun refetch si déjà en cache
```

### Flux résolution sprite de fusion

```mermaid
flowchart TD
    REQ([Fusion head_id · body_id])

    REQ --> CHK{Sprite custom\ndans nginx ?}
    CHK -->|Oui| PNG["/sprites/{head}.{body}.png\nnginx sidecar - direct"]
    CHK -->|Non| FB[FusionSprite fallback]

    FB --> MAP[usePokemonIdMap\nIF id → national_id]
    MAP --> PA1[PokeAPI sprite head\n/pokemon/{nationalHead}.png]
    MAP --> PA2[PokeAPI sprite body\n/pokemon/{nationalBody}.png]
    PA1 & PA2 --> COMP[Affichage côte à côte\nhead 55% · body 55%]

    style PNG  fill:#1e3b2f,color:#6ee7b7
    style COMP fill:#3b2f1e,color:#fcd34d
```

!!! note "IF id ≠ national dex id"
    Pour Gen 1–2 les deux IDs coïncident (1–251). Au-delà, IF utilise sa propre numérotation - ex. Arceus est `#315` en IF mais `#493` au national dex. `usePokemonIdMap` charge une fois la liste complète des 572 Pokémon et construit la map en mémoire (React Query `staleTime: Infinity`).

### Flux IA (SSE)

```mermaid
sequenceDiagram
    autonumber
    participant B  as Navigateur<br/>(AiChat.tsx)
    participant N  as Next.js<br/>proxy /api/*
    participant F  as FastAPI<br/>/ai/ask
    participant L  as LLM<br/>(DeepSeek / Ollama)
    participant T  as Tools<br/>(DB · Wiki · DDG)

    B  ->>  N : POST /api/ai/ask<br/>{message, context, history}
    N  ->>  F : POST /ai/ask (réseau Docker interne)
    F  -->> B : HTTP 200 + headers SSE<br/>Content-Type: text/event-stream

    note over F,L: Itération 1 - l'agent appelle un outil
    F  ->>  L : chat.completions.create(stream=True)<br/>[system, history, user]
    L  -->> F : delta tool_call {name, arguments}
    F  -->> B : data: {"type":"tool_call","name":"get_pokemon"}
    F  ->>  T : dispatch_tool(name, args)
    T  -->> F : {found: true, ...résultat JSON}
    F  ->>  L : messages += [tool_result]

    note over F,L: Itération 2 - l'agent génère la réponse
    F  ->>  L : chat.completions.create(stream=True)<br/>[system, history, user, tool_result]
    loop streaming tokens
        L  -->> F : delta content chunk
        F  -->> B : data: {"type":"token","chunk":"..."}
    end
    L  -->> F : usage {total_tokens: N}

    note over F,B: Fin de stream - attribution des sources
    F  -->> B : data: {"type":"source","sources":["db"],"web_urls":[]}
    F  -->> B : data: {"type":"usage","total_tokens":412}

    note over B: AiChat.tsx
    note over B: • tool_call → pastille ⚙ avant la bulle<br/>• token → chunk accumulé dans la bulle<br/>• source → badges db/wiki/web sous la bulle<br/>  (web = cliquable, ouvre les URLs consultées)<br/>• usage → compteur tokens sous la bulle
```

**Événements SSE émis :**

| Type | Payload | Affiché comme |
|------|---------|---------------|
| `tool_call` | `{name}` | Pastille ⚙ avant la réponse |
| `token` | `{chunk}` | Texte accumulé dans la bulle (streaming) |
| `source` | `{sources, web_urls}` | Badges db / wiki / web sous la bulle - web cliquable |
| `usage` | `{total_tokens}` | Compteur tokens sous la bulle |
| `error` | `{message}` | Message d'erreur inline, bulle supprimée |

## Architecture IA agentique

L'assistant IA est un **agent tool-calling** - il ne génère pas de réponse directement mais invoque des outils structurés pour chercher l'information, puis synthétise.

### System prompt

Stocké dans [`backend/prompts/system.md`](https://github.com/benjsant/InfiniDex/blob/main/backend/prompts/system.md) - fichier Markdown chargé au démarrage via `pathlib`. Écrit en anglais (meilleure instruction-following), avec règle explicite de répondre en français. Mis à jour sans redéploiement (hot-reload au prochain démarrage du conteneur).

### Boucle agent (`ai_service.py`)

```
messages = [system, ...history, user]
for iteration in range(MAX_ITERATIONS=8):
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

**Fail-closed** : si MAX_ITERATIONS est atteint sans réponse, ou si la réponse est vide → `"Je n'ai pas trouvé cette information."` - jamais d'invention.

### Outils disponibles

| Tool | Source | Description |
|------|--------|-------------|
| `get_pokemon` | DB | Fiche complète (stats, types, talents) par nom ou ID |
| `get_fusion` | DB | Stats, types et moveset d'une fusion head/body |
| `get_triple_fusion` | DB | Données d'une triple fusion (Zapmolcuno, Enraicune…) |
| `search_move` | DB | Recherche de capacité par nom (EN ou FR) |
| `get_item` | DB | Fiche item par nom |
| `get_move_tutors` | DB | NPCs enseignant une capacité + prix |
| `search_pokemon_locations` | DB | Cherche les Pokémon par condition/méthode dans `pokemon_location` |
| `search_wiki` | Wiki IF (HTTP) | Résumé de page wiki avec cache TTL 10 min - fetch page complète si intro < 300 caractères |
| `search_web` | DuckDuckGo (HTTP) | Fallback web en dernier recours, cache TTL 5 min, max 1 appel par tour |

### Cascade de retrieval

L'agent ne suit pas un script fixe - c'est le LLM qui décide quels outils appeler. Le system prompt le guide vers cette priorité :

```mermaid
flowchart TD
    Q([Question utilisateur]) --> LLM1[LLM - itération 1]

    LLM1 -->|tool_call DB| DB["Outils DB\nget_pokemon · get_fusion\nsearch_move · get_item\nget_move_tutors\nsearch_pokemon_locations"]
    DB -->|found: true| RESP([Réponse synthétisée])
    DB -->|found: false| LLM2[LLM - itération 2]

    LLM2 -->|tool_call wiki| WIKI["search_wiki\n(MediaWiki API IF)\ncache TTL 10 min"]
    WIKI -->|found: true| RESP
    WIKI -->|found: false| LLM3[LLM - itération 3]

    LLM3 -->|tool_call web| WEB["search_web\n(DuckDuckGo)\ncache TTL 5 min\nmax 1 500 chars"]
    WEB -->|found: true| RESP
    WEB -->|found: false| FAIL([Fail-closed\n&#34;Je n'ai pas trouvé cette information.&#34;])

    LLM1 -->|no tool_call| RESP
    LLM2 -->|no tool_call| RESP
    LLM3 -->|no tool_call| RESP

    CIRC["⚡ Circuit breaker\nmax 8 itérations"] -.->|stop| FAIL

    style DB   fill:#1e3a5f,color:#93c5fd
    style WIKI fill:#3b2f1e,color:#fcd34d
    style WEB  fill:#1e3b2f,color:#6ee7b7
    style FAIL fill:#3b1e1e,color:#fca5a5
    style CIRC fill:#2d1e3b,color:#c4b5fd
```

Chaque résultat d'outil est injecté dans le contexte avant l'itération suivante. Le LLM peut enchaîner plusieurs outils DB dans une même itération (ex. `get_pokemon` + `get_fusion`).

### Cache et performances

- **`StaticCacheMiddleware`** : ajoute `Cache-Control: public, max-age=3600` sur tous les `GET 200` sauf `/ai/*` et `/health` - les clients et CDN peuvent mettre en cache les données statiques.
- **Wiki TTL cache** : dict in-process `{query → (timestamp, result)}`, TTL 600s, clé normalisée. Évite de re-fetcher le wiki sur des questions similaires.
- **`staleTime: Infinity`** côté React Query : les données Pokémon ne changent pas entre deux déploiements - aucun refetch en arrière-plan.

### Provider pluggable

Interface `LLMProvider` abstraite - sélection runtime :

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

- [backend/main.py](https://github.com/benjsant/InfiniDex/blob/main/backend/main.py) - wiring FastAPI + CORS + StaticCacheMiddleware
- [backend/services/ai_service.py](https://github.com/benjsant/InfiniDex/blob/main/backend/services/ai_service.py) - boucle agent + SSE
- [backend/services/tools/](https://github.com/benjsant/InfiniDex/blob/main/backend/services/tools/) - db_tools, wiki_tool, dispatch
- [backend/prompts/system.md](https://github.com/benjsant/InfiniDex/blob/main/backend/prompts/system.md) - system prompt
- [docker-compose.yml](https://github.com/benjsant/InfiniDex/blob/main/docker-compose.yml) - services dev
- [docker-compose.prod.yml](https://github.com/benjsant/InfiniDex/blob/main/docker-compose.prod.yml) - override prod
- [frontend/app/api/[...path]/route.ts](https://github.com/benjsant/InfiniDex/blob/main/frontend/app/api/%5B...path%5D/route.ts) - proxy catch-all
- [Référence routes](reference/routes.md) - endpoints FastAPI auto-documentés.
