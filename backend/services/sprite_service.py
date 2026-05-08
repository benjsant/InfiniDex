"""Sprite lookup service."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from backend.db.models import FusionSprite, FusionSpriteCreator

SPRITES_DIR = Path(os.environ.get("SPRITES_DIR", "data/sprites"))


def list_sprites_for_pair(db: Session, head_id: int, body_id: int) -> list[FusionSprite]:
    return (
        db.query(FusionSprite)
        .options(
            joinedload(FusionSprite.creators).joinedload(FusionSpriteCreator.creator)
        )
        .filter(FusionSprite.head_id == head_id, FusionSprite.body_id == body_id)
        .order_by(FusionSprite.is_default.desc(), FusionSprite.sprite_path)
        .all()
    )


def list_custom_sprites_for_pokemon(db: Session, pokemon_id: int) -> list[FusionSprite]:
    """One default custom sprite per (head_id, body_id) pair involving pokemon_id."""
    # DISTINCT ON picks the first row per pair when ordered by is_default DESC — PostgreSQL only.
    subq = (
        db.query(FusionSprite.id)
        .filter(
            or_(FusionSprite.head_id == pokemon_id, FusionSprite.body_id == pokemon_id),
            FusionSprite.is_custom == True,  # noqa: E712
        )
        .order_by(
            FusionSprite.head_id,
            FusionSprite.body_id,
            FusionSprite.is_default.desc(),
            FusionSprite.id,
        )
        .distinct(FusionSprite.head_id, FusionSprite.body_id)
        .subquery()
    )
    return (
        db.query(FusionSprite)
        .options(joinedload(FusionSprite.creators).joinedload(FusionSpriteCreator.creator))
        .filter(FusionSprite.id.in_(subq))
        .order_by(FusionSprite.head_id, FusionSprite.body_id)
        .all()
    )


def resolve_sprite_file(
    db: Session,
    head_id: int,
    body_id: int,
    variant_id: int | None = None,
) -> Path | None:
    """Return the filesystem path of the sprite to serve, or None if missing.

    Picks the DB row (specific variant_id, or is_default, or first),
    then checks that `SPRITES_DIR/<sprite_path>` exists. Falls back to
    `{head}.{body}.png` if no DB row matches.
    """
    q = db.query(FusionSprite).filter(
        FusionSprite.head_id == head_id, FusionSprite.body_id == body_id
    )
    if variant_id is not None:
        row = q.filter(FusionSprite.id == variant_id).one_or_none()
    else:
        row = q.order_by(FusionSprite.is_default.desc(), FusionSprite.id).first()

    candidate = SPRITES_DIR / (row.sprite_path if row else f"{head_id}.{body_id}.png")
    if not candidate.resolve().is_relative_to(SPRITES_DIR.resolve()):
        return None
    return candidate if candidate.is_file() else None
