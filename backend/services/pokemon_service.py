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
) -> list[Pokemon]:
    """Paginated list of Pokémon with type / generation / Hoenn-only filters."""
    query = db.query(Pokemon).options(joinedload(Pokemon.types))
    if type_id is not None:
        sub = db.query(PokemonType.pokemon_id).filter(PokemonType.type_id == type_id)
        query = query.filter(Pokemon.id.in_(sub))
    if generation_id is not None:
        query = query.filter(Pokemon.generation_id == generation_id)
    if not include_hoenn:
        query = query.filter(Pokemon.is_hoenn_only.is_(False))
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
    """Evolution rows touching this Pokémon (as source OR target).

    Returns both:
      - outgoing (this Pokémon evolves into X) — `pokemon_id == id`
      - incoming (Y evolves into this Pokémon) — `evolves_into_id == id`
    """
    return (
        db.query(PokemonEvolution)
        .options(
            joinedload(PokemonEvolution.evolves_into),
            joinedload(PokemonEvolution.pokemon),
        )
        .filter(
            (PokemonEvolution.pokemon_id == pokemon_id)
            | (PokemonEvolution.evolves_into_id == pokemon_id)
        )
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
