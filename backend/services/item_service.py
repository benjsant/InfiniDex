"""Service layer for items (scope restreint : fusion / evolution / valuable)."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from backend.db.models import Item
from backend.utils.search import bilingual_ilike_search


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
    return bilingual_ilike_search(db, Item, name)
