---
title: Fiche projet — InfiniDex
---

# Fiche projet — InfiniDex

One-pager pour portfolio, pitch recruteur, ou base de README enrichi. Mis à jour au 2026-04-18.

## Pitch en une ligne

Pokédex intelligent pour **Pokémon Infinite Fusion** : pipeline ETL + API REST + frontend bilingue EN/FR + prep IA, entièrement conteneurisé.

## Contexte

Pokémon Infinite Fusion est un fan-game qui permet de fusionner n'importe quel Pokémon avec n'importe quel autre (~176 000 combinaisons). Aucune API officielle ; les données (stats, movepools, fusions, sprites, règles spéciales type Move Experts) sont réparties sur le **Wiki IF**, **PokeAPI** et **Poképédia**.

**InfiniDex** centralise tout ça dans une base PostgreSQL interrogeable, l'expose via une API REST propre et le rend explorable via un frontend Next.js.

## Stack technique

| Couche    | Technos                                              |
| --------- | ---------------------------------------------------- |
| ETL       | Python 3.12 · `uv` · MediaWiki API · PokeAPI         |
| Base      | PostgreSQL 16 (arrays natifs pour contraintes multi-valeurs) |
| Backend   | FastAPI · SQLAlchemy 2 · Pydantic · pytest           |
| Frontend  | Next.js 15 (App Router) · TypeScript · React Server Components |
| IA        | DeepSeek API (prep `/ai/ask`)                        |
| Infra     | Docker Compose (dev + prod override) · nginx sidecar · GitHub Actions |
| Doc       | MkDocs Material (conteneurisée sous profil Compose)  |

## Architecture en une phrase

**5 services Docker** (`db`, `backend`, `sprites`, `frontend`, `docs`) sur réseau interne, **seul le frontend exposé publiquement** ; toutes les requêtes navigateur passent par un proxy Next.js qui masque les URLs backend.

## Chiffres clés

- **572 Pokémon** (501 IF + 71 formes) · **676 moves** · **178 abilities**
- **40 067** entrées de learnset · **166 090** sprites de fusion · **23** fusions triples
- **65 règles Move Experts** (36 Knot Island + 29 Boon Island)
- **7 081** créateurs de sprites crédités
- **30+ endpoints API** · **53 tests pytest verts**

## Décisions techniques notables

1. **`INTEGER[]` Postgres pour les contraintes multi-valeurs (Move Experts).** Évite une table de jonction pour trois axes en OR / superset / intersection. Tableau vide = axe non contraint. Opérateurs `&&` et `<@` font tout le boulot.
2. **Proxy Next.js via route handlers** (`/app/api/[...path]/route.ts`) plutôt que `next.config.ts` rewrites → env lue à runtime, zéro URL backend dans le bundle client, retarget sans rebuild.
3. **CORS defense-in-depth côté FastAPI.** La voie principale passe par le proxy (même origine), CORS durci sert de filet de sécurité pour Swagger / Postman / intégrations tierces.
4. **Convention ports préfixe-5** (`53000/58000/58080/55432/58100`) via env → cohabitation sereine avec d'autres projets locaux.
5. **Override prod `!reset []`** — `docker-compose.prod.yml` retire les ports hôte de db/backend/sprites ; seul frontend est exposé publiquement.
6. **Tout conteneurisé, y compris la doc.** `Dockerfile.docs` + profil Compose `docs` avec volumes live pour le hot-reload.
7. **Parser MediaWiki maison rowspan-aware** pour extraire les Move Experts (tables avec cellules factorisées).
8. **Bidirectional evolution chain** — backend renvoie `pokemon_id ↔ evolves_into_id` dans les deux sens, frontend affiche pré + post évolutions en une chaîne.

## État actuel

- ✅ **ETL** stabilisé — pipeline 12 étapes, scripts `fix_*` idempotents
- ✅ **Backend** — 30+ endpoints, 53 tests pytest
- ✅ **Infra** — Docker dev + prod + CI GitHub Actions (smoke)
- ✅ **Doc** — 9 pages MkDocs Material conteneurisées
- 🚧 **Frontend** — fondations + bugs corrigés ; restent page triple-fusions, galerie sprites, chat IA
- 🚧 **IA DeepSeek** — code en place, validation E2E à faire
- 🚧 **CI full pytest** — nécessite un dump SQL fixture committé sous `backend/tests/fixtures/`

## Roadmap v1.0

- Page triple-fusions + galerie sprites avec crédits créateurs
- Chat IA `/ai/ask` validé bout-à-bout avec DeepSeek
- Dump SQL fixture → full pytest en CI
- Hébergement public (Fly.io / Railway / VPS) + TLS + domaine
- Tests Playwright sur le frontend

## Compétences démontrées

- **Data engineering** : pipeline ETL multi-sources, scraping MediaWiki structuré, normalisation de données, scripts idempotents.
- **Backend** : FastAPI productif (pagination, filtres, sous-endpoints), SQLAlchemy 2, schémas Pydantic, couverture pytest.
- **Modélisation relationnelle** : design des arrays Postgres pour contraintes multi-valeurs, arbres d'évolution bidirectionnels, CASCADE cohérent.
- **Frontend moderne** : Next.js 15 App Router, route handlers runtime, Server Components, TypeScript typé bout-en-bout (schémas backend → frontend).
- **Infra / DevOps** : Docker Compose multi-services avec profils, override prod, conventions ports, CI GitHub Actions, CORS durci, proxy applicatif pour masquer les services internes.
- **DevEx / discipline** : documentation technique structurée (MkDocs 9 pages), conventional commits, `ROADMAP.md` tenu à jour, décisions techniques explicitées.
- **Préparation IA** : intégration LLM externe (DeepSeek), endpoint dédié avec gestion propre de l'absence de clé (503 au lieu de crash).

## Liens

- **Repo** : [github.com/benjsant/InfiniDex](https://github.com/benjsant/InfiniDex)
- **Doc technique** : `docs/` (lancée via `docker compose --profile docs up docs` → `localhost:58100`)
- **Roadmap live** : [`ROADMAP.md`](../roadmap.md)
