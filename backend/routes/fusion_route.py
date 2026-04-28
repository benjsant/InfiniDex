"""API routes for fusion computation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.routes.deps import get_pokemon_or_404
from backend.db.models import Pokemon
from backend.schemas.fusion import (
    FusionAbilityOut,
    FusionExpertMoveOut,
    FusionInvolvingOut,
    FusionMoveOut,
    FusionResult,
)
from backend.schemas.type_ import TypeOut
from backend.schemas.weakness import WeaknessOut
from backend.services.fusion_service import (
    load_pokemon_with_types,
    compute_fusion,
    compute_fusion_abilities,
    compute_fusion_expert_moves,
    compute_fusion_moves,
    compute_fusion_weaknesses,
    list_fusions_involving,
    random_fusion_ids,
)

router = APIRouter(prefix="/fusion", tags=["Fusion"])
plural_router = APIRouter(prefix="/fusions", tags=["Fusion"])


@plural_router.get("/involving/{pokemon_id}", response_model=list[FusionInvolvingOut])
def get_fusions_involving(
    p: Pokemon = Depends(get_pokemon_or_404),
    db: Session = Depends(get_db),
    limit: int | None = Query(None, ge=1, le=2000),
    offset: int = Query(0, ge=0),
):
    """All fusion pairs (as head OR body) involving this Pokémon."""
    rows = list_fusions_involving(db, p.id, limit=limit, offset=offset)
    return [FusionInvolvingOut(**r) for r in rows]


def _to_type_out(t) -> TypeOut | None:
    if t is None:
        return None
    return TypeOut(
        id=t.id,
        name_en=t.name_en,
        name_fr=t.name_fr,
        is_triple_fusion_type=t.is_triple_fusion_type,
    )


def _load_pair_or_404(db: Session, head_id: int, body_id: int):
    head = load_pokemon_with_types(db, head_id)
    body = load_pokemon_with_types(db, body_id)
    if not head or not body:
        raise HTTPException(
            status_code=404,
            detail=f"Pokémon #{head_id} or #{body_id} not found",
        )
    return head, body


@router.get("/random", response_model=FusionResult)
def get_random_fusion(db: Session = Depends(get_db)):
    """Return a random fusion (head + body drawn at random)."""
    head_id, body_id = random_fusion_ids(db)
    return get_fusion(head_id, body_id, db)


@router.get("/{head_id}/{body_id}", response_model=FusionResult)
def get_fusion(head_id: int, body_id: int, db: Session = Depends(get_db)):
    """
    Stats, types, and sprite of a fusion.

    - Physical stats (HP/Atk/Def/Spe) = floor(Body×2/3 + Head×1/3)
    - Special stats (SpA/SpD)          = floor(Head×2/3 + Body×1/3)
    - Type 1 = primary type of Head
    - Type 2 = primary type of Body (if different)
    - Sprite: `{head_id}.{body_id}.png`
    """
    result = compute_fusion(db, head_id, body_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Pokémon #{head_id} or #{body_id} not found",
        )
    return FusionResult(
        head_id=result["head_id"],
        body_id=result["body_id"],
        head_name_en=result["head_name_en"],
        head_name_fr=result["head_name_fr"],
        body_name_en=result["body_name_en"],
        body_name_fr=result["body_name_fr"],
        hp=result["hp"],
        attack=result["attack"],
        defense=result["defense"],
        sp_attack=result["sp_attack"],
        sp_defense=result["sp_defense"],
        speed=result["speed"],
        type1=_to_type_out(result["type1"]),
        type2=_to_type_out(result["type2"]),
        sprite_path=result["sprite_path"],
    )


@router.get("/{head_id}/{body_id}/moves", response_model=list[FusionMoveOut])
def get_fusion_moves(head_id: int, body_id: int, db: Session = Depends(get_db)):
    """Combined head + body moveset, deduplicated per move (origin='head'|'body'|'both')."""
    head, body = _load_pair_or_404(db, head_id, body_id)
    rows = compute_fusion_moves(db, head.id, body.id)
    return [
        FusionMoveOut(
            move_id=r["move_id"],
            name_en=r["name_en"],
            name_fr=r["name_fr"],
            category=r["category"],
            power=r["power"],
            accuracy=r["accuracy"],
            pp=r["pp"],
            type=_to_type_out(r["type"]),
            method=r["method"],
            level=r["level"],
            source=r["source"],
            origin=r["origin"],
        )
        for r in rows
    ]


@router.get("/{head_id}/{body_id}/abilities", response_model=list[FusionAbilityOut])
def get_fusion_abilities(head_id: int, body_id: int, db: Session = Depends(get_db)):
    """Abilities available for the fusion (IF rule: head slot 1 + body slot 1 + hidden abilities)."""
    head, body = _load_pair_or_404(db, head_id, body_id)
    return [FusionAbilityOut(**a) for a in compute_fusion_abilities(db, head, body)]


@router.get("/{head_id}/{body_id}/weaknesses", response_model=list[WeaknessOut])
def get_fusion_weaknesses(head_id: int, body_id: int, db: Session = Depends(get_db)):
    """Damage multipliers against the fusion's types (non-neutral only)."""
    head, body = _load_pair_or_404(db, head_id, body_id)
    return compute_fusion_weaknesses(db, head, body)


@router.get(
    "/{head_id}/{body_id}/expert-moves",
    response_model=list[FusionExpertMoveOut],
)
def get_fusion_expert_moves(head_id: int, body_id: int, db: Session = Depends(get_db)):
    """Moves teachable to this fusion by a Move Expert (Knot / Boon Island)."""
    head, body = _load_pair_or_404(db, head_id, body_id)
    rows = compute_fusion_expert_moves(db, head, body)
    return [
        FusionExpertMoveOut(
            move_id=r["move_id"],
            name_en=r["name_en"],
            name_fr=r["name_fr"],
            category=r["category"],
            power=r["power"],
            accuracy=r["accuracy"],
            pp=r["pp"],
            type=_to_type_out(r["type"]),
            locations=r["locations"],
            prices_heart_scales=r["prices_heart_scales"],
        )
        for r in rows
    ]
