# FusionDex-IA — Roadmap

État d'avancement et prochaines étapes par couche.

## ETL — ✅ stabilisé

Pipeline complet en 12 étapes, factorisé en helpers :
- `etl/utils/sql.py` — `load_id_map`
- `etl/utils/wikitext.py` — fetch MediaWiki + clean
- `etl/utils/io.py` — `load_json` / `save_json`
- Héritage des moves de pré-évolutions (`enrich_evolution_movesets.py`)

**Données finales** : 572 Pokémon · 676 moves · 178 abilities · 40 067 pokemon_move · 166 090 fusion_sprite · 7 081 créateurs · 23 triple_fusion · 1 634 pokemon_location

**Pistes restantes**
- [ ] Audit DB — Pokémon sans sprites, moves orphelins, cohérence des fusions
- [ ] Scheduler (Prefect ou n8n) pour automatiser les refresh

## Base de données — ✅ stable

- [x] **Move tutors** — table `move_tutor` (41 tuteurs classiques, NPC + prix + localisation)
- [x] **pokemon_location enrichie** — 55 entrées "gift", 25 entrées "trade", tags `respawn:elite4|gold|none` sur les légendaires
- [x] **type_effectiveness** — 87 entrées pour les 8 types triple-fusion (IDs 37–44), types custom indépendants
- [x] **Fix triple fusion weaknesses** — `compute_triple_fusion_weaknesses` utilise les IDs de type directement
- [x] **TM location** — texte libre remplacé par lignes FK `tm_location` (lieu + notes structurés)

**Pistes restantes**
- [ ] Endpoint `GET /sprites/by_pokemon/{id}?custom_only=true` — nécessaire pour la grille de sprites customs frontend

## Backend FastAPI — ✅ stable

**41 endpoints + `/health`** couvrant Pokémon, moves, abilities, types, fusions, sprites, triple-fusions, générations, créateurs, stats, IA. **21 tests pytest** DB-free en CI (voir [backend/tests/](backend/tests/)).

**Livrés**
- [x] `/moves/tutors/all` + `/moves/experts/all` — listes complètes pour le frontend
- [x] `/moves/{id}/tutors` retourne `move_name_en` + `move_name_fr`
- [x] `/fusions/involving/{id}` — fusions impliquant un Pokémon (avec limit)
- [x] `/fusion/random` — fusion aléatoire head+body
- [x] Streaming SSE typé — `tool_call · token · source · usage`
- [x] Fix agent loop — `got_text and not tool_calls` (court-circuit sur preamble text + tool calls)
- [x] System prompt renforcé — règle database-first explicite, outils obligatoires par sujet

**Pistes restantes**
- [ ] `GET /sprites/by_pokemon/{id}?custom_only=true` — sprites custom d'un Pokémon (pour la grille frontend)
- [ ] CI full pytest — dump SQL fixture à committer sous `backend/tests/fixtures/`

## Frontend Next.js — ✅ complet

Toutes les pages livrées. Theme dark/light persistant. Design IF-style (palette navy/gold, tokens CSS `@theme`, grid texture). Responsive mobile-first.

**Pages**

| Route | Contenu |
|-------|---------|
| `/` | Landing — grille des modules |
| `/pokedex` | Liste paginée (40/page) + recherche + filtres type/légendaire |
| `/pokedex/[id]` | Onglets Stats · Capacités · Évolutions · Faiblesses · Fusion (100 aperçus) |
| `/fusion` | Sélecteur head/body + bouton fusion aléatoire |
| `/fusion/[headId]/[bodyId]` | Stats + double sprite + moveset + suggestion IA |
| `/ai` | Chat IA plein écran — badges source, compteur tokens, PromptModal |
| `/moves` | Liste paginée (50/page) + filtre type/catégorie + icône loupe |
| `/moves/[id]` | Fiche capacité — type, catégorie, puissance, PP, description FR/EN |
| `/moves/tutors` | Tuteurs classiques groupés par lieu + Move Experts par île |
| `/abilities` | Liste paginée (40/page) + panel détail inline + icône loupe |
| `/abilities/[id]` | Fiche talent — description FR/EN, badge "Modifié IF", notes |
| `/types` | Grille d'efficacité 18×18 Gen 7 |
| `/triple-fusions` | 23 fusions triples légendaires avec stats et faiblesses |
| `/creators` | Galerie paginée (48/page) + recherche |
| `/creators/[id]` | Grille sprites d'un créateur, cliquables vers la fusion |

**Composants clés**
- `MovesetTable` — icône `Info` par capacité → description inline lazy-fetchée
- `AiChat` — streaming SSE, pastilles ⚙ tool-call, badges DB/Wiki/Web, compteur tokens, `PromptModal`
- `FusionSelector` — bouton aléatoire (🔀), filtre Kanto/Hoenn/Tous
- `ThemeProvider` + anti-flash script — toggle ☀/🌙 persisté en `localStorage`

**Pistes restantes**
- [ ] Grille sprites customs dans l'onglet Fusion (attend l'endpoint backend)
- [ ] Toggle EN/FR global persistant
- [ ] Tests Playwright

## IA — ✅ phases 1–3 livrées

| Phase | Scope | État |
|-------|-------|------|
| 1 | Tools DB + refus strict | ✅ — 8 tools, boucle agent MAX_ITERATIONS=5, fail-closed |
| 2 | Tool `search_wiki` (MediaWiki IF) | ✅ — cache TTL 10 min, fetch page complète si intro courte |
| 3 | Tool `search_web` (DuckDuckGo) + streaming réel + transparence | ✅ — SSE token-par-token, SourceEvent, UsageEvent, PromptModal |
| 4 | Privacy layer (PII redactor) + provider OpenAI/Anthropic | ⬜ à faire |

**Fix livré (PR #37)** — agent loop corrigé : quand DeepSeek streame du texte de preamble *avant* ses tool_calls dans le même tour SSE, `got_text = True` court-circuitait le dispatch. Fix : `if got_text and not tool_calls`.

**Contraintes maintenues**
- Latence cascade ≤ 6s
- MAX_ITERATIONS = 5 (circuit breaker)
- MAX_TOKENS = 2048
- MAX_HISTORY_MSGS = 10

## Infra — ✅ v1 stable

- Docker Compose dev + override `docker-compose.prod.yml`
- Ports env-driven (préfixe 5)
- Proxy Next.js `/api/*` et `/sprites-cdn/*` (masque les URLs backend)
- CORS defense-in-depth côté FastAPI
- CI GitHub Actions — 21 tests DB-free sur chaque PR backend

**Pistes restantes**
- [ ] Dump SQL fixture → full pytest en CI
- [ ] Choix hébergement (Fly.io, Railway, VPS ?)
- [ ] TLS + domaine pour la démo publique
- [ ] Déployer la doc MkDocs (GitHub Pages ?)

## Documentation — ✅ à jour

9 pages MkDocs Material : index, architecture, database, development, api, frontend, fusion-rules, roadmap, reference. Hébergée via profil Compose `docs` sur `:58100`.

**Pistes restantes**
- [ ] Captures d'écran frontend
- [ ] Diagrammes Mermaid — séquence SSE, ERD complet
- [ ] `CONTRIBUTING.md`

## Prochaines étapes (ordre de priorité)

1. **`GET /sprites/by_pokemon/{id}?custom_only=true`** — endpoint backend + grille frontend dans l'onglet Fusion
2. **Déploiement** — choix hébergement, TLS, domaine public
3. **Toggle EN/FR** — persistant globalement
4. **Phase 4 IA** — PII redactor + support provider Anthropic/OpenAI
5. **CI full pytest** — dump SQL fixture committé

## Cap v1.0

- ✅ Frontend stable (toutes les pages en place)
- ✅ IA agentique phases 1–3 livrées
- ✅ Documentation à jour
- [ ] CI full verte (dump fixture committé)
- [ ] Déploiement public accessible
