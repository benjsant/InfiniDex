"""API routes for triple fusions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.triple_fusion import (
    TripleFusionAbilityOut,
    TripleFusionComponentOut,
    TripleFusionDetail,
    TripleFusionListItem,
    TripleFusionTypeOut,
)
from backend.services.triple_fusion_service import get_triple_fusion, list_triple_fusions

router = APIRouter(prefix="/triple-fusions", tags=["TripleFusion"])


def _serialize_types(types_rel) -> list[TripleFusionTypeOut]:
    return [
        TripleFusionTypeOut(
            slot=t.slot,
            name_en=t.type.name_en,
            name_fr=t.type.name_fr,
            is_triple_fusion_type=t.type.is_triple_fusion_type,
        )
        for t in sorted(types_rel, key=lambda x: x.slot)
    ]


@router.get("/", response_model=list[TripleFusionListItem])
def list_all(db: Session = Depends(get_db)):
    """List all triple fusions in the game (23 entries)."""
    return [
        TripleFusionListItem(
            id=tf.id,
            name_en=tf.name_en,
            name_fr=tf.name_fr,
            sprite_path=tf.sprite_path,
            types=_serialize_types(tf.types),
        )
        for tf in list_triple_fusions(db)
    ]


@router.get("/{tf_id}", response_model=TripleFusionDetail)
def get_detail(tf_id: int, db: Session = Depends(get_db)):
    """Full detail of a triple fusion: stats, components, types, and abilities."""
    tf = get_triple_fusion(db, tf_id)
    if not tf:
        raise HTTPException(status_code=404, detail=f"Triple fusion #{tf_id} not found")
    return TripleFusionDetail(
        id=tf.id,
        name_en=tf.name_en,
        name_fr=tf.name_fr,
        sprite_path=tf.sprite_path,
        hp=tf.hp,
        attack=tf.attack,
        defense=tf.defense,
        sp_attack=tf.sp_attack,
        sp_defense=tf.sp_defense,
        speed=tf.speed,
        evolves_from_id=tf.evolves_from_id,
        evolution_level=tf.evolution_level,
        steps_to_hatch=tf.steps_to_hatch,
        types=_serialize_types(tf.types),
        components=[
            TripleFusionComponentOut(
                position=c.position,
                pokemon_id=c.pokemon_id,
                name_en=c.pokemon.name_en,
                name_fr=c.pokemon.name_fr,
            )
            for c in sorted(tf.components, key=lambda x: x.position)
        ],
        abilities=[
            TripleFusionAbilityOut(
                slot=a.slot,
                is_hidden=a.is_hidden,
                name_en=a.ability.name_en,
                name_fr=a.ability.name_fr,
            )
            for a in sorted(tf.abilities, key=lambda x: x.slot)
        ],
    )
