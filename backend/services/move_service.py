"""Service layer for moves."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from backend.db.models import Location, Move, MoveTutor, PokemonMove, TM, TMLocation
from backend.utils.text import normalize


def list_moves(
    db: Session,
    *,
    category: str | None = None,
    type_id: int | None = None,
    power_min: int | None = None,
    power_max: int | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[Move]:
    query = db.query(Move).options(joinedload(Move.type))
    if category is not None:
        query = query.filter(Move.category == category)
    if type_id is not None:
        query = query.filter(Move.type_id == type_id)
    if power_min is not None:
        query = query.filter(Move.power >= power_min)
    if power_max is not None:
        query = query.filter(Move.power <= power_max)
    query = query.order_by(Move.id).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def get_move_by_id(db: Session, move_id: int) -> Move | None:
    return (
        db.query(Move)
        .options(joinedload(Move.type))
        .filter(Move.id == move_id)
        .first()
    )


def search_moves(db: Session, name: str) -> list[Move]:
    """Accent-insensitive partial match on name_en OR name_fr.

    Uses ilike as a DB-side pre-filter (case-insensitive, reduces candidates
    from all moves to a small subset), then applies normalize() for the
    accent-insensitive pass on that smaller set only.
    """
    needle = normalize(name)
    candidates = (
        db.query(Move)
        .options(joinedload(Move.type))
        .filter(Move.name_en.ilike(f"%{name}%") | Move.name_fr.ilike(f"%{name}%"))
        .all()
    )
    # If ilike caught everything (no accents in query), return directly.
    # Otherwise apply normalize() to catch accent variants missed by ilike.
    exact = [
        m for m in candidates
        if needle in normalize(m.name_en or "")
        or needle in normalize(m.name_fr or "")
    ]
    return exact if exact else candidates


def list_moves_by_type(db: Session, type_name: str) -> list[Move]:
    """All moves for a given type (name_en or name_fr, case-insensitive)."""
    from backend.db.models import Type  # avoid circular at module level

    type_obj = (
        db.query(Type)
        .filter(
            Type.name_en.ilike(f"{type_name}%") | Type.name_fr.ilike(f"{type_name}%")
        )
        .first()
    )
    if not type_obj:
        return []

    return (
        db.query(Move)
        .options(joinedload(Move.type))
        .filter(Move.type_id == type_obj.id)
        .order_by(Move.id)
        .all()
    )


def list_pokemon_moves(db: Session, pokemon_id: int) -> list[PokemonMove]:
    """All PokemonMove rows for a Pokémon, with move + type eagerly loaded."""
    return (
        db.query(PokemonMove)
        .options(
            joinedload(PokemonMove.move).joinedload(Move.type)
        )
        .filter(PokemonMove.pokemon_id == pokemon_id)
        .order_by(PokemonMove.method, PokemonMove.level)
        .all()
    )


def get_tm_for_move(db: Session, move_id: int) -> TM | None:
    """Return the TM row for a given move (with locations eagerly loaded), or None."""
    return (
        db.query(TM)
        .options(joinedload(TM.locations).joinedload(TMLocation.location))
        .filter(TM.move_id == move_id)
        .first()
    )


def list_tutors_for_move(db: Session, move_id: int) -> list[MoveTutor]:
    """All `move_tutor` rows teaching this move, location eagerly loaded.

    Ordered by price ASC (free/quest first via NULLs FIRST).
    """
    return (
        db.query(MoveTutor)
        .options(joinedload(MoveTutor.location))
        .filter(MoveTutor.move_id == move_id)
        .order_by(MoveTutor.price.asc().nullsfirst(), Location.name_en)
        .join(Location, Location.id == MoveTutor.location_id)
        .all()
    )
