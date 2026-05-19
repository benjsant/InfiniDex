"""Service layer for generations."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from backend.db.models import Generation, Pokemon, PokemonType


def list_generations(db: Session) -> list[Generation]:
    return db.query(Generation).order_by(Generation.id).all()


def get_generation_by_id(db: Session, gen_id: int) -> Generation | None:
    return db.query(Generation).filter(Generation.id == gen_id).first()


def list_pokemon_in_generation(db: Session, gen_id: int) -> list[Pokemon]:
    return (
        db.query(Pokemon)
        .options(joinedload(Pokemon.types).joinedload(PokemonType.type))
        .filter(Pokemon.generation_id == gen_id)
        .order_by(Pokemon.id)
        .all()
    )
