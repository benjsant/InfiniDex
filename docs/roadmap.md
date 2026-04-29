# Roadmap

Version live du suivi : [ROADMAP.md](https://github.com/benjsant/FusionDex-IA/blob/main/ROADMAP.md) à la racine du repo. Cette page reprend l'état au moment de la dernière mise à jour de la doc et liste les pistes ouvertes.

## État par couche

### ETL — ✅ stabilisé

Pipeline en 12 étapes. Données actuelles :

- **572 Pokémon** (501 IF + 71 formes)
- **676 moves** · **178 abilities** · **40 067** pokemon_move
- **166 090** fusion_sprite · **23** triple_fusion
- **7 081** créateurs · **1 634** pokemon_location
- **65** règles Move Expert (36 Knot + 29 Boon)

**Pistes ouvertes :**

- [ ] Audit DB — Pokémon sans sprites, moves orphelins, cohérence des fusions
- [ ] Scheduler (Prefect ou n8n) pour automatiser les refresh

### Base de données — 🚧 ajouts planifiés

Avant d'exploiter la cascade IA, enrichir les données structurées :

- [ ] **Move tutors** — nouvelle table `move_tutor(move_id, location_id, price, currency, notes)` scrapée depuis le wiki IF
- [ ] **TM location** — nettoyer `tm.location` (texte libre avec bugs de parsing) et la lier via FK à `location(id)`
- [ ] **Endpoint `/moves/{id}` enrichi** — inclure TM number + location + tutors

### Backend — ✅ base solide

41 endpoints (+ `/health`) + 109 tests collectés. Couvre pokémon, moves, abilities, types, fusions, sprites, triple-fusions, générations, créateurs, stats, IA.

**Optimisations livées (PRs #9 → #31)** :

- Index `idx_fusion_sprite_body` (seq scan 7.8ms → BitmapOr 2.76ms), contrainte partielle `uq_fusion_sprite_default`
- `load_pokemon_for_fusion` : double `joinedload` types+abilities en 1 query
- `compute_fusion_moves` : 1 query pour head+body au lieu de 2
- `search_moves` : ilike DB-side avant normalisation Python
- `random_fusion_ids` : `ORDER BY RANDOM() LIMIT 2` (plus de Python `random.choice`)
- `StaticCacheMiddleware` : `Cache-Control: public, max-age=3600` sur tous les GET statiques
- Cache TTL wiki in-process (10 min, clé normalisée)
- `MAX_TOKENS` IA : 1024 → 2048 (évite troncature sur réponses longues)
- SSE typé : `ToolCallEvent` + `TokenEvent` (remplacement du texte brut)

**Pistes ouvertes :**

- [ ] **CI full pytest** — le reste des tests nécessite un dump SQL fixture à committer sous `backend/tests/fixtures/`
- [ ] Endpoints pour les nouveaux ajouts BDD (tutors, TM enrichi)

### Frontend — ✅ pages principales complètes

Toutes les pages principales livrées : `/pokedex`, `/fusion`, `/moves`, `/types`, `/abilities`, `/ai`. Composants : `EvolutionChain`, `MovesetTable`, `FusionMovesetTable`, `FusionSprite`, `AiChat`, `AiSuggestButton`, `WeaknessGrid`, `PokemonCard`, `TypeBadge`, `StatBar`.

**Livraisons récentes (PRs #23 → #31)** :

- Streaming SSE IA avec pastilles ⚙ tool-call + badge provider
- Rendu Markdown des réponses IA (react-markdown + styles Tailwind)
- `staleTime: Infinity` sur tous les hooks — zéro refetch en arrière-plan
- Double sprite sur la page fusion (variante normale + inversée, cliquable)
- Crédit artiste sous chaque sprite (🎨 Nom, ou "Auto-généré")
- `FusionMovesetTable` : moveset head+body avec pastilles H/B/H+B par origine
- Requêtes différées par onglet sur la fiche Pokédex (−3 requêtes au chargement)
- `FusionSelector` pré-sélectionne via `?head=ID` et `?body=ID` (liens depuis Pokédex)
- Scroll SSE anti-jitter (`prevMessageCountRef` : smooth sur nouveau message, instant sur token)

**Pistes ouvertes :**

- [ ] Page triple-fusions (tab dédié)
- [ ] Galerie sprites + crédits (par créateur)
- [ ] Toggle EN/FR global persistent
- [ ] Tests Playwright
- [ ] UI transparence IA (sources, tokens, prompt envoyé)

### IA — 🚀 phases 1 et 2 livrées

**Phase 1 ✅** — Tools DB + circuit breaker + fail-closed :

- 5 tools DB : `get_pokemon`, `get_fusion`, `search_move`, `get_item`, `get_move_tutors`
- Boucle agent MAX_ITERATIONS=5, fail-closed sur réponse vide ou dépassement
- Provider pluggable : DeepSeek (prod) / Ollama (local)
- System prompt externe (`prompts/system.md`) en anglais, réponses forcées en français

**Phase 2 ✅** — Tool wiki IF + cache :

- `search_wiki` : requête MediaWiki API IF + cache TTL 10 min in-process
- Cascade retrieval : DB → wiki IF (→ futur : web DuckDuckGo)

**Phases restantes :**

| Phase | Scope | État |
|-------|-------|------|
| 3 | Tool DuckDuckGo (fallback web) + rate-limit | ⬜ à faire |
| 4 | UI transparence (sources, tokens, prompt affiché) | ⬜ à faire |
| 5 | Privacy layer (PII redactor) + provider OpenAI/Anthropic | ⬜ à faire |

**Contraintes maintenues :**

- Latence cascade ≤ 6s
- Max 5 tool calls par tour (circuit breaker)
- MAX_TOKENS=2048 (réponses longues sans troncature)

### Infra — ✅ v1 stable

- Docker Compose dev + override `docker-compose.prod.yml`
- Ports env-driven (préfixe 5)
- Proxy Next.js `/api/*` et `/sprites-cdn/*` (masque les URLs backend)
- CORS defense-in-depth côté FastAPI
- CI GitHub Actions — smoke test sur PR backend

**Pistes ouvertes :**

- [ ] Dump SQL fixture → full pytest en CI
- [ ] Choix de l'hébergement (Fly.io, Railway, VPS ?)
- [ ] TLS + domaine pour la démo publique
- [ ] Déployer la doc MkDocs (GitHub Pages ?)

### Documentation — ✅ mise à jour (PR #32)

Pages MkDocs Material à jour : architecture (section IA agentique + flux SSE), API (41 endpoints, SSE typé, `/ai/provider`), frontend (hooks lazy, FusionMovesetTable, AiChat), roadmap (état réel).

**Pistes ouvertes :**

- [ ] Diagrammes Mermaid de séquence (flux SSE détaillé)
- [ ] ERD complet de la base de données
- [ ] Guide contributeur (`CONTRIBUTING.md`)
- [ ] Captures d'écran frontend

## Cap v1.0

Les critères pour désarchiver les plans initiaux et considérer l'app complète :

- ✅ Frontend stable (toutes les pages principales en place)
- ✅ IA agentique phases 1-2 livrées (tool calling DB + wiki IF + refus strict)
- [ ] CI full verte (dump fixture committé)
- [ ] Déploiement public accessible
- ✅ Documentation à jour sur chaque page

Les phases 3-5 IA (DDG, transparence, privacy) sont cibles **v1.1** — amélioration continue post-lancement.

Avant cette étape, les docs historiques restent figées sous [Archive](archive/index.md).
