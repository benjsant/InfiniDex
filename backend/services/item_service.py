"""Service layer for items (scope restreint : fusion / evolution / valuable)."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from backend.db.models import Item
from backend.utils.text import ilike_escape, normalize


def _with_locations(query):
    return query.options(joinedload(Item.locations))


def list_items(db: Session, *, category: str | None = None) -> list[Item]:
    """List items, optionally filtered by category."""
    query = _with_locations(db.query(Item))
    if category is not None:
        query = query.filter(Item.category == category)
    return query.order_by(Item.category, Item.name_en).all()


def get_item_by_id(db: Session, item_id: int) -> Item | None:
    return _with_locations(db.query(Item)).filter(Item.id == item_id).first()


def search_items(db: Session, name: str) -> list[Item]:
    """Accent-insensitive partial match on name_en or name_fr."""
    needle = normalize(name)
    escaped = ilike_escape(name)
    candidates = (
        db.query(Item)
        .filter(
            Item.name_en.ilike(f"%{escaped}%", escape="\\")
            | Item.name_fr.ilike(f"%{escaped}%", escape="\\")
        )
        .all()
    )
    exact = [
        i for i in candidates
        if needle in normalize(i.name_en or "")
        or needle in normalize(i.name_fr or "")
    ]
    return exact if exact else candidates
