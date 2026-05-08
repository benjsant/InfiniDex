"""Service layer for abilities."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.db.models import Ability
from backend.utils.text import ilike_escape, normalize


def list_abilities(db: Session) -> list[Ability]:
    return db.query(Ability).order_by(Ability.id).all()


def get_ability_by_id(db: Session, ability_id: int) -> Ability | None:
    return db.query(Ability).filter(Ability.id == ability_id).first()


def search_abilities(db: Session, name: str) -> list[Ability]:
    """Accent-insensitive partial match on name_en OR name_fr."""
    needle = normalize(name)
    escaped = ilike_escape(name)
    candidates = (
        db.query(Ability)
        .filter(
            Ability.name_en.ilike(f"%{escaped}%", escape="\\")
            | Ability.name_fr.ilike(f"%{escaped}%", escape="\\")
        )
        .all()
    )
    exact = [
        a for a in candidates
        if needle in normalize(a.name_en or "")
        or needle in normalize(a.name_fr or "")
    ]
    return exact if exact else candidates
