from backend.db.models.generation import Generation
from backend.db.models.type_ import Type
from backend.db.models.type_effectiveness import TypeEffectiveness
from backend.db.models.ability import Ability
from backend.db.models.move import Move
from backend.db.models.tm import TM, TMLocation
from backend.db.models.location import Location
from backend.db.models.pokemon import Pokemon
from backend.db.models.pokemon_type import PokemonType
from backend.db.models.pokemon_ability import PokemonAbility
from backend.db.models.pokemon_evolution import PokemonEvolution
from backend.db.models.pokemon_location import PokemonLocation
from backend.db.models.pokemon_move import PokemonMove
from backend.db.models.triple_fusion import (
    TripleFusion,
    TripleFusionType,
    TripleFusionComponent,
    TripleFusionAbility,
)
from backend.db.models.creator import Creator
from backend.db.models.fusion_sprite import FusionSprite, FusionSpriteCreator
from backend.db.models.move_expert_move import MoveExpertMove
from backend.db.models.move_tutor import MoveTutor
from backend.db.models.item import Item, ItemLocation

__all__ = [
    "Generation",
    "Type",
    "TypeEffectiveness",
    "Ability",
    "Move",
    "TM",
    "TMLocation",
    "Location",
    "Pokemon",
    "PokemonType",
    "PokemonAbility",
    "PokemonEvolution",
    "PokemonLocation",
    "PokemonMove",
    "TripleFusion",
    "TripleFusionType",
    "TripleFusionComponent",
    "TripleFusionAbility",
    "Creator",
    "FusionSprite",
    "FusionSpriteCreator",
    "MoveExpertMove",
    "MoveTutor",
    "Item",
    "ItemLocation",
]
