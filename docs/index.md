# FusionDex-IA

**Pokédex intelligent pour [Pokémon Infinite Fusion](https://infinitefusion.fandom.com/)** — une application complète qui extrait, structure, expose et affiche les données du jeu (572 Pokémon, ~176k fusions, movepools, types, fusions triples, maîtres des capacités, Move Experts…) avec une interface bilingue EN/FR et un assistant IA agentique à 7 outils.

## Vue rapide

| Couche     | Stack                                       | État       |
| ---------- | ------------------------------------------- | ---------- |
| ETL        | Python 3.12 + `uv` + MediaWiki + PokeAPI    | ✅ stable  |
| Base       | PostgreSQL 16 (tables relationnelles + `INTEGER[]`) | ✅ stable |
| Backend    | FastAPI + SQLAlchemy 2 + Pydantic           | ✅ stable  |
| Frontend   | Next.js 15 App Router + TypeScript          | ✅ stable  |
| IA         | Agent tool-calling DeepSeek/Ollama — 8 outils | ✅ stable  |
| Infra      | Docker Compose (dev + prod), Next.js proxy  | ✅ stable  |

## Par où commencer

- **Comprendre l'ensemble** → [Architecture](architecture.md)
- **Schéma et données** → [Base de données](database.md)
- **Lancer le projet localement** → [Développement](development.md)
- **Consommer l'API** → [API backend](api.md)
- **Règles de fusion canoniques** → [Règles de fusion](fusion-rules.md)
- **Référence du code** → [Routes](reference/routes.md) · [Services](reference/services.md) · [Schemas](reference/schemas.md) · [Models](reference/models.md)
- **Ce qu'il reste à faire** → [Roadmap](roadmap.md)

## Sources des données

| Source | Données extraites |
|--------|-------------------|
| [PokeAPI](https://pokeapi.co/) | Stats canoniques, learnsets TM/tutor, national dex IDs |
| [Pokémon Infinite Fusion Wiki](https://infinitefusion.fandom.com/) | Fusions, Move Experts, maîtres des capacités, mécaniques IF |
| [Poképédia](https://www.pokepedia.fr/) | Noms FR |
| Sprites `PokeAPI/sprites` (GitHub) | 572 sprites base |
| Fichiers du jeu (ROM extract) | 166 090 fusion_sprites, 41 move_tutors, 1 634 pokemon_location |

!!! info "Pourquoi FusionDex-IA ?"
    Pokémon Infinite Fusion a une richesse de données éparpillées sur plusieurs wikis, sans API officielle. Ce projet centralise tout dans une base PostgreSQL interrogeable, avec une API REST propre et un frontend pour explorer les ~176k combinaisons de fusion.
