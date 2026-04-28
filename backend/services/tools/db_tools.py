"""DB-backed agent tools (PostgreSQL via SQLAlchemy).

All handlers are async for a uniform interface, even though the underlying
DB calls are synchronous — they return fast enough not to matter.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.db.models import Item, Move, Pokemon
from backend.services.fusion_service import (
    MOVE_EXPERT_PRICES_HEART_SCALES,
    compute_fusion,
    compute_fusion_abilities,
    compute_fusion_expert_moves,
    load_pokemon_with_types,
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
    full = get_pokemon_by_id(db, p.id)
    return _pokemon_payload(full) if full else {"error": f"Pokémon id={p.id} vanished"}


async def _get_fusion(db: Session, args: dict) -> dict:
    head, body = args.get("head"), args.get("body")
    if head is None or body is None:
        return {"error": "Missing required args 'head' and/or 'body'"}
    head_p = _resolve_pokemon(db, head)
    body_p = _resolve_pokemon(db, body)
    if isinstance(head_p, dict):
        return {"error": f"head: {head_p['error']}"}
    if isinstance(body_p, dict):
        return {"error": f"body: {body_p['error']}"}
    head_full = load_pokemon_with_types(db, head_p.id)
    body_full = load_pokemon_with_types(db, body_p.id)
    assert head_full and body_full
    fusion = compute_fusion(db, head_p.id, body_p.id)
    abilities = compute_fusion_abilities(db, head_full, body_full)
    expert_moves = compute_fusion_expert_moves(db, head_full, body_full)
    return {
        "head": {"id": head_p.id, "name_en": head_p.name_en, "name_fr": head_p.name_fr},
        "body": {"id": body_p.id, "name_en": body_p.name_en, "name_fr": body_p.name_fr},
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
        "Retourne la fiche d'un Pokémon d'Infinite Fusion : types, "
        "abilities (dont hidden), stats de base, génération. Accepte "
        "un nom (EN ou FR) ou un ID IF."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name_or_id": {
                "type": ["string", "integer"],
                "description": "Nom EN/FR (ex: 'Pikachu') ou ID IF (ex: 25)",
            }
        },
        "required": ["name_or_id"],
    },
    handler=_get_pokemon,
)

get_fusion_tool = Tool(
    name="get_fusion",
    description=(
        "Calcule une fusion head × body : stats, types, abilities, et "
        "moves enseignables par les Move Experts avec les prix en "
        "Heart Scales (Knot = 2, Boon = 10). Paramètres : nom ou ID "
        "de chaque Pokémon."
    ),
    parameters={
        "type": "object",
        "properties": {
            "head": {"type": ["string", "integer"], "description": "Pokémon tête (nom EN/FR ou ID IF)"},
            "body": {"type": ["string", "integer"], "description": "Pokémon corps (nom EN/FR ou ID IF)"},
        },
        "required": ["head", "body"],
    },
    handler=_get_fusion,
)

search_move_tool = Tool(
    name="search_move",
    description=(
        "Cherche un move par nom (EN/FR, insensible aux accents). "
        "Retourne le détail (type, catégorie, puissance, précision, "
        "PP, description), plus les infos TM (si ce move est une CT) "
        "et la liste des Move Tutors classiques qui l'enseignent."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Nom du move (EN ou FR), partiel accepté"},
        },
        "required": ["name"],
    },
    handler=_search_move,
)

get_item_tool = Tool(
    name="get_item",
    description=(
        "Cherche un item par nom dans les catégories couvertes : "
        "fusion items (DNA Splicers, ...), evolution items (Fire "
        "Stone, ...), valuables (Heart Scale, Nugget, ...). Retourne "
        "l'effet et les prix d'achat/revente."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Nom de l'item (EN), partiel accepté"},
        },
        "required": ["name"],
    },
    handler=_get_item,
)

get_move_tutors_tool = Tool(
    name="get_move_tutors",
    description=(
        "Liste les Move Tutors classiques (NPCs) qui enseignent un "
        "move donné, avec leur lieu et leur prix (en Pokédollars, "
        "gratuit, ou quête). Ne couvre pas les Move Experts des "
        "Knot/Boon Islands qui sont exposés via get_fusion."
    ),
    parameters={
        "type": "object",
        "properties": {
            "move_name": {"type": "string", "description": "Nom du move (EN ou FR)"},
        },
        "required": ["move_name"],
    },
    handler=_get_move_tutors,
)
