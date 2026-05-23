# InfiniDex — Plan d'action complet

## Sources de données

| Données | Source | Méthode |
|---|---|---|
| Liste 501 Pokémon + localisations | Wiki IF (MediaWiki API) | API |
| Stats base (HP/Atk/Def/SpAtk/SpDef/Vit) | PokeAPI | API |
| 644 moves avec stats complètes | Wiki IF (List of Moves) | API |
| 121 CTs IF + localisation | Wiki IF (List of TMs) | API |
| 47+ tuteurs | Wiki IF (List of Tutors) | API |
| ~289 capacités spéciales | Wiki IF (List of Abilities) | API |
| Localisations statiques | Wiki IF (List of Static Encounters) | API |
| Qui apprend quoi + méthode (niveau/CT/repro/tuteur) | Pokepedia | Scraping |
| Overrides méthodes IF (ex: CT Aqua Jet) | Wiki IF TMs + Tutors | API |
| Formules de fusion | Wiki IF (Fusion FAQs) | Connu (voir bas) |
| Sprites base | Dossier local du jeu | Volume Docker |
| Sprites fusion custom | Dossier CustomBattlers/ du jeu | Volume Docker |

### Formules de fusion (Fusion FAQs)

```
Stats physiques (Atk, Déf, Vit)   = floor((Body × 2/3) + (Head × 1/3))
Stats spéciales (PV, SpAtk, SpDéf) = floor((Head × 2/3) + (Body × 1/3))

Type1 = type primaire du Head
Type2 = type secondaire du Body (ou type primaire du Body si pas de type2)

Capacités spéciales = choix parmi les capacités des deux parents
Moves              = Move Teacher peut enseigner les moves des deux parents
```

### Convention de nommage des sprites de fusion

```
CustomBattlers/{head_id}.{body_id}.png
Exemple : 25.6.png = Pikachu (head) fusionné avec Charizard (body)
```

---

## Phase 1 — Fondations de données (ETL + DB)

### 1.1 Refonte du schéma PostgreSQL

**19 tables** réparties en 6 blocs (ordre de création respectant les FK) :

```
BLOC 1 — Référentiels
  generation          ← Gen 1, Gen 2, Gen 3…
  type                ← 27 types (18 officiels + 9 triple-fusion)
  ability             ← ~289 capacités spéciales (EN/FR)

BLOC 2 — Moves
  move                ← 644 moves du jeu IF (EN/FR, puissance, précision, PP)
  tm                  ← 121 CTs IF avec numéro et localisation

BLOC 3 — Pokémon de base
  pokemon             ← 501 Pokémon : IF ID + national_id (≠ parfois), stats, bilingue
  pokemon_type        ← types par Pokémon (slot 1-2) + flag if_override
  pokemon_ability     ← talents par Pokémon (slot 1-3) + flags if_swapped / if_override
  pokemon_evolution   ← évolutions officielles (PokeAPI) + overrides IF (~40 cas)
                        plusieurs lignes possibles par évolution (conditions alternatives)

BLOC 4 — Localisations et movesets
  location            ← zones du jeu IF (EN/FR, région)
  pokemon_location    ← où trouver chaque Pokémon (méthode : wild/gift/trade/static…)
  pokemon_move        ← moveset complet (méthode + source base/infinite_fusion)

BLOC 5 — Triple Fusions
  triple_fusion           ← 23 Pokémon triple fusion (stats propres, chaîne évolution)
  triple_fusion_type      ← jusqu'à 4 types par triple fusion
  triple_fusion_component ← les 3 Pokémon de base qui la composent
  triple_fusion_ability   ← talents de chaque triple fusion

BLOC 6 — Sprites
  creator               ← artistes de sprites custom
  fusion_sprite         ← sprites double fusion (head_id.body_id.png), multi-sprites par paire
  fusion_sprite_creator ← jonction sprite ↔ artiste (N-N)
```

**Points clés du schéma :**
- `pokemon.id` = IF ID (pour les sprites), `pokemon.national_id` = Pokédex national (PokeAPI)
- `pokemon_evolution` : plusieurs lignes par évolution pour les conditions alternatives (ex: Kadabra → Niv.40 OU Corde de Liaison)
- `pokemon_ability.if_swapped` : ~15 Pokémon dont les slots 1/2 sont échangés dans IF
- `pokemon_ability.if_override` : ex. Gengar a Lévitation au lieu de Corps Maudit
- `pokemon_type.if_override` : ex. Scizor dont les types sont inversés dans IF
- Types triple-fusion marqués `is_triple_fusion_type = TRUE`

### 1.2 Pipeline ETL (8 étapes)

**Étape 1 — extract_pokedex_if.py**
- Source : Wiki IF MediaWiki (page `Pokédex`)
- Données : ID, Nom, Type1, Type2, Génération, Localisation brute, flag Hoenn-only
- Sortie : `data/pokedex_if.json`

**Étape 2 — extract_stats_pokeapi.py**
- Source : PokeAPI (`/pokemon/{id}`)
- Données : HP, Atk, Def, SpAtk, SpDef, Vit pour chaque Pokémon de la liste IF
- Sortie : `data/pokemon_stats.json`

**Étape 3 — extract_moves_if.py**
- Source : Wiki IF (`List of Moves`, `List of TMs`, `List of Tutors`)
- Données : 644 moves complets (puissance/précision/PP) + 121 CTs + tuteurs
- Sortie : `data/moves_if.json`, `data/tms_if.json`, `data/tutors_if.json`

**Étape 4 — extract_abilities_if.py**
- Source : Wiki IF (`List of Abilities`)
- Données : nom, description, Pokémon associés (capacité normale + cachée)
- Sortie : `data/abilities_if.json`

**Étape 5 — extract_locations_if.py**
- Source : Wiki IF (`List of Static Encounters`, `List of Gift Pokémon and Trades`)
- Données : localisations par Pokémon dans le jeu
- Sortie : `data/locations_if.json`

**Étape 6 — extract_movesets_pokepedia.py** *(scraping)*
- Source : Pokepedia (page de chaque Pokémon)
- Données : qui apprend quoi + par quelle méthode (niveau / CT / reproduction / tuteur)
- Sortie : `data/movesets_base.json`

**Étape 7 — transform_merge_movesets.py** *(logique métier critique)*
- Merge `movesets_base.json` + `tms_if.json` + `tutors_if.json`
- Règle A : si IF ajoute une CT pour un move déjà appris autrement → conserver les deux méthodes
- Règle B : si un move est IF-only (pas dans Pokepedia Gen 1-7) → source = `infinite_fusion`
- Règle C : si un move est supprimé dans IF → à marquer ou ignorer
- Sortie : `data/movesets_merged.json`

**Étape 8 — load_db.py**
- Charge toutes les données dans PostgreSQL dans le bon ordre (FK)
- Idempotent : `ON CONFLICT (id) DO NOTHING` ou `DO UPDATE` selon la table

---

## Phase 2 — API Backend (FastAPI)

### Endpoints Pokémon

```
GET /pokemon                      ← liste avec filtres (type, gen, name)
GET /pokemon/{id}                 ← fiche complète
GET /pokemon/{id}/moves           ← moveset complet avec méthodes d'apprentissage
GET /pokemon/{id}/locations       ← où trouver dans le jeu
GET /pokemon/{id}/abilities       ← capacités spéciales
GET /search?q=                    ← recherche textuelle partielle
```

### Endpoints Moves

```
GET /moves                        ← liste avec filtres (type, catégorie, puissance)
GET /moves/{id}                   ← détail complet
GET /moves/{id}/pokemon           ← quels Pokémon apprennent ce move
```

### Endpoints Fusions (Phase 3)

```
GET /fusion/{head_id}/{body_id}         ← stats calculées à la volée
GET /fusion/{head_id}/{body_id}/sprite  ← URL du sprite
```

### Endpoint IA DeepSeek

```
POST /ai/ask
Body : { "question": "Pokémon feu rapide avec Flamboyance" }
Retour : { "results": [...], "explanation": "..." }
```

---

## Phase 3 — Sprites

### Court terme (maintenant)
- Volume Docker monté sur le backend FastAPI
- Servir en fichiers statiques
- `GET /sprites/base/{id}.png`
- `GET /sprites/fusion/{head_id}.{body_id}.png`

### Long terme (production)
- Ajouter service MinIO dans docker-compose (S3 self-hosted, gratuit)
- Script migration : PNG → WebP + upload MinIO (inspiré de Pokinder)
- Remplacement facile par S3/Cloudflare R2 en prod

---

## Phase 4 — Frontend (Next.js)

```
/                    ← accueil + barre de recherche globale
/pokemon             ← liste avec filtres (type, gen)
/pokemon/[id]        ← fiche Pokémon (stats, types, moves, localisations)
/fusion/[a]/[b]      ← fiche fusion (stats calculées + sprite)
/moves               ← liste des moves avec filtres
/ai                  ← interface de recherche IA (DeepSeek)
```

---

## Phase 5 — Intégration IA (DeepSeek)

### Architecture

```
User → POST /ai/ask
     → Contexte : schéma DB simplifié + exemples
     → DeepSeek API (deepseek-chat, compatible OpenAI)
     → Réponse : filtres JSON ou requête SQL + explication
     → Exécution + retour résultats
```

### Cas d'usage prioritaires
1. Recherche par description : *"pokémon rapide de type feu avec bonne attaque spéciale"*
2. Questions sur les moves : *"quels pokémon apprennent Tranche par CT ?"*
3. Conseil de fusion : *"quelle fusion donne le meilleur SpAtk de type Eau ?"*
4. Questions encyclopédiques : *"décris l'effet de la capacité Multitype"*

---

## Ordre d'exécution recommandé

```
Étape 1  → Refonte schéma DB (toutes les tables)
Étape 2  → ETL étapes 1-5 (wiki IF + PokeAPI, sans Pokepedia)
Étape 3  → ETL étape 6 (Pokepedia scraping)
Étape 4  → ETL étape 7-8 (merge + load DB)
Étape 5  → API endpoints Pokémon + Moves
Étape 6  → Sprites (static files Docker)
Étape 7  → Endpoints Fusions (calcul à la volée)
Étape 8  → Intégration DeepSeek (/ai/ask)
Étape 9  → Frontend Next.js
Étape 10 → MinIO sprites (optionnel, pour la prod)
```

---

## Ce qui ne change pas (claude.md)

- Pas de ML / XGBoost / MLflow
- Pas de Prometheus / Grafana
- Pas de prédiction de combat
- Pas de système de fusion complet dès le début
- Stack strict : FastAPI + PostgreSQL + Next.js + uv
