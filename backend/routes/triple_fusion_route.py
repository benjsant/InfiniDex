"""API routes for triple fusions."""

from __future__ import annotations

import os
from pathlib import Path as FilePath

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

SPECIAL_SPRITES_DIR = FilePath(os.environ.get("SPECIAL_SPRITES_DIR", "/app/data/special_sprites"))

from backend.db.session import get_db
from backend.schemas.triple_fusion import (
    TripleFusionAbilityOut,
    TripleFusionComponentOut,
    TripleFusionDetail,
    TripleFusionListItem,
    TripleFusionTypeOut,
)
from backend.schemas.weakness import WeaknessOut
from backend.services.triple_fusion_service import (
    compute_triple_fusion_weaknesses,
    get_triple_fusion,
    list_triple_fusions,
)

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


@router.get("/{tf_id}/sprite")
def get_triple_fusion_sprite(tf_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    """Serve the battle sprite PNG for a triple fusion."""
    tf = get_triple_fusion(db, tf_id)
    if not tf:
        raise HTTPException(status_code=404, detail=f"Triple fusion #{tf_id} not found")
    ids = sorted(c.pokemon_id for c in tf.components)
    filename = ".".join(str(i) for i in ids) + ".png"
    path = SPECIAL_SPRITES_DIR / filename
    resolved = path.resolve()
    if not resolved.is_relative_to(SPECIAL_SPRITES_DIR.resolve()) or not resolved.is_file():
        raise HTTPException(status_code=404, detail="Sprite not found")
    return FileResponse(resolved, media_type="image/png")


@router.get("/{tf_id}/weaknesses", response_model=list[WeaknessOut])
def get_triple_fusion_weaknesses(tf_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    """Damage multipliers against this triple fusion's type combination."""
    tf = get_triple_fusion(db, tf_id)
    if not tf:
        raise HTTPException(status_code=404, detail=f"Triple fusion #{tf_id} not found")
    return compute_triple_fusion_weaknesses(db, tf)


@router.get("/{tf_id}", response_model=TripleFusionDetail)
def get_detail(tf_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
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
                national_id=c.pokemon.national_id,
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
