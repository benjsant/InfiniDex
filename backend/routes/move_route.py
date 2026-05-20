"""API routes for moves."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.move import MoveDetail, MoveExpertOut, MoveListItem, MoveTutorOut, PokemonMoveOut, TMInfo, TMListItem, TMLocationOut
from backend.schemas.type_ import TypeOut
from backend.services.move_service import (
    get_move_by_id,
    get_tm_by_number,
    get_tm_for_move,
    list_all_expert_moves,
    list_all_tms,
    list_all_tutors,
    list_moves,
    list_moves_by_type,
    list_tutors_for_move,
    search_moves,
)

router = APIRouter(prefix="/moves", tags=["Moves"])
tms_router = APIRouter(prefix="/tms", tags=["TMs"])


def _tm_to_schema(tm) -> TMListItem:
    locations = [
        TMLocationOut(
            location_id=tl.location_id,
            location_name_en=tl.location.name_en,
            location_name_fr=tl.location.name_fr,
            notes=tl.notes,
        )
        for tl in tm.locations
    ]
    summary_parts = [
        f"{loc.location_name_en} ({loc.notes})" if loc.notes else loc.location_name_en
        for loc in locations
    ]
    return TMListItem(
        number=tm.number,
        move_id=tm.move_id,
        name_en=tm.move.name_en,
        name_fr=tm.move.name_fr,
        type=TypeOut.from_model(tm.move.type),
        category=tm.move.category,
        power=tm.move.power,
        accuracy=tm.move.accuracy,
        pp=tm.move.pp,
        location_summary=", ".join(summary_parts) or None,
        locations=locations,
    )


@tms_router.get("/", response_model=list[TMListItem])
def get_all_tms(db: Session = Depends(get_db)):
    """All 121 TMs ordered by number, with move info and obtention locations."""
    return [_tm_to_schema(tm) for tm in list_all_tms(db)]


@tms_router.get("/{number}", response_model=TMListItem)
def get_tm(number: int = Path(..., ge=1, le=200), db: Session = Depends(get_db)):
    """Single TM by its number (e.g. 1 = TM01, 121 = TM121)."""
    tm = get_tm_by_number(db, number)
    if not tm:
        raise HTTPException(status_code=404, detail=f"TM{number:03d} not found")
    return _tm_to_schema(tm)


def _tutor_to_schema(t) -> MoveTutorOut:
    return MoveTutorOut(
        id=t.id,
        move_id=t.move_id,
        move_name_en=t.move.name_en,
        move_name_fr=t.move.name_fr,
        location_id=t.location_id,
        location_name_en=t.location.name_en,
        location_name_fr=t.location.name_fr,
        price=t.price,
        currency=t.currency,
        npc_description=t.npc_description,
    )


def _move_to_list_item(m) -> MoveListItem:
    return MoveListItem(
        id=m.id,
        name_en=m.name_en,
        name_fr=m.name_fr,
        category=m.category,
        power=m.power,
        accuracy=m.accuracy,
        pp=m.pp,
        type=TypeOut.from_model(m.type),
    )


@router.get("/", response_model=list[MoveListItem])
def get_moves(
    db: Session = Depends(get_db),
    category: str | None = Query(None, pattern="^(Physical|Special|Status)$"),
    type_id: int | None = Query(None, ge=1),
    power_min: int | None = Query(None, ge=0),
    power_max: int | None = Query(None, ge=0),
    limit: int | None = Query(None, ge=1, le=1000),
    offset: int = Query(0, ge=0, le=100_000),
):
    """List moves with optional filters (category/type/power/pagination)."""
    moves = list_moves(
        db,
        category=category,
        type_id=type_id,
        power_min=power_min,
        power_max=power_max,
        limit=limit,
        offset=offset,
    )
    return [_move_to_list_item(m) for m in moves]


@router.get("/search", response_model=list[MoveListItem])
def search_moves_route(
    q: str = Query(..., min_length=1, max_length=100, description="Partial name EN or FR (accent-insensitive)"),
    db: Session = Depends(get_db),
):
    """Accent-insensitive search on EN or FR move name."""
    return [_move_to_list_item(m) for m in search_moves(db, q)]


@router.get("/by-type/{type_name}", response_model=list[MoveListItem])
def get_moves_by_type(type_name: str = Path(..., min_length=1, max_length=50), db: Session = Depends(get_db)):
    """All moves of a given type (EN or FR name, case-insensitive prefix match)."""
    moves = list_moves_by_type(db, type_name)
    if not moves:
        raise HTTPException(status_code=404, detail=f"No moves found for type '{type_name}'")
    return [_move_to_list_item(m) for m in moves]


@router.get("/tutors/all", response_model=list[MoveTutorOut])
def get_all_tutors(db: Session = Depends(get_db)):
    """All classic move tutors grouped by location, ordered by price."""
    return [_tutor_to_schema(t) for t in list_all_tutors(db)]


@router.get("/experts/all", response_model=list[MoveExpertOut])
def get_all_expert_moves(db: Session = Depends(get_db)):
    """All Move Expert moves (Knot Island / Boon Island) with unlock conditions."""
    return list_all_expert_moves(db)


@router.get("/{move_id}/tutors", response_model=list[MoveTutorOut])
def get_move_tutors(move_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    """Locations and prices where this move can be learned from a classic Move Tutor.

    Returns an empty list if no tutor teaches this move. Scope: classic tutors
    only (one NPC = one move). Out of scope: Move Experts (fusion-only),
    Move Relearner, Move Deleter, Egg Move Tutor.
    """
    return [_tutor_to_schema(t) for t in list_tutors_for_move(db, move_id)]


@router.get("/{move_id}", response_model=MoveDetail)
def get_move(move_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    """Full detail of a move. Includes `tm` if the move is a TM."""
    move = get_move_by_id(db, move_id)
    if not move:
        raise HTTPException(status_code=404, detail="Move not found")

    tm_info: TMInfo | None = None
    tm = get_tm_for_move(db, move.id)
    if tm is not None:
        tm_locations = [
            TMLocationOut(
                location_id=tl.location_id,
                location_name_en=tl.location.name_en,
                location_name_fr=tl.location.name_fr,
                notes=tl.notes,
            )
            for tl in tm.locations
        ]
        # Build location_summary from FK rows (no longer stored in tm.location).
        summary_parts = [
            f"{tl.location_name_en} ({tl.notes})" if tl.notes else tl.location_name_en
            for tl in tm_locations
        ]
        tm_info = TMInfo(
            number=tm.number,
            location_summary=", ".join(summary_parts) or None,
            locations=tm_locations,
        )

    return MoveDetail(
        id=move.id,
        name_en=move.name_en,
        name_fr=move.name_fr,
        category=move.category,
        power=move.power,
        accuracy=move.accuracy,
        pp=move.pp,
        description_en=move.description_en,
        description_fr=move.description_fr,
        source=move.source,
        type=TypeOut.from_model(move.type),
        tm=tm_info,
    )
