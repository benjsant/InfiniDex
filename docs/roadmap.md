# Roadmap

Version live du suivi : [ROADMAP.md](https://github.com/benjsant/InfiniDex/blob/main/ROADMAP.md) à la racine du repo. Cette page reprend l'état au moment de la dernière mise à jour de la doc et liste les pistes ouvertes.

## État par couche

### ETL - ✅ stabilisé

Pipeline en 38 étapes (orchestrateur `etl/pipeline.py`). Données actuelles :

- **572 Pokémon** (501 IF + 71 formes)
- **658 moves** · **183 abilities** · **45 073** pokemon_move
- **168 154** fusion_sprite · **23** triple_fusion
- **7 126** créateurs · **2 448** pokemon_location · **188** locations
- **121** TMs · **41** tuteurs de capacités

**Pistes ouvertes :**

- [x] Audit DB - moves orphelins nettoyés, Pokémon sans abilities enrichis
- [x] Scheduler Prefect self-hosted - `etl/flows/etl_pipeline.py` (profil `prefect`)
- [x] Localisations sauvages - `load_pokedex_locations.py` depuis la page Pokédex du wiki IF (541/572 Pokémon couverts)

### Base de données - ✅ enrichie

- [x] **Move tutors** - table `move_tutor` (41 NPCs classiques, prix, localisation)
- [x] **pokemon_location enrichie** - 55 entrées "gift", 25 entrées "trade", tags `respawn:elite4|gold|none` sur les légendaires
- [x] **type_effectiveness triple-fusion** - 87 entrées pour les 8 types triple-fusion (id 37–44) ; ces types sont des types custom indépendants, pas calculés multiplicativement
- [x] **Fix `compute_triple_fusion_weaknesses`** - utilise les IDs de types directement au lieu de décomposer les noms composés

**Piste ouverte :**

- [x] **TM location** - `tm.location` (texte libre) supprimée, `location_summary` dérivé des FK `tm_location`

### Backend - ✅ base solide

54 endpoints + `/health` + 136 tests pytest. Couvre pokémon, moves, abilities, types, fusions, sprites, triple-fusions, générations, créateurs, stats, IA.

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

- [ ] **CI full pytest** - le reste des tests nécessite un dump SQL fixture à committer sous `backend/tests/fixtures/`
- [ ] Endpoint `/moves/{id}` enrichi avec TM number + location (après TM location cleanup)

### Frontend - ✅ complet

Pages : `/pokedex`, `/pokedex/[id]`, `/pokedex/favorites`, `/fusion`, `/fusion/[headId]/[bodyId]`, `/fusion/compare`, `/fusion/top`, `/fusion/history`, `/fusion/random`, `/moves`, `/moves/tutors`, `/types`, `/abilities`, `/items`, `/triple-fusions`, `/creators`, `/creators/[id]`, `/ai`. Composants : `EvolutionChain`, `MovesetTable`, `FusionMovesetTable`, `FusionSprite`, `AiChat`, `WeaknessGrid`, `PokemonCard`, `TypeBadge`, `StatBar`, `CreatorModal`.

**Livraisons récentes :**

- [x] Page `/fusion/compare` - comparateur côte à côte avec delta stats + bouton d'inversion head↔body
- [x] Page `/fusion/history` - historique local (localStorage)
- [x] Page `/creators` et `/creators/[id]` - galerie des 7 126 créateurs de sprites
- [x] Suggestions IA en popover (icône ampoule dans la toolbar)
- [x] Footer masqué sur `/ai` pour maximiser l'espace chat
- [x] Refonte OG images + JSON-LD + sitemap + PWA icons
- [x] `cache: "no-store"` sur `apiFetch` - évite le cache HTTP navigateur après un re-run ETL

**Pistes ouvertes :**

- [ ] Toggle EN/FR global persistent
- [x] Tests Playwright - 10 tests E2E Chromium (`docker compose --profile e2e run --rm e2e`)

### IA - ✅ phases 1 à 5 livrées

**Phase 1 ✅** - Tools DB + circuit breaker + fail-closed :

- 8 tools : `get_pokemon`, `get_fusion`, `get_triple_fusion`, `search_move`, `get_item`, `get_move_tutors`, `search_pokemon_locations`, `search_wiki`
- Boucle agent MAX_ITERATIONS=8, fail-closed sur réponse vide ou dépassement
- Provider pluggable : DeepSeek (prod) / Ollama (local)
- System prompt externe (`prompts/system.md`) - règles anti-hallucination, anti-extrapolation jeux officiels, anti-emojis, fail-closed strict

**Phase 2 ✅** - Tool wiki IF + cache :

- `search_wiki` : MediaWiki API IF + cache TTL 10 min in-process

**Phase 3 ✅** - Tool web DuckDuckGo :

- `search_web` : fallback web en dernier recours, cache TTL 5 min, max 1 appel par tour

**Phase 4 ✅** - Transparence UI :

- Pastilles ⚙ tool-call + badges `db` / `wiki` / `web` avec URLs cliquables
- Compteur de tokens sous chaque réponse

**Phase 5 ✅** - Privacy + robustesse :

- `pii_redact` sur tous les résultats d'outils avant envoi au LLM
- Temperature abaissée à 0.1 (moins d'hallucinations)
- Historique tronqué côté client à 30 messages (évite erreur 422 sur longues sessions)

**Contraintes maintenues :**

- Max 8 itérations agent (circuit breaker)
- MAX_TOKENS=4096
- Fail-closed strict : "Je n'ai pas trouvé cette information." si aucun tool ne remonte de données IF

### Infra - ✅ v1 stable

- Docker Compose dev + override `docker-compose.prod.yml`
- Ports env-driven (préfixe 5)
- Proxy Next.js `/api/*` et `/sprites-cdn/*` (masque les URLs backend)
- CORS defense-in-depth côté FastAPI
- CI GitHub Actions - smoke test sur PR backend

**Pistes ouvertes :**

- [ ] Dump SQL fixture → full pytest en CI
- [ ] Choix de l'hébergement (Fly.io, Railway, VPS ?)
- [ ] TLS + domaine pour la démo publique
- [ ] Déployer la doc MkDocs (GitHub Pages ?)

### Documentation - ✅ mise à jour

Pages MkDocs Material à jour : README, ROADMAP, architecture (9 outils IA, flux SSE, cascade DB→wiki→web), API, frontend (toutes les pages + hooks), ETL (pipeline.py 38 étapes), database, roadmap.

**Pistes ouvertes :**

- [ ] ERD complet de la base de données
- [ ] Diagrammes Mermaid de séquence supplémentaires

## Cap v1.0

Les critères pour désarchiver les plans initiaux et considérer l'app complète :

- ✅ Frontend stable (toutes les pages principales en place)
- ✅ IA agentique phases 1-5 livrées (tool calling DB + wiki IF + web + privacy + transparence)
- [ ] CI full verte (dump fixture committé)
- [ ] Déploiement public accessible
- ✅ Documentation à jour sur chaque page

Avant cette étape, les docs historiques restent figées sous [Archive](archive/index.md).

## Cap v1.1 - séparation InfiniDex / HoennDex

Décision actée 2026-06-23 : le futur jeu Pokémon Infinite Fusion: Hoenn est un fan-game séparé, pas une DLC. Il aura son propre projet (HoennDex). En conséquence, les 71 Pokémon actuellement marqués `is_hoenn_only` dans la DB d'InfiniDex ne sont **pas** dans le jeu Kanto et seront retirés à terme.

**Phase A - soft-remove** (à exécuter après livraison de la v0.1 du companion mobile Flutter `infinidex_mobile`) :

- [ ] `include_hoenn=False` par défaut sur les endpoints `/pokemon/*`
- [ ] Retirer le toggle Kanto/Hoenn du frontend (ou le mettre derrière un flag avancé)
- [ ] Mettre à jour les comptes dans README + docs : `572 Pokémon` → `501`
- [ ] CHANGELOG v1.1

**Phase B - hard delete** (à exécuter après HoennDex v0.1) :

- [ ] Migration SQL : DELETE en cascade sur `pokemon_move`, `pokemon_ability`, `pokemon_location`, `fusion_sprite`, `evolution`, puis `pokemon WHERE is_hoenn_only`
- [ ] Retrait du param API `include_hoenn` + colonne `is_hoenn_only` (modèle + schemas)
- [ ] Retrait des étapes ETL qui chargent ces Pokémon
- [ ] Recompter et publier les nouveaux chiffres (fusion_sprite notamment)
- [ ] Bump v1.2.0

Les Pokémon Hoenn complets (Gen 3) seront servis par le futur HoennDex via son propre wiki source et son propre Pokédex. Cf. mémoire `project_hoenn_cleanup_deferred.md`.
