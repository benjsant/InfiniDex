"""Service layer for Pokémon — list/detail queries + sub-aspects (moves,
evolutions, locations, weaknesses)."""

from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from backend.db.models import Move, Pokemon, PokemonEvolution, PokemonLocation, PokemonMove, PokemonType, Type, TypeEffectiveness


def list_pokemon(
    db: Session,
    *,
    limit: int | None = None,
    offset: int = 0,
    type_id: int | None = None,
    generation_id: int | None = None,
    include_hoenn: bool = True,
    legendary_only: bool = False,
) -> list[Pokemon]:
    """Paginated list of Pokémon with type / generation / Hoenn-only / legendary filters."""
    query = db.query(Pokemon).options(joinedload(Pokemon.types))
    if type_id is not None:
        sub = db.query(PokemonType.pokemon_id).filter(PokemonType.type_id == type_id)
        query = query.filter(Pokemon.id.in_(sub))
    if generation_id is not None:
        query = query.filter(Pokemon.generation_id == generation_id)
    if not include_hoenn:
        query = query.filter(Pokemon.is_hoenn_only.is_(False))
    if legendary_only:
        query = query.filter(Pokemon.is_legendary.is_(True))
    query = query.order_by(Pokemon.id).offset(offset)
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
            Pokemon.name_en.ilike(f"%{name}%")
            | Pokemon.name_fr.ilike(f"%{name}%")
        )
        .order_by(Pokemon.id)
        .all()
    )


def compute_pokemon_weaknesses(db: Session, pokemon_id: int) -> list[dict] | None:
    """
    Returns damage multipliers for every attacking type against this Pokémon.

    For dual-type Pokémon the multipliers are compounded:
      e.g. Grass/Flying vs Fire → 0.5 × 2.0 = 1.0 (neutral)

    Only types with a non-neutral final multiplier (≠ 1.0) are returned.
    Types not listed in type_effectiveness default to 1.0.
    """
    pokemon = db.query(Pokemon).filter(Pokemon.id == pokemon_id).first()
    if not pokemon:
        return None

    defending_type_ids = [pt.type_id for pt in pokemon.types]

    multipliers: dict[int, Decimal] = defaultdict(lambda: Decimal("1.0"))

    affinities = (
        db.query(TypeEffectiveness)
        .filter(TypeEffectiveness.defending_type_id.in_(defending_type_ids))
        .all()
    )

    for eff in affinities:
        multipliers[eff.attacking_type_id] *= eff.multiplier

    # Only return non-neutral results — fetch only the attacking types that appear.
    type_map = {t.id: t for t in db.query(Type).filter(Type.id.in_(multipliers.keys())).all()}

    return [
        {
            "attacking_type_id":      tid,
            "attacking_type_name_en": type_map[tid].name_en,
            "attacking_type_name_fr": type_map[tid].name_fr,
            "multiplier":             float(mult),
        }
        for tid, mult in sorted(multipliers.items())
        if mult != Decimal("1.0") and tid in type_map
    ]


def get_pokemon_moves(db: Session, pokemon_id: int) -> list[PokemonMove]:
    """All moves for a Pokémon, with move + type eagerly loaded."""
    return (
        db.query(PokemonMove)
        .options(
            joinedload(PokemonMove.move).joinedload(Move.type)
        )
        .filter(PokemonMove.pokemon_id == pokemon_id)
        .order_by(PokemonMove.method, PokemonMove.level)
        .all()
    )


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
        query = query.filter(PokemonLocation.notes.ilike(f"%{condition}%"))
    return query.order_by(Pokemon.id).all()
