"""API routes for generations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.routes.pokemon_route import pokemon_to_list_item
from backend.schemas.generation import GenerationOut
from backend.schemas.pokemon import PokemonListItem
from backend.services.generation_service import (
    get_generation_by_id,
    list_generations,
    list_pokemon_in_generation,
)

router = APIRouter(prefix="/generations", tags=["Generations"])


@router.get("/", response_model=list[GenerationOut])
def get_generations(db: Session = Depends(get_db)):
    """List all generations (1–9)."""
    return list_generations(db)


@router.get("/{gen_id}", response_model=GenerationOut)
def get_generation(gen_id: int, db: Session = Depends(get_db)):
    """Detail of a generation by ID (1–9)."""
    g = get_generation_by_id(db, gen_id)
    if not g:
        raise HTTPException(status_code=404, detail="Generation not found")
    return g


@router.get("/{gen_id}/pokemon", response_model=list[PokemonListItem])
def get_pokemon_for_generation(gen_id: int, db: Session = Depends(get_db)):
    """All Pokémon belonging to a generation."""
    if not get_generation_by_id(db, gen_id):
        raise HTTPException(status_code=404, detail="Generation not found")
    return [pokemon_to_list_item(p) for p in list_pokemon_in_generation(db, gen_id)]
