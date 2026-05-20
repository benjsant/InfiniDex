"""Reusable search helpers for service-layer queries."""

from __future__ import annotations

from typing import Sequence, TypeVar

from sqlalchemy.orm import Session

from backend.utils.text import ilike_escape, normalize

T = TypeVar("T")


def bilingual_ilike_search(
    db: Session,
    model: type[T],
    name: str,
    *,
    with_options: Sequence = (),
) -> list[T]:
    """Bilingual partial-match search on `name_en | name_fr`.

    Uses ilike as a DB-side pre-filter (case-insensitive, reduces the
    candidate set), then re-ranks with `normalize()` so accent variants
    that ilike missed are still treated as exact substring hits.

    Returns exact-substring matches when there is at least one, else
    falls back to the full ilike candidate list.

    `with_options` is an optional sequence of `Load` directives
    (typically `joinedload(...)`) applied to the query.
    """
    needle = normalize(name)
    escaped = ilike_escape(name)
    query = db.query(model).filter(
        model.name_en.ilike(f"%{escaped}%", escape="\\")
        | model.name_fr.ilike(f"%{escaped}%", escape="\\")
    )
    if with_options:
        query = query.options(*with_options)
    candidates = query.all()
    exact = [
        c for c in candidates
        if needle in normalize(c.name_en or "")
        or needle in normalize(c.name_fr or "")
    ]
    return exact if exact else candidates
