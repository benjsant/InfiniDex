"""Service layer for Pokémon — list/detail queries + sub-aspects (moves,
evolutions, locations, weaknesses)."""

from sqlalchemy.orm import Session, joinedload

from backend.db.models import Pokemon, PokemonAbility, PokemonEvolution, PokemonLocation, PokemonType
from backend.services.type_effectiveness import compute_weaknesses_for
from backend.utils.text import ilike_escape


_BST = (
    Pokemon.hp + Pokemon.attack + Pokemon.defense
    + Pokemon.sp_attack + Pokemon.sp_defense + Pokemon.speed
)


def _base_query(
    db: Session,
    *,
    type_id: int | None = None,
    type2_id: int | None = None,
    generation_id: int | None = None,
    include_hoenn: bool = True,
    min_bst: int | None = None,
    max_bst: int | None = None,
    ability_id: int | None = None,
):
    """Shared filter logic for list and count queries."""
    query = db.query(Pokemon)
    if type_id is not None:
        sub = db.query(PokemonType.pokemon_id).filter(PokemonType.type_id == type_id)
        query = query.filter(Pokemon.id.in_(sub))
    if type2_id is not None:
        sub = db.query(PokemonType.pokemon_id).filter(PokemonType.type_id == type2_id)
        query = query.filter(Pokemon.id.in_(sub))
    if ability_id is not None:
        sub = db.query(PokemonAbility.pokemon_id).filter(PokemonAbility.ability_id == ability_id)
        query = query.filter(Pokemon.id.in_(sub))
    if generation_id is not None:
        query = query.filter(Pokemon.generation_id == generation_id)
    if not include_hoenn:
        query = query.filter(Pokemon.is_hoenn_only.is_(False))
    if min_bst is not None:
        query = query.filter(_BST >= min_bst)
    if max_bst is not None:
        query = query.filter(_BST <= max_bst)
    return query


_STAT_COLS = {
    "hp":         Pokemon.hp,
    "attack":     Pokemon.attack,
    "defense":    Pokemon.defense,
    "sp_attack":  Pokemon.sp_attack,
    "sp_defense": Pokemon.sp_defense,
    "speed":      Pokemon.speed,
}


def count_pokemon(
    db: Session,
    *,
    type_id: int | None = None,
    type2_id: int | None = None,
    generation_id: int | None = None,
    include_hoenn: bool = True,
    min_bst: int | None = None,
    max_bst: int | None = None,
    ability_id: int | None = None,
) -> int:
    """Count Pokémon matching the given filters (no pagination)."""
    return _base_query(db, type_id=type_id, type2_id=type2_id, generation_id=generation_id,
                       include_hoenn=include_hoenn, min_bst=min_bst, max_bst=max_bst,
                       ability_id=ability_id).count()


def list_pokemon(
    db: Session,
    *,
    limit: int | None = None,
    offset: int = 0,
    type_id: int | None = None,
    type2_id: int | None = None,
    generation_id: int | None = None,
    include_hoenn: bool = True,
    min_bst: int | None = None,
    max_bst: int | None = None,
    sort_by: str = "id",
    ability_id: int | None = None,
) -> list[Pokemon]:
    """Paginated list of Pokémon with type / generation / Hoenn-only / BST / ability filters."""
    query = _base_query(db, type_id=type_id, type2_id=type2_id, generation_id=generation_id,
                        include_hoenn=include_hoenn, min_bst=min_bst, max_bst=max_bst,
                        ability_id=ability_id)
    query = query.options(joinedload(Pokemon.types))
    if sort_by == "bst_asc":
        query = query.order_by(_BST.asc(), Pokemon.id)
    elif sort_by == "bst_desc":
        query = query.order_by(_BST.desc(), Pokemon.id)
    elif sort_by == "name_asc":
        query = query.order_by(Pokemon.name_fr.asc().nullsfirst(), Pokemon.name_en.asc())
    elif sort_by == "name_desc":
        query = query.order_by(Pokemon.name_fr.desc().nullslast(), Pokemon.name_en.desc())
    elif sort_by.endswith("_asc") and sort_by[:-4] in _STAT_COLS:
        col = _STAT_COLS[sort_by[:-4]]
        query = query.order_by(col.asc(), Pokemon.id)
    elif sort_by.endswith("_desc") and sort_by[:-5] in _STAT_COLS:
        col = _STAT_COLS[sort_by[:-5]]
        query = query.order_by(col.desc(), Pokemon.id)
    elif sort_by == "id_desc":
        query = query.order_by(Pokemon.id.desc())
    else:
        query = query.order_by(Pokemon.id)
    query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def get_pokemon_by_id(db: Session, pokemon_id: int) -> Pokemon | None:
    """Load a Pokémon by ID with its types and abilities eagerly loaded."""
    return (
        db.query(Pokemon)
        .options(
            joinedload(Pokemon.types),
            joinedload(Pokemon.abilities),
        )
        .filter(Pokemon.id == pokemon_id)
        .first()
    )


def search_pokemon(db: Session, name: str) -> list[Pokemon]:
    """Search Pokémon by EN or FR name (ilike, case-insensitive)."""
    return (
        db.query(Pokemon)
        .options(joinedload(Pokemon.types))
        .filter(
            Pokemon.name_en.ilike(f"%{ilike_escape(name)}%", escape="\\")
            | Pokemon.name_fr.ilike(f"%{ilike_escape(name)}%", escape="\\")
        )
        .order_by(Pokemon.id)
        .all()
    )


def compute_pokemon_weaknesses(db: Session, pokemon_id: int, pokemon: Pokemon | None = None) -> list[dict] | None:
    """Damage multipliers for every attacking type against this Pokémon.

    For dual-type Pokémon the multipliers are compounded:
      e.g. Grass/Flying vs Fire → 0.5 × 2.0 = 1.0 (neutral, excluded).

    Pass `pokemon` when already loaded to avoid a redundant DB query.
    """
    if pokemon is None:
        pokemon = db.query(Pokemon).filter(Pokemon.id == pokemon_id).first()
    if not pokemon:
        return None
    return compute_weaknesses_for(db, [pt.type_id for pt in pokemon.types])


def get_pokemon_evolutions(db: Session, pokemon_id: int) -> list[PokemonEvolution]:
    """Return all evolution links in the same chain as pokemon_id.

    Walks the chain iteratively (covers baby→stage1→stage2 in 2 passes)
    so that calling /pokemon/1/evolutions returns both Bulbasaur→Ivysaur
    and Ivysaur→Venusaur, not just the single direct link.
    """
    chain_ids: set[int] = {pokemon_id}
    for _ in range(4):  # max depth guard — deepest IF chain is ≤3 stages
        rows = (
            db.query(PokemonEvolution)
            .filter(
                PokemonEvolution.pokemon_id.in_(chain_ids)
                | PokemonEvolution.evolves_into_id.in_(chain_ids)
            )
            .all()
        )
        expanded = {e.pokemon_id for e in rows} | {e.evolves_into_id for e in rows}
        if expanded == chain_ids:
            break
        chain_ids = expanded

    return (
        db.query(PokemonEvolution)
        .options(
            joinedload(PokemonEvolution.evolves_into),
            joinedload(PokemonEvolution.pokemon),
        )
        .filter(PokemonEvolution.pokemon_id.in_(chain_ids))
        .all()
    )


def get_pokemon_locations(db: Session, pokemon_id: int) -> list[PokemonLocation]:
    """Encounter locations for a Pokémon, with location name eagerly loaded."""
    from backend.db.models import Location  # noqa: PLC0415
    return (
        db.query(PokemonLocation)
        .options(joinedload(PokemonLocation.location))
        .filter(PokemonLocation.pokemon_id == pokemon_id)
        .order_by(PokemonLocation.method)
        .all()
    )


def search_pokemon_locations(
    db: Session,
    condition: str | None = None,
    method: str | None = None,
) -> list[PokemonLocation]:
    """Bulk search of pokemon_location rows by method and/or notes keyword.

    condition: keyword searched case-insensitively in the notes field
               (e.g. "Legendary", "Starter", "Gift").
    method:    encounter method filter (wild | gift | trade | static | fishing).
    """
    query = (
        db.query(PokemonLocation)
        .options(
            joinedload(PokemonLocation.pokemon),
            joinedload(PokemonLocation.location),
        )
        .join(Pokemon, Pokemon.id == PokemonLocation.pokemon_id)
    )
    if method:
        query = query.filter(PokemonLocation.method == method)
    if condition:
        query = query.filter(PokemonLocation.notes.ilike(f"%{ilike_escape(condition)}%", escape="\\"))
    return query.order_by(Pokemon.id).limit(200).all()
