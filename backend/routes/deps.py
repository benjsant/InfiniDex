"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Path
from sqlalchemy.orm import Session

from backend.db.models import Pokemon
from backend.db.session import get_db
from backend.services.pokemon_service import get_pokemon_by_id


def get_pokemon_or_404(
    pokemon_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> Pokemon:
    """Resolve a Pokémon from the path parameter; raises 404 if not found."""
    p = get_pokemon_by_id(db, pokemon_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Pokémon #{pokemon_id} not found")
    return p
