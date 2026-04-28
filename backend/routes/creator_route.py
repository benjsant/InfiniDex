"""API routes for sprite creators."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.creator import CreatorOut
from backend.schemas.sprite import SpriteOut
from backend.services.creator_service import (
    get_creator_by_id,
    list_creators,
    list_sprites_for_creator,
)

router = APIRouter(prefix="/creators", tags=["Creators"])


@router.get("/", response_model=list[CreatorOut])
def get_creators(
    db: Session = Depends(get_db),
    limit: int | None = Query(None, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, description="Filter by name (ilike)"),
):
    """List sprite artists, sorted by sprite count in descending order."""
    rows = list_creators(db, limit=limit, offset=offset, q=q)
    return [CreatorOut(id=c.id, name=c.name, sprite_count=cnt) for c, cnt in rows]


@router.get("/{creator_id}", response_model=CreatorOut)
def get_creator(creator_id: int, db: Session = Depends(get_db)):
    """Detail of a sprite creator with their total sprite count."""
    row = get_creator_by_id(db, creator_id)
    if not row:
        raise HTTPException(status_code=404, detail="Creator not found")
    c, cnt = row
    return CreatorOut(id=c.id, name=c.name, sprite_count=cnt)


@router.get("/{creator_id}/sprites", response_model=list[SpriteOut])
def get_sprites_by_creator(creator_id: int, db: Session = Depends(get_db)):
    """All sprites created by this creator."""
    if not get_creator_by_id(db, creator_id):
        raise HTTPException(status_code=404, detail="Creator not found")
    sprites = list_sprites_for_creator(db, creator_id)
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
