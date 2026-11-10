# Contributing to InfiniDex

Thanks for your interest in contributing. This guide covers local setup, conventions, and the PR process.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker + Docker Compose v2 | latest | All services |
| Python | ≥ 3.12 | Backend / ETL (via `uv`) |
| [`uv`](https://github.com/astral-sh/uv) | latest | Python dependency manager |
| Node.js | ≥ 20 | Frontend (optional - Docker works too) |

## Local setup

```bash
git clone https://github.com/benjsant/InfiniDex.git
cd InfiniDex

cp .env.example .env
# Optional: add DEEPSEEK_API_KEY or OPENROUTER_API_KEY for AI features

docker compose up -d
```

Services:

- Frontend → http://localhost:53000
- Backend / Swagger → http://localhost:58000/docs
- Sprites → http://localhost:58080/sprites/
- Postgres → `localhost:55432`

### Populate the database

The schema is created automatically, but **data is not bundled** (fan-game assets). On a fresh volume, `docker compose up -d` runs the `etl` container first (~40 min, mostly the sprite download) and the backend waits for it. To re-run it on an existing database:

```bash
docker compose run --rm etl python etl/pipeline.py --force
docker compose up backend -d --force-recreate   # reload the backend caches
```

### Dev without Docker

**Backend:**
```bash
cd backend
uv sync
uv run uvicorn backend.main:app --reload --port 58000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

## Running tests

All tests run via Docker - never install pytest or Playwright locally.

**Backend (~170 tests against a real Postgres):**
```bash
docker compose --profile test run --rm test-backend
```

**ETL (parser and pipeline unit tests, no database):**
```bash
docker compose --profile test run --rm test-etl
```

**E2E Playwright (13 tests - requires the stack to be running):**
```bash
docker compose up -d          # start frontend + backend + db
docker compose --profile e2e run --rm e2e
```

**Frontend build (typecheck + `next build`):**
```bash
docker compose build frontend
```

The CI runs six workflows, path-filtered on the layer they cover:

| Workflow | Trigger | Content |
|----------|---------|---------|
| `backend-ci.yml` | `backend/**` | import check + DB-free tests, then full pytest against Postgres 16 with the committed fixtures |
| `frontend-ci.yml` | `frontend/**` | `next typegen` + `tsc --noEmit` + ESLint |
| `etl-ci.yml` | `etl/**` | `compileall` gate + ETL unit tests |
| `e2e.yml` | frontend, backend, e2e, Dockerfiles, compose | 13 Playwright tests against the Docker stack on the fixture DB |
| `docs.yml` | push on `main` (docs) | MkDocs build + GitHub Pages deploy |
| `wiki-watch.yml` | Monday cron + manual | probes upstream sources; red means "re-run the ETL" (see `docs/etl.md`) |

## Commit conventions

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(backend): add search_pokemon_locations tool
fix(frontend): correct token count display condition
refactor(ai): extract web_service from ai_service
test(backend): add search_web mock tests
docs: add screenshots to MkDocs fusion section
ci: add full pytest workflow
chore: update uv.lock with duckduckgo-search 8.1.1
```

Scope hints: `backend`, `frontend`, `etl`, `ai`, `infra`, `db`.

Breaking changes: append `!` after scope - `feat(api)!: rename endpoint`.

## Branch naming

```
feat/<short-description>
fix/<short-description>
docs/<short-description>
```

Work from `main`. Open PRs against `main`.

## Pull request checklist

- [ ] Backend tests pass (`docker compose --profile test run --rm test-backend`)
- [ ] ETL tests pass if `etl/` changed (`docker compose --profile test run --rm test-etl`)
- [ ] Frontend builds without TypeScript errors (`docker compose build frontend`)
- [ ] New tools registered in `TOOLS` list and covered by a test
- [ ] Prompt changes in `backend/prompts/system.md` reviewed for fail-closed behavior

## Project structure

```
backend/        FastAPI + SQLAlchemy 2 + Pydantic (54 endpoints, ~170 tests)
├── routes/     API route handlers
├── services/   Business logic, AI agent, tools
│   └── tools/  Agent tools (db_tools, wiki_tool, web_tool)
├── prompts/    LLM system prompt
└── tests/      pytest suite (fixtures/ = dump SQL Postgres)

frontend/       Next.js 16 App Router + TypeScript
├── app/        Pages and layouts
├── components/ UI components (AI, Pokemon, Fusion…)
├── hooks/      Data-fetching hooks
└── lib/        Constants, API client, types

etl/            Data pipeline (MediaWiki + PokeAPI → Postgres)
e2e/            Playwright E2E tests (13 happy-path tests, Chromium)
docker/         Dockerfiles + init_postgres.sql
docs/           MkDocs documentation source
```

## AI / tool-calling system

The AI agent (`backend/services/ai_service.py`) calls tools in a cascade:
**DB tools → search_wiki → search_web → fail-closed**.

Adding a tool:
1. Create `backend/services/tools/your_tool.py` - define a `Tool` instance
2. Import and add it to `TOOLS` in `backend/services/tools/__init__.py`
3. Add its label to `AI_TOOL_LABELS` in `frontend/lib/constants.ts`
4. Add tests in `backend/tests/test_ai_tools.py`
5. Update `backend/prompts/system.md` if the tool changes call semantics

## Code style

- **Python**: follow the surrounding style (PEP 8, type hints). No linter or type checker is wired in yet, neither in the lockfiles nor in CI.
- **TypeScript**: ESLint (flat config, `eslint-config-next`) + tsc, both enforced by `frontend-ci`.
- **Comments**: only when the *why* is non-obvious. No docstring novels.
- **No hallucination surface**: every factual claim in the AI prompt must be verifiable via a tool - no hardcoded game data in system.md that the DB already covers.

## Getting help

Open a [GitHub issue](https://github.com/benjsant/InfiniDex/issues) for bugs or questions. The [docs](https://benjsant.github.io/InfiniDex/) cover architecture, API reference, and the full development guide.
