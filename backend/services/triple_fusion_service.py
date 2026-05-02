"""Triple fusion queries."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from backend.db.models.triple_fusion import (
    TripleFusion,
    TripleFusionAbility,
    TripleFusionComponent,
    TripleFusionType,
)
from backend.db.models import Type, TypeEffectiveness


def list_triple_fusions(db: Session) -> list[TripleFusion]:
    return (
        db.query(TripleFusion)
        .options(
            joinedload(TripleFusion.types).joinedload(TripleFusionType.type),
        )
        .order_by(TripleFusion.id)
        .all()
    )


def get_triple_fusion(db: Session, tf_id: int) -> TripleFusion | None:
    return (
        db.query(TripleFusion)
        .options(
            joinedload(TripleFusion.types).joinedload(TripleFusionType.type),
            joinedload(TripleFusion.components).joinedload(TripleFusionComponent.pokemon),
            joinedload(TripleFusion.abilities).joinedload(TripleFusionAbility.ability),
        )
        .filter(TripleFusion.id == tf_id)
        .first()
    )


def compute_triple_fusion_weaknesses(db: Session, tf: TripleFusion) -> list[dict]:
    """Damage multipliers against the triple fusion's types.

    Triple fusion compound types (e.g. 'Ice/Fire/Electric') are custom types
    with their own pre-defined type effectiveness rows — they are NOT
    decomposed into component types.
    """
    defending_ids: list[int] = [slot.type.id for slot in sorted(tf.types, key=lambda x: x.slot)]

    if not defending_ids:
        return []

    multipliers: dict[int, Decimal] = defaultdict(lambda: Decimal("1.0"))
    rows = (
        db.query(TypeEffectiveness)
        .filter(TypeEffectiveness.defending_type_id.in_(defending_ids))
        .all()
    )
    for eff in rows:
        multipliers[eff.attacking_type_id] *= eff.multiplier

    # Only expose standard types as attackers — triple fusion types as attackers
    # are internal game data (cross-type interactions) not relevant to the player UI.
    type_map = {
        t.id: t for t in
        db.query(Type)
        .filter(Type.id.in_(multipliers.keys()), Type.is_triple_fusion_type == False)  # noqa: E712
        .all()
    }
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
