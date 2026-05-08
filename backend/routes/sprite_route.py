"""API routes for fusion sprites."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.sprite import SpriteOut
from backend.services.sprite_service import (
    list_custom_sprites_for_pokemon,
    list_sprites_for_pair,
    resolve_sprite_file,
)

router = APIRouter(prefix="/sprites", tags=["Sprites"])


@router.get("/by_pokemon/{pokemon_id}", response_model=list[SpriteOut])
def get_custom_sprites_for_pokemon(
    pokemon_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    """
    List one custom sprite per fusion pair involving this Pokémon (head or body).

    Returns the default custom sprite for each pair, sorted by head_id then body_id.
    """
    sprites = list_custom_sprites_for_pokemon(db, pokemon_id)
    return [
        SpriteOut(
            id=s.id,
            head_id=s.head_id,
            body_id=s.body_id,
            sprite_path=s.sprite_path,
            is_custom=s.is_custom,
            is_default=s.is_default,
            source=s.source,
            creators=[c.creator.name for c in s.creators],
        )
        for s in sprites
    ]


@router.get("/{head_id}/{body_id}", response_model=list[SpriteOut])
def get_sprites_for_pair(
    head_id: int = Path(..., ge=1),
    body_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    """
    List all sprite variants for a head/body pair, including their credits (creators).

    - The default sprite is sorted first (is_default=true).
    - `source`: 'local' (auto-generated), 'community' (custom sprite), 'auto_generated'.
    """
    sprites = list_sprites_for_pair(db, head_id, body_id)
    return [
        SpriteOut(
            id=s.id,
            head_id=s.head_id,
            body_id=s.body_id,
            sprite_path=s.sprite_path,
            is_custom=s.is_custom,
            is_default=s.is_default,
            source=s.source,
            creators=[c.creator.name for c in s.creators],
        )
        for s in sprites
    ]


@router.get("/{head_id}/{body_id}/image")
def get_sprite_image(
    head_id: int = Path(..., ge=1),
    body_id: int = Path(..., ge=1),
    variant_id: int | None = Query(None, description="Specific sprite.id; default=variant marked is_default"),
    db: Session = Depends(get_db),
):
    """Serve the PNG image of a sprite (default or specific variant)."""
    path = resolve_sprite_file(db, head_id, body_id, variant_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Sprite not found")
    return FileResponse(path, media_type="image/png")
