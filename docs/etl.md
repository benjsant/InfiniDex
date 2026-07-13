# Pipeline ETL

Le pipeline ETL extrait les données depuis plusieurs sources externes, les transforme, puis les charge dans PostgreSQL. Il tourne en **mode one-shot** via `pipeline.py` (Prefect disponible sous le profil `prefect`).

## Sources

| Source                            | Utilisée pour                                                   |
| --------------------------------- | --------------------------------------------------------------- |
| **PokeAPI** (REST)                | Stats de base, national dex IDs, learnsets TM/tutor             |
| **Wiki IF - pages spécifiques**   | Fusions, Move Experts, légendaires, tuteurs, mécaniques IF      |
| **Wiki IF - sous-pages Pokédex**  | 572 entrées `PokedexTable` + localisations (voir note ci-dessous) |
| **Poképédia** (MediaWiki + Scrapy)| Noms FR, learnsets Gen 7 (USUL)                                 |
| **GitHub PokeAPI/sprites**        | Sprites PNG statiques                                           |

## Stack

- Python 3.12 + [`uv`](https://github.com/astral-sh/uv) (lockfile + venv)
- `httpx` pour l'HTTP, `psycopg2-binary` + `sqlalchemy` pour la DB
- Parsers maison (wikitext) dans `etl/utils/wikitext.py`
- Scrapy pour les learnsets Pokepédia (projet `etl/pokepedia_scraper/`)

## Séquence d'exécution

L'orchestrateur [etl/pipeline.py](https://github.com/benjsant/InfiniDex/blob/main/etl/pipeline.py) enchaîne 38 étapes numérotées (résumées par groupes ci-dessous) :

| Étape | Script | Rôle |
|-------|--------|------|
| 1 | `extract_pokedex_if.py` | 572 Pokémon depuis le wiki IF (sous-pages `Pokédex/Hoenn/Classic` + `Pokédex/Kanto/Classic`) |
| 2a | `extract_stats_pokeapi.py` | Stats + name_fr + évolutions via PokeAPI |
| 2b | `extract_pokepedia_names.py` | Mapping name_en → slug Pokepédia + URL Gen 7 |
| 3 | `extract_moves_if.py` | 658 moves + 121 TMs + 40 tuteurs + 57 Move Experts |
| 3b | `enrich_moves_fr.py` | name_fr + description_fr des moves via PokeAPI |
| 4 | `extract_abilities_if.py` | 183 talents depuis le wiki IF |
| 4b | `enrich_abilities_fr.py` | name_fr + description_fr des talents via PokeAPI |
| 5 | `extract_encounters_if.py` | Rencontres sauvages/statiques/légendaires |
| 6 | `scrapy if_movesets` | Learnsets Gen 7 depuis Pokepédia (USUL) |
| 7 | `transform_merge_movesets.py` | Fusion learnsets de base + overrides IF |
| 8 | `load_db.py` | Chargement de tout dans PostgreSQL |
| 8b–8f | `fix_pokemon_types.py` `fix_national_ids.py` `fix_stats_and_fr_names.py` `fix_evolutions.py` `fix_tms_from_pokeapi.py` `enrich_evolution_movesets.py` | Correctifs canoniques post-import (re-sync stats/types/évolutions une fois les `national_id` corrigés) |
| 9–9g | `seed_type_effectiveness.py` `load_encounters.py` `fix_pokemon_locations.py` `load_pokedex_locations.py` `load_locations_snapshot.py` `load_items.py` `load_move_tutors.py` `fix_tutors_from_pokeapi.py` `load_tm_locations.py` `fix_move_experts.py` | Enrichissements et localisations |
| 10–12 | `extract_sprites.py` `extract_triple_fusions.py` `load_triple_fusions.py` `load_sprite_credits.py` | Sprites, triple fusions, crédits |
| 13–14 | `clean_orphan_moves.py` `enrich_missing_abilities.py` | Nettoyage et complétion |

!!! note "Étape 9b-ter - `load_pokedex_locations.py`"
    Parse la sous-page `Pokédex/Hoenn/Classic` du wiki IF (`{{PokedexTable/Data|...}}`) pour extraire les localisations sauvages et quêtes manquantes. Utilise `ON CONFLICT DO NOTHING` - ne réécrit jamais les données prioritaires de `fix_pokemon_locations.py`. Gère le `|` dans les liens wiki (`[[Page|Display]]`) en reconstruisant le champ depuis `parts[6:]`.

!!! warning "Restructuration du wiki (2026-07)"
    La page `Pokédex` du wiki IF est devenue un hub sans données : les 572 entrées vivent dans `Pokédex/Hoenn/Classic`, le template a gagné un champ `form` en 4e position, et les marqueurs "Not in game" ont disparu (le flag `is_hoenn_only` est désormais dérivé de la différence Kanto/Hoenn). La restructuration a aussi remis la plupart des champs Location à `TBA` (436/572) - `load_pokedex_locations.py` ne récupère plus que ~7 tuples contre ~2 448 avant. L'étape 9b-quater (`load_locations_snapshot.py`) rejoue un snapshot committé de la table pré-restructuration (`etl/data/snapshots/pokemon_location_snapshot.json`, dump du 2026-07-13) en `ON CONFLICT DO NOTHING` : les données wiki vivantes gagnent toujours, le snapshot ne fait que combler les trous. Les deux scripts qui lisent cette page échouent désormais bruyamment s'ils parsent 0 entrée.

!!! note "Étape 8e-ter - `fix_evolutions.py`"
    Re-fetch les chaînes d'évolution PokeAPI une fois les `national_id` corrigés par `fix_national_ids.py`. Nécessaire parce que `extract_stats_pokeapi.py` interroge PokeAPI par `if_id` (qui ne correspond au `national_id` que pour les 151 Kanto purs) - pour les 320 Pokémon post-Kanto, la chaîne récupérée appartient à la mauvaise espèce et n'est jamais ré-extraite sans ce script. Résolution slug-aware (`pokeapi_move_slug`) pour matcher correctement les noms à caractères spéciaux (`Mime Jr.` ↔ `mime-jr`, `Nidoran♀` ↔ `nidoran-f`, `Flabébé` ↔ `flabebe`). Idempotent.

## Diagramme de pipeline

```mermaid
flowchart TD
    subgraph SRC["Sources externes"]
        PA[PokeAPI\nREST JSON]
        WI[Wiki IF\nMediaWiki API]
        PK[Pokepédia\nMediaWiki API]
        GH[PokeAPI/sprites\nGitHub]
    end

    subgraph ETL["ETL - etl/scripts/"]
        direction TB
        S1[1. init_postgres.sql\ncréation des tables]
        S2[2. types + générations]
        S3[3. pokedex_if → 572 Pokémon]
        S4[4. abilities + pokemon_ability]
        S5[5. moves + learnsets\n45 100 pokemon_move]
        S6[6. évolutions]
        S7[7. fusion_sprite\n168 k lignes + créateurs]
        S8[8. triple_fusions]
        S9[9. locations + pokemon_location]
        S10[10. TMs + tm_location]
        S11[11. move_tutors + move_experts]
        FX[fix_*.py\ncorrectifs canoniques]
        AU[audit_db.py\nvérification cohérence]

        S1 --> S2 --> S3 --> S4 --> S5 --> S6
        S6 --> S7 --> S8 --> S9 --> S10 --> S11 --> FX --> AU
    end

    subgraph DB[(PostgreSQL 16)]
        T1[pokemon · move\nability · type]
        T2[fusion_sprite\n168 k sprites]
        T3[move_expert_move\npokemon_location]
    end

    PA -->|stats · national_id\nlearnsets · abilities| S3
    PA -->|TMs · tuteurs| S10
    WI -->|Move Experts\nfusions spéciales| S11
    PK -->|noms FR| FX
    GH -->|sprites PNG\n→ nginx sidecar| S7
    ETL --> DB

    style SRC fill:#1e2d40,color:#93c5fd
    style ETL fill:#1e3b2f,color:#6ee7b7
    style DB  fill:#2d1e3b,color:#c4b5fd
```

## Lancer le pipeline

```bash
# Via Docker (recommandé)
docker compose run --rm etl

# Ou localement
cd etl && uv sync && uv run python etl/pipeline.py
```

!!! warning "Requiert la DB up"
    Le pipeline attend PostgreSQL via `docker/wait_for_db.py`. Lance d'abord `docker compose up -d db` si tu pars de zéro.

Pour forcer une réexécution complète (même si les données sont déjà chargées) :

```bash
docker compose run --rm etl python etl/pipeline.py --force
```

!!! warning "Recrée le backend après un rebuild"
    Le backend warm `_pokemon_cache` / `_fusion_cache` **au démarrage**.
    Après un re-run ETL (surtout `--force`), recrée-le pour qu'il recharge
    depuis la base reconstruite - sinon il sert des données périmées
    silencieusement :
    ```bash
    docker compose up backend -d --force-recreate
    ```

## Patterns récurrents

### Cache de requêtes wiki

Les pages MediaWiki sont longues à fetch. Chaque script met en cache le wikitext brut sous `etl/data/cache/` pour éviter de requêter à chaque relance.

### Normalisation de noms

Les sources divergent sur quelques noms (ex : wiki IF écrit *Flaafy* au lieu de *Flaaffy*). Chaque parseur expose un dictionnaire d'alias + une fonction `norm()` qui strip espaces, `-`, `'`, `.` et lowercase pour matcher contre la DB.

```python
WIKI_POKEMON_ALIASES = {"flaafy": "flaaffy"}

def norm_pokemon(name: str) -> str:
    n = norm(name)
    return WIKI_POKEMON_ALIASES.get(n, n)
```

### Parsing de tables avec rowspan

Les Move Experts et plusieurs autres pages wiki utilisent `rowspan` pour factoriser les cellules partagées entre plusieurs lignes. Le parseur maison reconstruit la matrice complète avant d'extraire les données.

### Idempotence

Les scripts `fix_*.py` sont réexécutables : ils font du `UPSERT` (SQL `ON CONFLICT DO UPDATE`) ou un `DELETE` + `INSERT` pour les tables dont ils sont seuls responsables (`move_expert_move`).

## Voir aussi

- [Base de données](database.md) - schéma cible.
- [Roadmap](roadmap.md) - audit DB et mega-évolutions restent à traiter.
