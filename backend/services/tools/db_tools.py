"""DB-backed agent tools (PostgreSQL via SQLAlchemy).

All handlers are async for a uniform interface, even though the underlying
DB calls are synchronous — they return fast enough not to matter.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.db.models import Item, Move, Pokemon
from backend.services.fusion_service import (
    MOVE_EXPERT_PRICES_HEART_SCALES,
    compute_fusion_abilities,
    compute_fusion_expert_moves,
    compute_fusion_from_objects,
    load_pokemon_for_fusion,
)
from backend.services.item_service import search_items
from backend.services.move_service import (
    get_tm_for_move,
    list_tutors_for_move,
    search_moves,
)
from backend.services.pokemon_service import get_pokemon_by_id, search_pokemon
from backend.services.tools._base import Tool


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _resolve_pokemon(db: Session, name_or_id: str | int) -> Pokemon | dict:
    if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
        p = get_pokemon_by_id(db, int(name_or_id))
        return p if p else {"error": f"No Pokémon with id={name_or_id}"}
    needle = str(name_or_id).lower().strip()
    matches = search_pokemon(db, str(name_or_id))
    if not matches:
        return {"error": f"No Pokémon matching name '{name_or_id}'"}
    for p in matches:
        if (p.name_en or "").lower() == needle or (p.name_fr or "").lower() == needle:
            return p
    return matches[0]


def _resolve_to_id(db: Session, name_or_id: str | int) -> int | dict:
    """Resolve a name or ID to an integer pokemon_id without loading the full object."""
    if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
        return int(name_or_id)
    needle = str(name_or_id).lower().strip()
    matches = search_pokemon(db, str(name_or_id))
    if not matches:
        return {"error": f"No Pokémon matching name '{name_or_id}'"}
    for p in matches:
        if (p.name_en or "").lower() == needle or (p.name_fr or "").lower() == needle:
            return p.id
    return matches[0].id


def _resolve_move(db: Session, name_or_id: str | int) -> Move | dict:
    if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
        m = db.query(Move).filter(Move.id == int(name_or_id)).first()
        return m if m else {"error": f"No move with id={name_or_id}"}
    needle = str(name_or_id).lower().strip()
    matches = search_moves(db, str(name_or_id))
    if not matches:
        return {"error": f"No move matching name '{name_or_id}'"}
    for m in matches:
        if (m.name_en or "").lower() == needle or (m.name_fr or "").lower() == needle:
            return m
    return matches[0]


def _pokemon_payload(p: Pokemon) -> dict:
    return {
        "id": p.id,
        "name_en": p.name_en,
        "name_fr": p.name_fr,
        "types": [pt.type.name_en for pt in sorted(p.types, key=lambda x: x.slot)],
        "abilities": [
            {"name_en": pa.ability.name_en, "is_hidden": pa.is_hidden}
            for pa in sorted(p.abilities, key=lambda x: x.slot)
        ],
        "stats": {
            "hp": p.hp, "attack": p.attack, "defense": p.defense,
            "sp_attack": p.sp_attack, "sp_defense": p.sp_defense, "speed": p.speed,
        },
        "generation_id": p.generation_id,
    }


# ─── Handlers ─────────────────────────────────────────────────────────────────

async def _get_pokemon(db: Session, args: dict) -> dict:
    name_or_id = args.get("name_or_id")
    if name_or_id is None:
        return {"error": "Missing required arg 'name_or_id'"}
    p = _resolve_pokemon(db, name_or_id)
    if isinstance(p, dict):
        return p
    # ID lookup: _resolve_pokemon already called get_pokemon_by_id (types+abilities
    # eager-loaded) — reuse directly. Name lookup: search_pokemon only loads types,
    # so we need one extra fetch to get abilities.
    is_id = isinstance(name_or_id, int) or (
        isinstance(name_or_id, str) and name_or_id.isdigit()
    )
    if is_id:
        return _pokemon_payload(p)
    full = get_pokemon_by_id(db, p.id)
    return _pokemon_payload(full) if full else {"error": f"Pokémon id={p.id} vanished"}


async def _get_fusion(db: Session, args: dict) -> dict:
    head, body = args.get("head"), args.get("body")
    if head is None or body is None:
        return {"error": "Missing required args 'head' and/or 'body'"}

    # Resolve names/IDs to integer IDs first (search only — no full object load).
    head_id = _resolve_to_id(db, head)
    body_id = _resolve_to_id(db, body)
    if isinstance(head_id, dict):
        return {"error": f"head: {head_id['error']}"}
    if isinstance(body_id, dict):
        return {"error": f"body: {body_id['error']}"}

    # Single load per Pokémon: types (+ Type) + abilities (+ Ability) in one query.
    # Replaces the previous _resolve_pokemon + load_pokemon_with_types + compute_fusion
    # chain which issued up to 6 redundant queries for the same two rows.
    head_obj = load_pokemon_for_fusion(db, head_id)
    body_obj = load_pokemon_for_fusion(db, body_id)
    if not head_obj:
        return {"error": f"head: No Pokémon with id={head_id}"}
    if not body_obj:
        return {"error": f"body: No Pokémon with id={body_id}"}

    fusion = compute_fusion_from_objects(head_obj, body_obj)
    abilities = compute_fusion_abilities(db, head_obj, body_obj)
    expert_moves = compute_fusion_expert_moves(db, head_obj, body_obj)
    return {
        "head": {"id": head_obj.id, "name_en": head_obj.name_en, "name_fr": head_obj.name_fr},
        "body": {"id": body_obj.id, "name_en": body_obj.name_en, "name_fr": body_obj.name_fr},
        "stats": {
            "hp": fusion["hp"], "attack": fusion["attack"], "defense": fusion["defense"],
            "sp_attack": fusion["sp_attack"], "sp_defense": fusion["sp_defense"],
            "speed": fusion["speed"],
        },
        "types": [t.name_en for t in (fusion["type1"], fusion["type2"]) if t],
        "abilities": [
            {"name_en": a["name_en"], "origin": a["origin"], "is_hidden": a["is_hidden"]}
            for a in abilities
        ],
        "expert_moves": [
            {
                "name_en": m["name_en"], "type": m["type"].name_en,
                "locations": m["locations"], "prices_heart_scales": m["prices_heart_scales"],
            }
            for m in expert_moves
        ],
        "expert_pricing_note": f"Heart Scales per move: {MOVE_EXPERT_PRICES_HEART_SCALES}",
    }


async def _search_move(db: Session, args: dict) -> dict:
    name = args.get("name")
    if not name:
        return {"error": "Missing required arg 'name'"}
    m = _resolve_move(db, name)
    if isinstance(m, dict):
        return m
    tm = get_tm_for_move(db, m.id)
    tutors = list_tutors_for_move(db, m.id)
    return {
        "id": m.id, "name_en": m.name_en, "name_fr": m.name_fr,
        "type": m.type.name_en, "category": m.category,
        "power": m.power, "accuracy": m.accuracy, "pp": m.pp,
        "description_en": m.description_en,
        "tm": (
            {
                "number": tm.number,
                "locations": [
                    {"name_en": tl.location.name_en, "notes": tl.notes}
                    for tl in tm.locations
                ],
            }
            if tm else None
        ),
        "tutors": [
            {"location": t.location.name_en, "price": t.price,
             "currency": t.currency, "npc": t.npc_description}
            for t in tutors
        ],
    }


async def _get_item(db: Session, args: dict) -> dict:
    name = args.get("name")
    if not name:
        return {"error": "Missing required arg 'name'"}
    matches: list[Item] = search_items(db, str(name))
    if not matches:
        return {"error": f"No item matching '{name}'"}
    it = matches[0]
    return {
        "id": it.id, "name_en": it.name_en, "category": it.category,
        "effect": it.effect, "price_buy": it.price_buy, "price_sell": it.price_sell,
    }


async def _get_move_tutors(db: Session, args: dict) -> dict:
    name = args.get("move_name")
    if not name:
        return {"error": "Missing required arg 'move_name'"}
    m = _resolve_move(db, name)
    if isinstance(m, dict):
        return m
    tutors = list_tutors_for_move(db, m.id)
    return {
        "move": {"id": m.id, "name_en": m.name_en, "name_fr": m.name_fr},
        "tutors": [
            {"location": t.location.name_en, "price": t.price,
             "currency": t.currency, "npc": t.npc_description}
            for t in tutors
        ],
    }


# ─── Tool instances ───────────────────────────────────────────────────────────

get_pokemon_tool = Tool(
    name="get_pokemon",
    description=(
        "Returns the Pokédex entry for an Infinite Fusion Pokémon: types, "
        "abilities (including hidden), base stats, generation. Accepts "
        "a name (EN or FR) or an IF ID."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name_or_id": {
                "type": ["string", "integer"],
                "description": "EN/FR name (e.g. 'Pikachu') or IF ID (e.g. 25)",
            }
        },
        "required": ["name_or_id"],
    },
    handler=_get_pokemon,
)

get_fusion_tool = Tool(
    name="get_fusion",
    description=(
        "Computes a head × body fusion: stats, types, abilities, and "
        "moves teachable by Move Experts with their Heart Scale prices "
        "(Knot = 2, Boon = 10). Parameters: name or ID of each Pokémon."
    ),
    parameters={
        "type": "object",
        "properties": {
            "head": {"type": ["string", "integer"], "description": "Head Pokémon (EN/FR name or IF ID)"},
            "body": {"type": ["string", "integer"], "description": "Body Pokémon (EN/FR name or IF ID)"},
        },
        "required": ["head", "body"],
    },
    handler=_get_fusion,
)

search_move_tool = Tool(
    name="search_move",
    description=(
        "Search for a move by name (EN/FR, accent-insensitive). "
        "Returns the detail (type, category, power, accuracy, PP, "
        "description), plus TM info (if this move is a TM) and the "
        "list of classic Move Tutors that teach it."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Move name (EN or FR), partial match accepted"},
        },
        "required": ["name"],
    },
    handler=_search_move,
)

get_item_tool = Tool(
    name="get_item",
    description=(
        "Search for an item by name within the covered categories: "
        "fusion items (DNA Splicers, ...), evolution items (Fire "
        "Stone, ...), valuables (Heart Scale, Nugget, ...). Returns "
        "the effect and buy/sell prices."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Item name (EN), partial match accepted"},
        },
        "required": ["name"],
    },
    handler=_get_item,
)

get_move_tutors_tool = Tool(
    name="get_move_tutors",
    description=(
        "List classic Move Tutors (NPCs) that teach a given move, "
        "with their location and price (in Pokédollars, free, or "
        "quest). Does not cover Move Experts on Knot/Boon Islands, "
        "which are exposed via get_fusion."
    ),
    parameters={
        "type": "object",
        "properties": {
            "move_name": {"type": "string", "description": "Move name (EN or FR)"},
        },
        "required": ["move_name"],
    },
    handler=_get_move_tutors,
)
