"""API routes for fusion computation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.routes.deps import get_pokemon_or_404
from backend.db.models import Pokemon
from backend.schemas.fusion import (
    FusionAbilityOut,
    FusionExpertMoveOut,
    FusionFeaturedItem,
    FusionFullOut,
    FusionInvolvingOut,
    FusionMoveOut,
    FusionResult,
    FusionTopItem,
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
    list_featured_fusions,
    list_fusions_involving,
    list_top_fusions_for_pokemon,
    random_fusion_ids,
)

router = APIRouter(prefix="/fusion", tags=["Fusion"])
plural_router = APIRouter(prefix="/fusions", tags=["Fusion"])


@plural_router.get("/featured", response_model=list[FusionFeaturedItem])
def get_featured_fusions(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Random sample of fusions that have a custom community sprite."""
    rows = list_featured_fusions(db, limit=limit)
    return [
        FusionFeaturedItem(
            head_id=r["head_id"],
            body_id=r["body_id"],
            head_name_en=r["head_name_en"],
            head_name_fr=r["head_name_fr"],
            body_name_en=r["body_name_en"],
            body_name_fr=r["body_name_fr"],
            type1=TypeOut.from_model(r["type1"]),
            type2=TypeOut.from_model(r["type2"]),
            sprite_path=r["sprite_path"],
        )
        for r in rows
    ]


@plural_router.get("/top-by-pokemon/{pokemon_id}", response_model=list[FusionTopItem])
def get_top_fusions_for_pokemon(
    p: Pokemon = Depends(get_pokemon_or_404),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Best fusions for a given Pokémon (as head OR body), ranked by BST."""
    rows = list_top_fusions_for_pokemon(db, p.id, limit=limit)
    return [
        FusionTopItem(
            rank=r["rank"],
            head_id=r["head_id"],
            body_id=r["body_id"],
            head_name_en=r["head_name_en"],
            head_name_fr=r["head_name_fr"],
            body_name_en=r["body_name_en"],
            body_name_fr=r["body_name_fr"],
            hp=r["hp"],
            attack=r["attack"],
            defense=r["defense"],
            sp_attack=r["sp_attack"],
            sp_defense=r["sp_defense"],
            speed=r["speed"],
            bst=r["bst"],
            type1=TypeOut.from_model(r["type1"]),
            type2=TypeOut.from_model(r["type2"]),
            sprite_path=r["sprite_path"],
            role=r["role"],
        )
        for r in rows
    ]


@plural_router.get("/involving/{pokemon_id}", response_model=list[FusionInvolvingOut])
def get_fusions_involving(
    p: Pokemon = Depends(get_pokemon_or_404),
    db: Session = Depends(get_db),
    limit: int | None = Query(None, ge=1, le=2000),
    offset: int = Query(0, ge=0, le=100_000),
):
    """All fusion pairs (as head OR body) involving this Pokémon."""
    rows = list_fusions_involving(db, p.id, limit=limit, offset=offset)
    return [FusionInvolvingOut(**r) for r in rows]


def _to_fusion_result(r: dict) -> FusionResult:
    return FusionResult(
        head_id=r["head_id"],
        body_id=r["body_id"],
        head_name_en=r["head_name_en"],
        head_name_fr=r["head_name_fr"],
        body_name_en=r["body_name_en"],
        body_name_fr=r["body_name_fr"],
        hp=r["hp"],
        attack=r["attack"],
        defense=r["defense"],
        sp_attack=r["sp_attack"],
        sp_defense=r["sp_defense"],
        speed=r["speed"],
        type1=TypeOut.from_model(r["type1"]),
        type2=TypeOut.from_model(r["type2"]),
        sprite_path=r["sprite_path"],
    )


def _to_fusion_move(r: dict) -> FusionMoveOut:
    return FusionMoveOut(
        move_id=r["move_id"],
        name_en=r["name_en"],
        name_fr=r["name_fr"],
        category=r["category"],
        power=r["power"],
        accuracy=r["accuracy"],
        pp=r["pp"],
        type=TypeOut.from_model(r["type"]),
        method=r["method"],
        level=r["level"],
        source=r["source"],
        origin=r["origin"],
    )


def _to_fusion_expert_move(r: dict) -> FusionExpertMoveOut:
    return FusionExpertMoveOut(
        move_id=r["move_id"],
        name_en=r["name_en"],
        name_fr=r["name_fr"],
        category=r["category"],
        power=r["power"],
        accuracy=r["accuracy"],
        pp=r["pp"],
        type=TypeOut.from_model(r["type"]),
        locations=r["locations"],
        prices_heart_scales=r["prices_heart_scales"],
    )


def _id_path() -> int:
    """Factory for Path(ge=1, le=2000).

    Must NOT be shared between parameters — FastAPI mutates FieldInfo aliases
    in-place during route registration, so a shared instance causes body_id to
    resolve from the {head_id} path segment instead of {body_id}.
    """
    return Path(ge=1, le=2000)


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
    try:
        head_id, body_id = random_fusion_ids(db)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return get_fusion(head_id, body_id, db)


@router.get("/{head_id}/{body_id}", response_model=FusionResult)
def get_fusion(head_id: int = _id_path(), body_id: int = _id_path(), db: Session = Depends(get_db)):
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
    return _to_fusion_result(result)


@router.get("/{head_id}/{body_id}/full", response_model=FusionFullOut)
def get_fusion_full(head_id: int = _id_path(), body_id: int = _id_path(), db: Session = Depends(get_db)):
    """Stats + full moveset + expert moves in a single round-trip.

    Replaces the three separate calls (/{h}/{b}, /{h}/{b}/moves,
    /{h}/{b}/expert-moves) made by the fusion result page.
    """
    result = compute_fusion(db, head_id, body_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Pokémon #{head_id} or #{body_id} not found",
        )
    head, body = _load_pair_or_404(db, head_id, body_id)

    fusion = _to_fusion_result(result)
    moves = [_to_fusion_move(r) for r in compute_fusion_moves(db, head.id, body.id)]
    expert_moves = [_to_fusion_expert_move(r) for r in compute_fusion_expert_moves(db, head, body)]
    return FusionFullOut(fusion=fusion, moves=moves, expert_moves=expert_moves)


@router.get("/{head_id}/{body_id}/moves", response_model=list[FusionMoveOut])
def get_fusion_moves(head_id: int = _id_path(), body_id: int = _id_path(), db: Session = Depends(get_db)):
    """Combined head + body moveset, deduplicated per move (origin='head'|'body'|'both')."""
    head, body = _load_pair_or_404(db, head_id, body_id)
    return [_to_fusion_move(r) for r in compute_fusion_moves(db, head.id, body.id)]


@router.get("/{head_id}/{body_id}/abilities", response_model=list[FusionAbilityOut])
def get_fusion_abilities(head_id: int = _id_path(), body_id: int = _id_path(), db: Session = Depends(get_db)):
    """Abilities available for the fusion (IF rule: head slot 1 + body slot 1 + hidden abilities)."""
    head, body = _load_pair_or_404(db, head_id, body_id)
    return [FusionAbilityOut(**a) for a in compute_fusion_abilities(db, head, body)]


@router.get("/{head_id}/{body_id}/weaknesses", response_model=list[WeaknessOut])
def get_fusion_weaknesses(head_id: int = _id_path(), body_id: int = _id_path(), db: Session = Depends(get_db)):
    """Damage multipliers against the fusion's types (non-neutral only)."""
    head, body = _load_pair_or_404(db, head_id, body_id)
    return compute_fusion_weaknesses(db, head, body)


@router.get(
    "/{head_id}/{body_id}/expert-moves",
    response_model=list[FusionExpertMoveOut],
)
def get_fusion_expert_moves(head_id: int = _id_path(), body_id: int = _id_path(), db: Session = Depends(get_db)):
    """Moves teachable to this fusion by a Move Expert (Knot / Boon Island)."""
    head, body = _load_pair_or_404(db, head_id, body_id)
    return [_to_fusion_expert_move(r) for r in compute_fusion_expert_moves(db, head, body)]
