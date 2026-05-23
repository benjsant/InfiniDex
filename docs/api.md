# API backend

FastAPI exposant 49 endpoints + `/health`. Swagger interactif en dev : [http://localhost:58000/docs](http://localhost:58000/docs). Référence auto-générée : [Routes](reference/routes.md).

En prod le backend n'est **pas** exposé publiquement — les requêtes passent par le proxy Next.js (`/api/*` sur le domaine public).

## Organisation

```
backend/
  main.py                 # wiring FastAPI + CORS + StaticCacheMiddleware
  routes/                 # endpoints HTTP (un fichier par domaine)
  services/               # logique métier + accès DB
    tools/                # outils de l'agent IA (db_tools.py, wiki_tool.py)
  schemas/                # Pydantic — contrat I/O
  prompts/
    system.md             # system prompt LLM (anglais, réponse forcée en français)
  db/
    models/               # SQLAlchemy
    base.py               # engine + session
  tests/                  # pytest + TestClient (160 tests)
```

Chaque `route` importe son `service`, qui importe ses `models` et `schemas`. Les routes ne touchent jamais directement SQLAlchemy.

## Cache HTTP

`StaticCacheMiddleware` (dans `main.py`) ajoute `Cache-Control: public, max-age=3600` sur toutes les réponses `GET 200`, **sauf** `/ai/*` et `/health`. Les clients et CDN peuvent mettre en cache les données statiques pendant 1 heure.

## Endpoints principaux

### Pokémon

| Méthode | Chemin                                          | Description                               |
| ------- | ----------------------------------------------- | ----------------------------------------- |
| GET     | `/pokemon/count`                                | Nombre total de Pokémon (entier brut)     |
| GET     | `/pokemon/`                                     | Liste paginée + filtres type/gen/Hoenn    |
| GET     | `/pokemon/search?q={nom}`                       | Recherche par nom EN ou FR (ilike accent-insensitive) |
| GET     | `/pokemon/{id}`                                 | Fiche complète (types, talents, stats)    |
| GET     | `/pokemon/{id}/moves`                           | Learnset (level-up + TM + tutor + egg)    |
| GET     | `/pokemon/{id}/evolutions`                      | Chaîne pre + post (bidirectionnelle)      |
| GET     | `/pokemon/{id}/locations`                       | Zones de capture                          |
| GET     | `/pokemon/{id}/weaknesses`                      | Matchups défensifs (multiplicateurs non-neutres uniquement) |

### Moves

| Méthode | Chemin                               | Description                                        |
| ------- | ------------------------------------ | -------------------------------------------------- |
| GET     | `/moves/`                            | Liste + filtres (category, type_id, power_min/max) |
| GET     | `/moves/search?q={nom}`              | Recherche nom EN/FR (accent-insensitive)           |
| GET     | `/moves/by-type/{type_name}`         | Capacités d'un type (EN ou FR)                     |
| GET     | `/moves/tutors/all`                  | Tous les tuteurs classiques (41) pour le frontend  |
| GET     | `/moves/experts/all`                 | Tous les Move Experts pour le frontend             |
| GET     | `/moves/{id}`                        | Détail complet + descriptions + TM info            |
| GET     | `/moves/{id}/tutors`                 | NPCs enseignant ce move (prix + localisation + `move_name_en` / `move_name_fr`) |

### Abilities

| Méthode | Chemin                           | Description                                |
| ------- | -------------------------------- | ------------------------------------------ |
| GET     | `/abilities/`                    | Liste des ~178 talents                     |
| GET     | `/abilities/search?q={nom}`      | Recherche nom EN/FR                        |
| GET     | `/abilities/{id}`                | Détail + descriptions EN/FR                |

### Types

| Méthode | Chemin                     | Description                                         |
| ------- | -------------------------- | --------------------------------------------------- |
| GET     | `/types/`                  | 27 types (18 standard + 9 triple-fusion)            |
| GET     | `/types/by-name/{name}`    | Résolution par nom EN ou FR (préfixe, insensible)   |
| GET     | `/types/{id}`              | Type par ID                                         |

### Items

| Méthode | Chemin                     | Description                                         |
| ------- | -------------------------- | --------------------------------------------------- |
| GET     | `/items/`                  | 70 items (fusion/evolution/valuable) — filtre `?category=` |
| GET     | `/items/search?q={nom}`    | Recherche nom EN/FR                                 |
| GET     | `/items/{id}`              | Détail item (effect, price_buy, price_sell)         |

### Fusions

| Méthode | Chemin                                      | Description                                    |
| ------- | ------------------------------------------- | ---------------------------------------------- |
| GET     | `/fusion/{head_id}/{body_id}`               | Stats, types et sprite d'une fusion            |
| GET     | `/fusion/{head_id}/{body_id}/full`          | Stats + moves + expert_moves en une seule requête |
| GET     | `/fusion/{head_id}/{body_id}/moves`         | Moveset combiné head+body, dédupliqué — chaque move inclut `origin: "head"\|"body"\|"both"` |
| GET     | `/fusion/{head_id}/{body_id}/abilities`     | Talents combinés selon règles IF (head slot1 + body slot1 + hiddens) |
| GET     | `/fusion/{head_id}/{body_id}/weaknesses`    | Matchups défensifs de la combinaison de types  |
| GET     | `/fusion/{head_id}/{body_id}/expert-moves`  | Moves enseignables par Move Expert (Knot/Boon Island) + prix en Heart Scales |
| GET     | `/fusion/random`                            | Fusion aléatoire (ORDER BY RANDOM() LIMIT 2)   |
| GET     | `/fusions/involving/{pokemon_id}`           | Toutes les paires où ce Pokémon intervient     |

### Sprites

| Méthode | Chemin                                     | Description                                   |
| ------- | ------------------------------------------ | --------------------------------------------- |
| GET     | `/sprites/by_pokemon/{pokemon_id}`         | Toutes les variantes impliquant ce Pokémon (head ou body) |
| GET     | `/sprites/{head_id}/{body_id}`             | Liste des variantes + crédits (`creators: list[str]`) |
| GET     | `/sprites/{head_id}/{body_id}/image`       | PNG — default ou `?variant_id=N`              |

### Méta

| Méthode | Chemin                              | Description                                    |
| ------- | ----------------------------------- | ---------------------------------------------- |
| GET     | `/generations/`                     | Liste des 9 générations                        |
| GET     | `/generations/{id}`                 | Fiche d'une génération                         |
| GET     | `/generations/{id}/pokemon`         | Pokémon d'une génération                       |
| GET     | `/creators/`                        | Créateurs de sprites (tri par nb décroissant)  |
| GET     | `/creators/{id}`                    | Fiche créateur + compteur                      |
| GET     | `/creators/{id}/sprites`            | Sprites d'un créateur                          |
| GET     | `/triple-fusions/`                  | 23 fusions triples                             |
| GET     | `/triple-fusions/{id}`              | Détail d'une triple-fusion                     |
| GET     | `/triple-fusions/{id}/sprite`       | Sprite PNG de la triple-fusion                 |
| GET     | `/triple-fusions/{id}/weaknesses`   | Matchups défensifs de la triple-fusion         |
| GET     | `/stats/coverage`                   | Audit de complétude DB                         |
| GET     | `/health`                           | Healthcheck (Docker + CI)                      |

### IA agentique

| Méthode | Chemin           | Description                                                                 |
| ------- | ---------------- | --------------------------------------------------------------------------- |
| POST    | `/ai/ask`        | Agent tool-calling — réponse en streaming SSE                               |
| POST    | `/ai/feedback`   | Envoie un retour utilisateur (webhook Discord) — toujours 200, best-effort  |
| GET     | `/ai/provider`   | Provider actif (`{"name": "DeepSeek", "model": "deepseek-chat"}`)           |
| GET     | `/ai/prompt`     | System prompt actif (contenu de `prompts/system.md`) + liste des outils     |

**Payload `/ai/ask`** : `{ "message": "...", "context": "...", "history": [...] }`

- `context` (optionnel) : texte injecté avant la question — utilisé par le bouton "Demander à l'IA" pour passer la sélection courante (ex. *"Fusion de Dracaufeu (tête) et Mewtwo (corps). Types: Fire/Psychic. Total: 600."*)
- `history` (optionnel) : tableau `[{role, content}]` des échanges précédents — tronqué à 10 messages

**Format SSE** — chaque ligne `data: {...}\n\n` contient un événement typé :

```json
{"type": "tool_call", "name": "get_pokemon"}
{"type": "token", "chunk": "Dracaufeu est un Pokémon de type Feu..."}
```

Les événements `tool_call` permettent à l'UI d'afficher les outils invoqués (pastilles ⚙). Les `token` sont accumulés pour le rendu Markdown progressif.

**Fonctionnement de la boucle agent** :

1. Le LLM reçoit la question + `TOOL_SPECS` (9 outils : 7 DB + 1 wiki + 1 web)
2. Il peut invoquer 1+ tools → le backend exécute et renvoie les résultats JSON
3. Boucle jusqu'à réponse textuelle ou MAX_ITERATIONS (5)
4. **Circuit breaker** : si MAX_ITERATIONS atteint → *« Je n'ai pas trouvé cette information. »*
5. **Fail-closed** : réponse vide → même message de refus

**Provider sélectionné à runtime** : `DEEPSEEK_API_KEY` → DeepSeek · `OPENROUTER_API_KEY` → OpenRouter · `OLLAMA_URL` → Ollama · Aucun → `503` avec instructions de setup.

Implémentation : [`backend/services/ai_service.py`](https://github.com/benjsant/InfiniDex/blob/main/backend/services/ai_service.py) (boucle), [`backend/services/tools/`](https://github.com/benjsant/InfiniDex/blob/main/backend/services/tools/) (handlers).

## CORS

Défense en profondeur uniquement — le flux principal passe par le proxy Next.js (même origine).

```python
# backend/main.py
cors_origins = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:53000,http://localhost:58000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
```

En prod, `CORS_ALLOWED_ORIGINS` doit lister uniquement le domaine public.

## Tests

160 tests. Ils nécessitent le dump SQL sous `backend/tests/fixtures/` (committé). Lance via Docker :

```bash
docker compose --profile test run --rm test-backend
```

## Voir aussi

- [Règles de fusion](fusion-rules.md) — sémantique des endpoints `/fusion/*`.
- [Architecture](architecture.md) — flux de requêtes + boucle agent IA.
- [Référence routes](reference/routes.md) — signatures + docstrings auto-générées.
- [Référence schemas](reference/schemas.md) — modèles Pydantic (I/O).
