"""Damage multiplier computation shared by Pokémon / Fusion / TripleFusion."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Sequence

from sqlalchemy.orm import Session

from backend.db.models import Type, TypeEffectiveness


def compute_weaknesses_for(
    db: Session,
    defending_type_ids: Sequence[int],
    *,
    standard_attackers_only: bool = False,
) -> list[dict]:
    """Per-attacking-type damage multipliers against a set of defending types.

    Multipliers compound: e.g. a Grass/Flying defender vs Fire = 2.0 × 0.5 = 1.0.
    Only non-neutral results are returned (≠ 1.0). Defending types not listed in
    `type_effectiveness` default to 1.0 against all attackers.

    `standard_attackers_only=True` excludes triple-fusion compound types from
    the result (used by triple fusion endpoints — those internal types are not
    relevant to player-facing UI).
    """
    if not defending_type_ids:
        return []

    multipliers: dict[int, Decimal] = defaultdict(lambda: Decimal("1.0"))
    rows = (
        db.query(TypeEffectiveness)
        .filter(TypeEffectiveness.defending_type_id.in_(defending_type_ids))
        .all()
    )
    for eff in rows:
        multipliers[eff.attacking_type_id] *= eff.multiplier

    type_query = db.query(Type).filter(Type.id.in_(multipliers.keys()))
    if standard_attackers_only:
        type_query = type_query.filter(Type.is_triple_fusion_type == False)  # noqa: E712
    type_map = {t.id: t for t in type_query.all()}

    return [
        {
            "attacking_type_id":      tid,
            "attacking_type_name_en": type_map[tid].name_en,
            "attacking_type_name_fr": type_map[tid].name_fr,
            "multiplier":             float(mult),
        }
        for tid, mult in sorted(multipliers.items())
        if mult != Decimal("1.0") and tid in type_map
    ]
