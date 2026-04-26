# Développement

Guide pour installer, lancer et contribuer au projet.

## Prérequis

- **Docker** + Docker Compose v2
- **Node.js** ≥ 20 (pour le dev frontend hors Docker)
- **Python** ≥ 3.12 + [`uv`](https://github.com/astral-sh/uv) (pour l'ETL et la doc)

## Premier lancement

```bash
git clone <repo-url>
cd FusionDex-IA
cp .env.example .env               # ajuste POSTGRES_PASSWORD si besoin
docker compose up -d               # db + backend + sprites + frontend
```

Services accessibles :

- Frontend : [http://localhost:53000](http://localhost:53000)
- Backend / Swagger : [http://localhost:58000/docs](http://localhost:58000/docs)
- Sprites (direct, debug) : [http://localhost:58080/sprites/](http://localhost:58080/sprites/)
- Postgres : `localhost:55432` (user/db dans `.env`)

!!! tip "Base vide au premier démarrage"
    Le schéma se crée automatiquement via `docker/init_postgres.sql`, mais **les données ne sont pas incluses**. Lance le pipeline ETL pour peupler la base (voir plus bas).

## Peupler la base

```bash
cd etl
uv sync
uv run python -m etl.scripts.load_db
```

Durée : ~5–15 min selon ton réseau (beaucoup de fetch MediaWiki + PokeAPI).

## Dev sans Docker

### Backend

```bash
cd backend
uv sync
uv run uvicorn backend.main:app --reload --port 58000
```

### Frontend

```bash
cd frontend
npm install
npm run dev       # http://localhost:3000
```

En dev hors Docker, le proxy `/api/*` cible `BACKEND_INTERNAL_URL=http://localhost:58000` (cf. `frontend/.env.local.example`).

### Documentation

Voie principale — Docker, cohérent avec le reste du projet :

```bash
docker compose --profile docs up docs     # http://localhost:58100
```

Le service est sous profil `docs` → il ne démarre **pas** avec un simple `docker compose up`. Les fichiers `docs/`, `mkdocs.yml`, `pyproject.toml`, `uv.lock` sont montés en volume, donc le hot-reload fonctionne dès qu'on édite une page.

Premier lancement : `--build` pour construire l'image.

```bash
docker compose --profile docs up --build docs
```

Fallback host (sans Docker) :

```bash
uv sync --group docs
uv run mkdocs serve     # http://127.0.0.1:58100
```

## Configuration

### Ports (convention préfixe 5)

Les ports hôte sont tous configurables via `.env` pour éviter les collisions avec d'autres projets locaux.

```dotenv
FUSIONDEX_FRONTEND_PORT=53000
FUSIONDEX_BACKEND_PORT=58000
FUSIONDEX_SPRITES_PORT=58080
FUSIONDEX_DB_PORT=55432
```

Le serveur MkDocs (dev-tooling) est fixé à `58100` dans `mkdocs.yml`.

### CORS

```dotenv
CORS_ALLOWED_ORIGINS=http://localhost:53000,http://localhost:58000
```

En prod, lister uniquement le domaine public.

### Assistant IA (DeepSeek ou Ollama local)

L'endpoint `POST /ai/ask` est un agent tool-calling (cf. [API](api.md#ia-agentique-deepseek-ou-ollama)). Il sélectionne automatiquement un provider à runtime :

1. **DeepSeek** si `DEEPSEEK_API_KEY` est défini (priorité, qualité maximale)
2. **Ollama local** si `OLLAMA_URL` est défini
3. Sinon → `503` avec instructions de setup retournées en JSON

#### Option 1 — DeepSeek (cloud)

```dotenv
DEEPSEEK_API_KEY=sk-...
```

1. Créer un compte sur [platform.deepseek.com](https://platform.deepseek.com/)
2. Générer une clé API
3. Décommenter et coller dans `.env`
4. `docker compose restart backend` (clé lue à runtime, pas de rebuild)

#### Option 2 — Ollama local (autonome, sans clé)

```bash
docker compose --profile ollama up -d ollama
```

Puis dans `.env` :

```dotenv
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:3b   # défaut, ~2 GB téléchargés au premier boot
```

`docker compose restart backend`.

**Modèles recommandés** (override via `OLLAMA_MODEL`) :

| Modèle | Taille Q4 | RAM | Cible |
|--------|-----------|-----|-------|
| `qwen2.5:3b` (défaut) | ~2 GB | 4 GB | CPU only, laptop |
| `qwen2.5:7b` | ~4.5 GB | 6 GB | GPU 8 GB / Apple Silicon |

!!! note "Qualité comparée"
    Ollama local est moins fiable que DeepSeek sur le tool calling : 5-15 % d'arguments malformés contre <1 %, latence 5-30 s sur CPU contre ~2 s en cloud. Le fail-closed garantit qu'aucune hallucination ne passe — au pire l'agent répond *« Je n'ai pas trouvé cette information. »*.

#### Test rapide

```bash
curl -X POST http://localhost:58000/ai/ask \
  -H 'Content-Type: application/json' \
  -d '{"message": "Que peut apprendre la fusion Pikachu × Charizard ?"}'
```

#### Que se passe-t-il sans provider ?

```bash
$ curl -s http://localhost:58000/ai/ask -d '{"message":"hi"}' | jq .detail
{
  "error": "No LLM provider configured",
  "options": [
    { "provider": "deepseek", "label": "...", "steps": [...] },
    { "provider": "ollama",   "label": "...", "steps": [...] }
  ]
}
```

Le frontend peut afficher cette payload comme une bannière d'aide.

### Proxy Next.js

```dotenv
BACKEND_INTERNAL_URL=http://backend:8000     # Docker interne
SPRITES_INTERNAL_URL=http://sprites:80       # Docker interne
```

Ces variables sont lues **à runtime** par les route handlers — pas besoin de rebuild pour les changer.

## Mode prod / démo

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

En prod, seul `frontend` est exposé publiquement. Prérequis : `.env.prod` avec `POSTGRES_PASSWORD`, `CORS_ALLOWED_ORIGINS=https://<domaine>`, `FUSIONDEX_FRONTEND_PORT=<public>`.

## Tests

### Backend

```bash
cd backend
uv run pytest
```

53 tests. **Ils nécessitent un dump SQL** sous `backend/tests/fixtures/` (non committé). La CI actuelle ne lance que `test_ai.py` (smoke test DeepSeek). Cf. [Roadmap](roadmap.md).

### Frontend

Pas encore de suite de tests (Playwright prévu).

## Commits

Le projet suit [Conventional Commits](https://www.conventionalcommits.org/) :

- `feat(backend):` / `feat(frontend):` / `feat(etl):`
- `fix(frontend):` — bugs UI
- `refactor(infra):` — Docker, CI, proxy
- `test(backend):` — pytest
- `docs:` — cette doc

Les commits générés par l'assistant incluent :

```
Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

## Structure du repo

```
backend/        # FastAPI + SQLAlchemy + tests
etl/            # pipeline Python + uv
frontend/       # Next.js 15 App Router
docker/         # Dockerfiles + init_postgres.sql
docs/           # cette documentation (MkDocs)
data/           # dumps + caches (gitignored)
.github/        # CI workflows
```

## Voir aussi

- [Architecture](architecture.md)
- [ETL](etl.md)
- [API backend](api.md)
- [Référence code (auto-générée)](reference/index.md) — routes, services, schemas, models
