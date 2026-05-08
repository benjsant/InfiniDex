"""Service layer for types."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.db.models import Type
from backend.utils.text import ilike_escape, normalize


def list_types(db: Session) -> list[Type]:
    """All 27 IF types (18 standard + 9 triple-fusion)."""
    return db.query(Type).order_by(Type.id).all()


def get_type_by_id(db: Session, type_id: int) -> Type | None:
    return db.query(Type).filter(Type.id == type_id).first()


def find_type_by_name(db: Session, name: str) -> Type | None:
    """Accent and case-insensitive prefix match."""
    needle = normalize(name)
    escaped = ilike_escape(name)
    candidates = (
        db.query(Type)
        .filter(
            Type.name_en.ilike(f"{escaped}%", escape="\\")
            | Type.name_fr.ilike(f"{escaped}%", escape="\\")
        )
        .all()
    )
    for t in candidates:
        if normalize(t.name_en or "").startswith(needle) or \
           normalize(t.name_fr or "").startswith(needle):
            return t
    return None
