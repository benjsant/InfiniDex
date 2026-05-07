"""API routes for Pokémon — list, detail, moveset, evolutions, locations, weaknesses."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.db.models import Pokemon
from backend.db.session import get_db
from backend.routes.deps import get_pokemon_or_404
from backend.schemas.evolution import EvolutionOut
from backend.schemas.location import LocationOut
from backend.schemas.move import PokemonMoveOut
from backend.schemas.pokemon import AbilityOut, PokemonDetail, PokemonListItem, PokemonTypeOut
from backend.schemas.type_ import TypeOut
from backend.schemas.weakness import WeaknessOut
from backend.services.pokemon_service import (
    compute_pokemon_weaknesses,
    get_pokemon_evolutions,
    get_pokemon_locations,
    get_pokemon_moves,
    list_pokemon,
    search_pokemon,
)

router = APIRouter(prefix="/pokemon", tags=["Pokemon"])


def _serialize_types(types_rel) -> list[PokemonTypeOut]:
    return [
        PokemonTypeOut(slot=pt.slot, name_en=pt.type.name_en, name_fr=pt.type.name_fr)
        for pt in sorted(types_rel, key=lambda x: x.slot)
    ]


def _serialize_abilities(abilities_rel) -> list[AbilityOut]:
    return [
        AbilityOut(
            slot=pa.slot,
            is_hidden=pa.is_hidden,
            name_en=pa.ability.name_en,
            name_fr=pa.ability.name_fr,
        )
        for pa in sorted(abilities_rel, key=lambda x: x.slot)
    ]


def pokemon_to_list_item(p: Pokemon) -> PokemonListItem:
    """Serialize a Pokémon to `PokemonListItem` format. Public: reused by `generation_route`."""
    return PokemonListItem(
        id=p.id,
        national_id=p.national_id,
        name_en=p.name_en,
        name_fr=p.name_fr,
        types=_serialize_types(p.types),
        sprite_path=p.sprite_path,
        is_hoenn_only=p.is_hoenn_only,
        pokepedia_url=p.pokepedia_url,
    )


@router.get("/", response_model=list[PokemonListItem])
def get_pokemon_list(
    db: Session = Depends(get_db),
    limit: int | None = Query(None, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    type_id: int | None = Query(None, ge=1, description="Filter by type (id)"),
    generation_id: int | None = Query(None, ge=1, description="Filter by generation"),
    include_hoenn: bool = Query(True, description="Include Hoenn-only Pokémon"),
):
    """List Pokémon in the Infinite Fusion game, with pagination and filters."""
    pokemons = list_pokemon(
        db,
        limit=limit,
        offset=offset,
        type_id=type_id,
        generation_id=generation_id,
        include_hoenn=include_hoenn,
    )
    return [pokemon_to_list_item(p) for p in pokemons]


@router.get("/search", response_model=list[PokemonListItem])
def search_pokemon_route(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """Search by English or French name (accent-insensitive)."""
    return [pokemon_to_list_item(p) for p in search_pokemon(db, q)]


@router.get("/{pokemon_id}", response_model=PokemonDetail)
def get_pokemon(p: Pokemon = Depends(get_pokemon_or_404)):
    """Detailed Pokédex entry for a Pokémon by its IF ID."""
    return PokemonDetail(
        id=p.id,
        national_id=p.national_id,
        name_en=p.name_en,
        name_fr=p.name_fr,
        generation_id=p.generation_id,
        hp=p.hp,
        attack=p.attack,
        defense=p.defense,
        sp_attack=p.sp_attack,
        sp_defense=p.sp_defense,
        speed=p.speed,
        base_experience=p.base_experience,
        is_hoenn_only=p.is_hoenn_only,
        sprite_path=p.sprite_path,
        pokepedia_url=p.pokepedia_url,
        types=_serialize_types(p.types),
        abilities=_serialize_abilities(p.abilities),
    )


@router.get("/{pokemon_id}/moves", response_model=list[PokemonMoveOut])
def get_moves_for_pokemon(
    p: Pokemon = Depends(get_pokemon_or_404),
    db: Session = Depends(get_db),
):
    """Full moveset (level_up, tm, breeding, tutor, before_evolution)."""
    rows = get_pokemon_moves(db, p.id)
    return [
        PokemonMoveOut(
            move_id=r.move_id,
            name_en=r.move.name_en,
            name_fr=r.move.name_fr,
            category=r.move.category,
            power=r.move.power,
            accuracy=r.move.accuracy,
            pp=r.move.pp,
            type=TypeOut(
                id=r.move.type.id,
                name_en=r.move.type.name_en,
                name_fr=r.move.type.name_fr,
                is_triple_fusion_type=r.move.type.is_triple_fusion_type,
            ),
            method=r.method,
            level=r.level,
            source=r.source,
        )
        for r in rows
    ]


@router.get("/{pokemon_id}/evolutions", response_model=list[EvolutionOut])
def get_evolutions_for_pokemon(
    p: Pokemon = Depends(get_pokemon_or_404),
    db: Session = Depends(get_db),
):
    """Evolution chain for a Pokémon."""
    rows = get_pokemon_evolutions(db, p.id)
    return [
        EvolutionOut(
            id=r.id,
            pokemon_id=r.pokemon_id,
            pokemon_name_en=r.pokemon.name_en if r.pokemon else None,
            pokemon_name_fr=r.pokemon.name_fr if r.pokemon else None,
            pokemon_national_id=r.pokemon.national_id if r.pokemon else None,
            evolves_into_id=r.evolves_into_id,
            evolves_into_name_en=r.evolves_into.name_en,
            evolves_into_name_fr=r.evolves_into.name_fr,
            evolves_into_national_id=r.evolves_into.national_id,
            trigger_type=r.trigger_type,
            min_level=r.min_level,
            item_name_en=r.item_name_en,
            item_name_fr=r.item_name_fr,
            if_override=r.if_override,
            if_notes=r.if_notes,
        )
        for r in rows
    ]


@router.get("/{pokemon_id}/locations", response_model=list[LocationOut])
def get_locations_for_pokemon(
    p: Pokemon = Depends(get_pokemon_or_404),
    db: Session = Depends(get_db),
):
    """Encounter locations for a Pokémon (wild, static, legendary…)."""
    rows = get_pokemon_locations(db, p.id)
    return [
        LocationOut(
            location_id=r.location_id,
            location_name=r.location.name_en,
            method=r.method,
            notes=r.notes,
        )
        for r in rows
    ]


@router.get("/{pokemon_id}/weaknesses", response_model=list[WeaknessOut])
def get_weaknesses_for_pokemon(
    p: Pokemon = Depends(get_pokemon_or_404),
    db: Session = Depends(get_db),
):
    """Damage multipliers by attacking type (non-neutral only)."""
    return compute_pokemon_weaknesses(db, p.id) or []
