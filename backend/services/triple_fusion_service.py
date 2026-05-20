"""Triple fusion queries."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from backend.db.models.triple_fusion import (
    TripleFusion,
    TripleFusionAbility,
    TripleFusionComponent,
    TripleFusionType,
)
from backend.services.type_effectiveness import compute_weaknesses_for


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

    Only standard types are exposed as attackers — triple fusion types as
    attackers are internal game data, not relevant to the player UI.
    """
    defending_ids: list[int] = [slot.type.id for slot in sorted(tf.types, key=lambda x: x.slot)]
    return compute_weaknesses_for(db, defending_ids, standard_attackers_only=True)
