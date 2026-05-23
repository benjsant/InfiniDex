# InfiniDex — Roadmap

État d'avancement et prochaines étapes par couche.

## ETL — ✅ stabilisé

Pipeline complet en 14 étapes (orchestrateur `etl/pipeline.py`), factorisé en helpers :
- `etl/utils/sql.py` — `load_id_map`
- `etl/utils/wikitext.py` — fetch MediaWiki + clean
- `etl/utils/io.py` — `load_json` / `save_json`
- Héritage des moves de pré-évolutions (`enrich_evolution_movesets.py`)

**Données finales** : 572 Pokémon · 659 moves · 183 abilities · 45105 pokemon_move · 168154 fusion_sprite · 7126 créateurs · 23 triple_fusion · 2560 pokemon_location · 188 locations · 121 TMs · 41 tuteurs

**Pistes restantes**
- [x] Audit DB — `audit_db.py` (11 checks) : 17 moves orphelins supprimés, 76 Pokémon enrichis (171 abilities ajoutées)
- [x] Scheduler Prefect self-hosted — `etl/flows/etl_pipeline.py` + `prefect.yaml` + services docker-compose (profil `prefect`)
- [x] Localisations sauvages — `load_pokedex_locations.py` parse la page Pokédex du wiki IF (541/572 Pokémon couverts, 2 560 entrées `pokemon_location`)

## Base de données — ✅ stable

**Données finales enrichies** :
- [x] **Move tutors** — table `move_tutor` (41 tuteurs classiques, NPC + prix + localisation)
- [x] **pokemon_location enrichie** — 55 entrées "gift", 25 entrées "trade", tags `respawn:elite4|gold|none` sur les légendaires
- [x] **type_effectiveness** — 87 entrées ajoutées pour les 8 types triple-fusion (IDs 37-44), types custom indépendants
- [x] **Fix triple fusion weaknesses** — `compute_triple_fusion_weaknesses` utilise les IDs de type directement
- [x] **TM location cleanup** — colonne `tm.location` supprimée, `location_summary` dérivé des FK `tm_location`

## Backend FastAPI — ✅ base solide

**51 endpoints + `/health`** couvrant Pokémon, moves, abilities, types, fusions, sprites, triple-fusions, générations, créateurs, stats, IA, CTs. **163 tests pytest** (voir [backend/tests/](backend/tests/)).

**Optimisations DB** (PR #9 en cours) — index `idx_fusion_sprite_body` (seq scan 7.8ms → BitmapOr 2.76ms sur `/fusions/involving`), contrainte partielle `uq_fusion_sprite_default`, `compute_fusion_abilities` 2→1 query.

**Endpoints ajoutés**
- [x] `/moves/tutors/all` — tous les tuteurs classiques pour le frontend
- [x] `/moves/experts/all` — tous les Move Experts pour le frontend
- [x] `/moves/{id}/tutors` retourne aussi `move_name_en` et `move_name_fr`

**Pistes restantes**
- [x] **CI full pytest** — dump SQL committé sous `backend/tests/fixtures/`, workflow `full` avec postgres:16
- [x] **Endpoints TM enrichi** — `GET /tms/` + `GET /tms/{number}` avec move complet + lieux d'obtention

## Frontend Next.js — ✅ stable

Pages en place : `/pokedex` + `/pokedex/[id]`, `/fusion` + `/fusion/[headId]/[bodyId]`, `/moves`, `/moves/tutors`, `/types`, `/abilities`, `/ai`, `/triple-fusions`. Proxy runtime `/api/*` + `/sprites-cdn/*`. Composants : EvolutionChain, MovesetTable, PokemonCard, FusionSprite, AiChat, CreatorModal, WeaknessGrid, etc. Hooks typés : useFusion, useMoves, usePokemon, useAiChat.

**Fonctionnalités ajoutées**
- [x] Page `/moves/tutors` — Maîtres des Capacités (tuteurs classiques groupés par lieu + Move Experts par île)
- [x] Page `/triple-fusions` — liste des 23 fusions triples
- [x] `FusionSelector` — filtre Kanto/Hoenn/Tous (`GameFilter = "kanto" | "hoenn" | "all"`)
- [x] Responsive mobile — hamburger + drawer full-width (`md:hidden`), `hidden sm:table-cell`, `flex-col md:flex-row`
- [x] Design IF-style — palette gold `#e8b84b`, fond `#090c1a`, tokens CSS `@theme`, grid texture, TypeBadge avec glow, PokemonCard avec gradient de type, StatBar avec gradient + glow
- [x] `search_pokemon_locations` — outil IA pour chercher les Pokémon par condition/méthode

**Pistes restantes**
- [x] Galerie sprites + crédits (par créateur) — page `/creators` avec 7 126 créateurs, recherche, modal sprites
- [ ] Toggle EN/FR global persistent
- [x] Tests Playwright — 10 tests E2E (homepage, pokédex, fusion, types/items, moves) via `docker compose --profile e2e run --rm e2e`
- [x] UI transparence IA — ToolPill, SourceBadge, token count, PromptModal

## IA — 🚧 en cours : phases avancées (transparence, privacy)

L'objectif n'est plus un simple chat générique branché sur DeepSeek, mais un **assistant agentique** qui interroge la BDD, le wiki IF et le web de façon structurée, avec refus explicite en cas d'absence de donnée et transparence sur ce qui est envoyé au LLM.

### Principes de conception

1. **Tool calling natif** — DeepSeek (OpenAI-compatible function calling) choisit quels tools appeler
2. **Cascade de retrieval** — DB interne → wiki IF (MediaWiki API) → web (DuckDuckGo)
3. **Fail-closed** — si aucun tool ne remonte d'info pertinente, réponse explicite `"Je n'ai pas trouvé cette information."` — jamais d'invention
4. **Transparence** — l'UI montre quels tools ont été appelés, quelles sources, combien de tokens
5. **Privacy first** — couche de redaction PII (noms de créateurs, futurs usernames) **avant** envoi au LLM
6. **Provider pluggable** — interface `LLMProvider` abstraite, implémentations DeepSeek / OpenAI / Anthropic / Ollama

### Phases d'implémentation

Chaque phase = une PR + un post LinkedIn *building in public*.

| Phase | Scope | État |
|-------|-------|------|
| 1 | **Tools DB + refus strict** | ✅ livré — 7 tools (`get_pokemon`, `get_fusion`, `search_move`, `get_item`, `get_move_tutors`, `search_wiki`, `search_pokemon_locations`), boucle tool-call, system prompt anti-hallucination, circuit breaker (max 5 tool calls/turn) |
| 2 | **Tool MediaWiki IF** | ✅ livré — `search_wiki` avec cache TTL 10 min, fetch page complète si intro < 300 caractères |
| 3 | **Tool DuckDuckGo** | ✅ livré — `search_web` via `ddgs`, cache 5 min, déduplication concurrente, max 1500 chars, 3 tests mockés |
| 4 | **UI transparence** | ✅ livré — tool pills en temps réel, source badges (db/wiki/web), compteur tokens, bouton « voir le prompt » + PromptModal (system prompt + outils) |
| 5 | **Privacy layer + provider pluggable** | ✅ livré — `LLMProvider` ABC, DeepSeek/OpenRouter/Ollama, PII redactor (key removal + regex Discord/@ en profondeur), 19 tests |

### Contraintes techniques

- **Latence** : cascade complète ≤ 6s (SLA cible). Si dépassé, un mode `/ai/ask-fast` (DB only) reste disponible.
- **Coûts** : compter tokens par session, alerte si > seuil configurable.
- **Context window** : DeepSeek chat = 64k tokens. Compression/troncation des tool results si besoin.
- **Boucles infinies** : max 5 tool calls/turn, sinon fail-closed.

### Précisions use-case

L'assistant cible 3 usages (par ordre de priorité) :
1. **Expliquer une fusion** — "Pourquoi cette fusion a tel type ?", "Quels moves intéressants ?"
2. **Recommandations stratégiques** — "Donne-moi une fusion anti-Psychic avec Pikachu en head"
3. **Q&A mécaniques IF** — "Comment fonctionnent les Move Experts ?", "Où est le Mystic Water ?"

## Infra — ✅ v1 stable

- Docker Compose dev + override `docker-compose.prod.yml`
- Ports env-driven (préfixe 5)
- Proxy Next.js `/api/*` et `/sprites-cdn/*` (masque les URLs backend)
- CORS defense-in-depth côté FastAPI
- CI GitHub Actions — smoke test sur PR backend

**Pistes restantes**
- [x] Dump SQL fixture → full pytest en CI
- [ ] Choix de l'hébergement (Fly.io, Railway, VPS ?)
- [ ] TLS + domaine pour la démo publique
- [x] Déployer la doc MkDocs (GitHub Pages) — workflow `docs.yml`, URL `benjsant.github.io/InfiniDex`

## Documentation — ✅ complète

10 pages MkDocs Material + référence auto-générée via `mkdocstrings`. Build strict vert. Hébergée via profil Compose `docs` sur `:58100`.

**Pistes restantes**
- [x] Diagrammes Mermaid enrichis — pipeline ETL, ERD complet (toutes tables), séquences requête Pokémon + résolution sprite
- [x] Guide contributeur (`CONTRIBUTING.md`)
- [x] Captures d'écran frontend — 30 captures (desktop, mobile, light/dark) via Playwright
- [x] Page dédiée à l'architecture IA agentique — `docs/ia.md` : boucle agent, cascade retrieval, privacy PII, provider pluggable

## Cap v1.0

Les critères pour désarchiver les plans initiaux et considérer l'app complète :

- Frontend stable (toutes les pages principales, pas de bugs bloquants)
- **IA agentique phase 1-2 livrée** (tool calling DB + wiki IF + refus strict)
- CI full verte (dump fixture committé)
- Déploiement public accessible
- Documentation à jour sur chaque page

Les phases 3-5 IA (DDG, transparence, privacy) sont livrées en **v1.0** — toutes les phases IA sont complètes.
