# Contributing to InfiniDex-IA

Thanks for your interest in contributing. This guide covers local setup, conventions, and the PR process.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker + Docker Compose v2 | latest | All services |
| Python | ≥ 3.12 | Backend / ETL (via `uv`) |
| [`uv`](https://github.com/astral-sh/uv) | latest | Python dependency manager |
| Node.js | ≥ 20 | Frontend (optional — Docker works too) |

## Local setup

```bash
git clone https://github.com/benjsant/InfiniDex-IA.git
cd InfiniDex-IA

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

The schema is created automatically, but **data is not bundled** (fan-game assets). Run the ETL:

```bash
cd etl
uv sync
uv run python -m etl.scripts.load_db   # ~5–15 min
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

All tests run via Docker — never install pytest or Playwright locally.

**Backend (160 tests against a real Postgres):**
```bash
docker compose --profile test run --rm test-backend
```

**E2E Playwright (10 tests — requires the stack to be running):**
```bash
docker compose up -d          # start frontend + backend + db
docker compose --profile e2e run --rm e2e
```

**Type-check frontend only:**
```bash
docker compose run --rm --no-deps frontend sh -c "npm run build"
```

The CI runs two workflows:

- `ci.yml` — lint + mypy + build on every push
- `full-pytest.yml` — 160 backend tests against a real Postgres, triggered on PRs

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

Breaking changes: append `!` after scope — `feat(api)!: rename endpoint`.

## Branch naming

```
feat/<short-description>
fix/<short-description>
docs/<short-description>
```

Work from `main`. Open PRs against `main`.

## Pull request checklist

- [ ] Backend tests pass (`docker compose --profile test run --rm test-backend`)
- [ ] No new mypy errors (`docker compose run --rm --no-deps backend uv run mypy backend/`)
- [ ] Frontend builds without TypeScript errors (`docker compose run --rm --no-deps frontend sh -c "npm run build"`)
- [ ] New tools registered in `TOOLS` list and covered by a test
- [ ] Prompt changes in `backend/prompts/system.md` reviewed for fail-closed behavior

## Project structure

```
backend/        FastAPI + SQLAlchemy 2 + Pydantic (49 endpoints, 160 tests)
├── routes/     API route handlers
├── services/   Business logic, AI agent, tools
│   └── tools/  Agent tools (db_tools, wiki_tool, web_tool)
├── prompts/    LLM system prompt
└── tests/      pytest suite (fixtures/ = dump SQL Postgres)

frontend/       Next.js 15 App Router + TypeScript
├── app/        Pages and layouts
├── components/ UI components (AI, Pokemon, Fusion…)
├── hooks/      Data-fetching hooks
└── lib/        Constants, API client, types

etl/            Data pipeline (MediaWiki + PokeAPI → Postgres)
e2e/            Playwright E2E tests (10 happy-path tests, Chromium)
docker/         Dockerfiles + init_postgres.sql
docs/           MkDocs documentation source
```

## AI / tool-calling system

The AI agent (`backend/services/ai_service.py`) calls tools in a cascade:
**DB tools → search_wiki → search_web → fail-closed**.

Adding a tool:
1. Create `backend/services/tools/your_tool.py` — define a `Tool` instance
2. Import and add it to `TOOLS` in `backend/services/tools/__init__.py`
3. Add its label to `AI_TOOL_LABELS` in `frontend/lib/constants.ts`
4. Add tests in `backend/tests/test_ai_tools.py`
5. Update `backend/prompts/system.md` if the tool changes call semantics

## Code style

- **Python**: ruff (linting + formatting), mypy strict. Run `uv run ruff check . && uv run mypy backend/`.
- **TypeScript**: ESLint + tsc. Run `npm run lint && npm run build` in `frontend/`.
- **Comments**: only when the *why* is non-obvious. No docstring novels.
- **No hallucination surface**: every factual claim in the AI prompt must be verifiable via a tool — no hardcoded game data in system.md that the DB already covers.

## Getting help

Open a [GitHub issue](https://github.com/benjsant/InfiniDex-IA/issues) for bugs or questions. The [docs](https://benjsant.github.io/InfiniDex-IA/) cover architecture, API reference, and the full development guide.
