# API backend

FastAPI exposant 40 endpoints (+ `/health`). Swagger interactif en dev : [http://localhost:58000/docs](http://localhost:58000/docs). Référence auto-générée : [Routes](reference/routes.md).

En prod le backend n'est **pas** exposé publiquement — les requêtes passent par le proxy Next.js (`/api/*` sur le domaine public).

## Organisation

```
backend/
  main.py                 # wiring FastAPI + CORS
  routes/                 # endpoints HTTP (une file par domaine)
  services/               # logique métier + accès DB
  schemas/                # Pydantic — contrat I/O
  db/
    models/               # SQLAlchemy
    base.py               # engine + session
  tests/                  # pytest + TestClient (53 tests verts)
```

Chaque `route` importe son `service`, qui importe ses `models` et `schemas`. Les routes ne touchent jamais directement SQLAlchemy.

## Endpoints principaux

### Pokémon

| Méthode | Chemin                                          | Description                               |
| ------- | ----------------------------------------------- | ----------------------------------------- |
| GET     | `/pokemon/`                                     | Liste paginée + filtres type/gen/Hoenn    |
| GET     | `/pokemon/search?q={nom}`                       | Recherche par nom EN ou FR (ilike)        |
| GET     | `/pokemon/{id}`                                 | Fiche complète (types, talents, stats)    |
| GET     | `/pokemon/{id}/moves`                           | Learnset (level-up + TM + tutor + egg)    |
| GET     | `/pokemon/{id}/evolutions`                      | Chaîne pre + post (bidirectionnelle)      |
| GET     | `/pokemon/{id}/locations`                       | Zones de capture                          |
| GET     | `/pokemon/{id}/weaknesses`                      | Matchups défensifs                        |

### Moves

| Méthode | Chemin                               | Description                                        |
| ------- | ------------------------------------ | -------------------------------------------------- |
| GET     | `/moves/`                            | Liste + filtres (category, type_id, power_min/max) |
| GET     | `/moves/search?q={nom}`              | Recherche nom EN/FR (accent-insensitive)           |
| GET     | `/moves/by-type/{type_name}`         | Capacités d'un type (EN ou FR)                     |
| GET     | `/moves/{id}`                        | Détail complet + descriptions + TM info (si le move est un TM) |
| GET     | `/moves/{id}/tutors`                 | NPCs enseignant ce move (prix + localisation)      |

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
| GET     | `/fusion/{head_id}/{body_id}`               | Calcul de la fusion (stats, types, moves…)     |
| GET     | `/fusion/{head_id}/{body_id}/moves`         | Learnset de la fusion                          |
| GET     | `/fusion/{head_id}/{body_id}/abilities`     | Talents combinés                               |
| GET     | `/fusion/{head_id}/{body_id}/weaknesses`    | Matchups défensifs                             |
| GET     | `/fusion/{head_id}/{body_id}/expert-moves`  | Moves débloqués par les Move Experts (+ prix Heart Scales par location) |
| GET     | `/fusion/random`                            | Fusion aléatoire                               |
| GET     | `/fusions/involving/{pokemon_id}`           | Toutes les paires où ce Pokémon intervient     |

### Sprites

| Méthode | Chemin                                     | Description                                   |
| ------- | ------------------------------------------ | --------------------------------------------- |
| GET     | `/sprites/{head_id}/{body_id}`             | Liste des variantes + crédits                 |
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
| GET     | `/stats/coverage`                   | Audit de complétude DB                         |
| GET     | `/health`                           | Healthcheck (Docker + CI)                      |

### IA agentique (DeepSeek ou Ollama)

| Méthode | Chemin      | Description                                                                 |
| ------- | ----------- | --------------------------------------------------------------------------- |
| POST    | `/ai/ask`   | Agent tool-calling — streaming SSE. Provider sélectionné runtime (DeepSeek si `DEEPSEEK_API_KEY`, sinon Ollama si `OLLAMA_URL`, sinon `503` avec instructions de setup). |

Payload : `{ "message": "...", "context": "..." }` (context optionnel pour injecter la sélection courante — ex. *"Pokémon Dracaufeu id=6, fusion avec Mewtwo id=150"*).

**Fonctionnement** (Phase 1 de la roadmap IA) :

1. Le LLM reçoit la question + la liste des 5 tools BDD (`get_pokemon`, `get_fusion`, `search_move`, `get_item`, `get_move_tutors`)
2. Il peut choisir d'appeler 1+ tools → le backend exécute et renvoie les résultats
3. Boucle jusqu'à ce que le LLM rende une réponse textuelle
4. **Circuit breaker** : max 5 itérations, sinon *« Je n'ai pas trouvé cette information. »*
5. **Fail-closed** : si la réponse finale est vide, même message de refus
6. Le streaming SSE ne concerne que la réponse finale (les tool calls restent internes)

Les specs des tools sont dans [backend/services/ai_tools.py](https://github.com/benjsant/FusionDex-IA/blob/main/backend/services/ai_tools.py) et la boucle dans [backend/services/ai_service.py](https://github.com/benjsant/FusionDex-IA/blob/main/backend/services/ai_service.py).

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

53 tests pytest + `TestClient`. Ils nécessitent un dump SQL sous `backend/tests/fixtures/` (actuellement non committé — seul `test_ai.py` tourne en CI).

```bash
cd backend
uv run pytest
```

## Voir aussi

- [Règles de fusion](fusion-rules.md) — sémantique des endpoints `/fusion/*`.
- [Architecture](architecture.md) — flux de requêtes.
- [Référence routes](reference/routes.md) — signatures + docstrings auto-générées.
- [Référence schemas](reference/schemas.md) — modèles Pydantic (I/O).
