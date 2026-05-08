"""Service layer for creators (sprite artists)."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.db.models import Creator, FusionSprite, FusionSpriteCreator
from backend.utils.text import ilike_escape


def list_creators(
    db: Session, *, limit: int | None = None, offset: int = 0, q: str | None = None
) -> list[tuple[Creator, int]]:
    """Return (creator, sprite_count) tuples, ordered by count desc."""
    query = (
        db.query(Creator, func.count(FusionSpriteCreator.fusion_sprite_id).label("cnt"))
        .outerjoin(FusionSpriteCreator, FusionSpriteCreator.creator_id == Creator.id)
        .group_by(Creator.id)
        .order_by(func.count(FusionSpriteCreator.fusion_sprite_id).desc(), Creator.name)
    )
    if q:
        query = query.filter(Creator.name.ilike(f"%{ilike_escape(q)}%", escape="\\"))
    query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def get_creator_by_id(db: Session, creator_id: int) -> tuple[Creator, int] | None:
    row = (
        db.query(Creator, func.count(FusionSpriteCreator.fusion_sprite_id))
        .outerjoin(FusionSpriteCreator, FusionSpriteCreator.creator_id == Creator.id)
        .filter(Creator.id == creator_id)
        .group_by(Creator.id)
        .one_or_none()
    )
    return row


def list_sprites_for_creator(db: Session, creator_id: int) -> list[FusionSprite]:
    return (
        db.query(FusionSprite)
        .join(FusionSpriteCreator, FusionSpriteCreator.fusion_sprite_id == FusionSprite.id)
        .filter(FusionSpriteCreator.creator_id == creator_id)
        .options(joinedload(FusionSprite.creators).joinedload(FusionSpriteCreator.creator))
        .order_by(FusionSprite.head_id, FusionSprite.body_id)
        .all()
    )
