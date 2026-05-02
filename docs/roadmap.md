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

### Base de données — ✅ enrichie

- [x] **Move tutors** — table `move_tutor` (41 NPCs classiques, prix, localisation)
- [x] **pokemon_location enrichie** — 55 entrées "gift", 25 entrées "trade", tags `respawn:elite4|gold|none` sur les légendaires
- [x] **type_effectiveness triple-fusion** — 87 entrées pour les 8 types triple-fusion (id 37–44) ; ces types sont des types custom indépendants, pas calculés multiplicativement
- [x] **Fix `compute_triple_fusion_weaknesses`** — utilise les IDs de types directement au lieu de décomposer les noms composés

**Piste ouverte :**

- [ ] **TM location** — nettoyer `tm.location` (texte libre avec bugs de parsing) et la lier via FK à `location(id)`

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

**Ajouts récents :**

- [x] Endpoints `GET /moves/tutors/all` et `GET /moves/experts/all` (liste complète pour le frontend)
- [x] `/moves/{id}/tutors` retourne maintenant `move_name_en` + `move_name_fr`

**Pistes ouvertes :**

- [ ] **CI full pytest** — le reste des tests nécessite un dump SQL fixture à committer sous `backend/tests/fixtures/`
- [ ] Endpoint `/moves/{id}` enrichi avec TM number + location (après TM location cleanup)

### Frontend — ✅ complet

Toutes les pages livrées : `/pokedex`, `/fusion`, `/moves`, `/moves/tutors`, `/types`, `/abilities`, `/triple-fusions`, `/ai`. Composants : `EvolutionChain`, `MovesetTable`, `FusionMovesetTable`, `FusionSprite`, `AiChat`, `AiSuggestButton`, `WeaknessGrid`, `PokemonCard`, `TypeBadge`, `StatBar`, `CreatorModal`.

**Livraisons récentes :**

- Streaming SSE IA avec pastilles ⚙ tool-call + badge provider
- Rendu Markdown des réponses IA (react-markdown + styles Tailwind)
- `staleTime: Infinity` sur tous les hooks — zéro refetch en arrière-plan
- Double sprite sur la page fusion (variante normale + inversée, cliquable)
- Crédit artiste sous chaque sprite (par créateur, ou "Auto-généré")
- `FusionMovesetTable` : moveset head+body avec pastilles H/B/H+B par origine
- Requêtes différées par onglet sur la fiche Pokédex (−3 requêtes au chargement)
- `FusionSelector` pré-sélectionne via `?head=ID` et `?body=ID` + filtre `GameFilter` (Kanto/Hoenn/Tous)
- [x] Page `/moves/tutors` — 41 tuteurs classiques + Move Experts groupés par île
- [x] Page `/triple-fusions` — 23 fusions triples avec faiblesses
- [x] **Responsive mobile/tablette** — hamburger Navbar, tables avec `hidden sm:table-cell`, panels `flex-col md:flex-row`
- [x] **Design IF-style** — palette navy `#090c1a`, gold `#e8b84b`, tokens CSS `@theme`, grid texture, TypeBadge glow, PokemonCard gradient type, StatBar gradient + glow

**Pistes ouvertes :**

- [ ] Galerie sprites + crédits (par créateur)
- [ ] Toggle EN/FR global persistent
- [ ] Tests Playwright
- [ ] UI transparence IA (sources, tokens, prompt envoyé)

### IA — 🚀 phases 1 et 2 livrées

**Phase 1 ✅** — Tools DB + circuit breaker + fail-closed :

- 6 tools DB : `get_pokemon`, `get_fusion`, `search_move`, `get_item`, `get_move_tutors`, `search_pokemon_locations`
- `search_pokemon_locations` : cherche les Pokémon par condition/méthode dans `pokemon_location` (gift, trade, static, wild…)
- Boucle agent MAX_ITERATIONS=5, fail-closed sur réponse vide ou dépassement
- Provider pluggable : DeepSeek (prod) / Ollama (local)
- System prompt externe (`prompts/system.md`) en anglais, réponses forcées en français + règles anti-boucle, guidage `search_pokemon_locations`, section "Key game mechanics" (trade evos, HMs, triple fusion unlock, respawn, OHKO+NoGuard, Hidden Power)

**Phase 2 ✅** — Tool wiki IF + cache :

- `search_wiki` (7e outil) : requête MediaWiki API IF + cache TTL 10 min in-process ; fetch page complète si intro < 300 caractères
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

### Documentation — ✅ mise à jour

Pages MkDocs Material à jour : README, ROADMAP, architecture (outils IA, flux SSE), API (41 endpoints + tutors/experts), frontend (design IF, responsive, nouvelles pages), roadmap (état réel), `docs/index.md`.

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
