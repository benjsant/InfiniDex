# Services

Couche métier — auto-généré depuis `backend/services/`.

Chaque route FastAPI délègue sa logique DB / calculs à un service. Séparation
stricte : **pas de HTTP dans les services**, **pas de SQLAlchemy dans les routes**.

## Pokémon

::: backend.services.pokemon_service

## Fusion

::: backend.services.fusion_service

## Triple fusion

::: backend.services.triple_fusion_service

## Moves

::: backend.services.move_service

## Abilities

::: backend.services.ability_service

## Types

::: backend.services.type_service

## Générations

::: backend.services.generation_service

## Créateurs

::: backend.services.creator_service

## Sprites

::: backend.services.sprite_service

## Stats d'audit

::: backend.services.stats_service

## IA (DeepSeek)

::: backend.services.ai_service

## Wiki IF (client MediaWiki)

::: backend.services.wiki_service

## Outils agent IA

::: backend.services.tools.db_tools

::: backend.services.tools.wiki_tool
