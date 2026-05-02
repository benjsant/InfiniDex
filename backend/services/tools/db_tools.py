"""DB-backed agent tools (PostgreSQL via SQLAlchemy).

All handlers are async for a uniform interface, even though the underlying
DB calls are synchronous — they return fast enough not to matter.
"""

from __future__ import annotations

import re

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
from backend.services.pokemon_service import get_pokemon_by_id, get_pokemon_locations, search_pokemon, search_pokemon_locations
from backend.services.triple_fusion_service import get_triple_fusion, list_triple_fusions
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


def _parse_location_notes(notes: str | None) -> dict:
    """Extract structured data from raw pokemon_location.notes strings.

    Format examples:
      "rate:20%|10%|5% | lv:23-26"  → rates per 3 game versions + level range
      "rate:35% | lv:32"             → single rate + fixed level
      "lv:75 | Legendary"            → level + free-text condition
      "Legendary"                    → condition only
    """
    if not notes:
        return {}
    result: dict = {}

    # Strip wiki table artifacts
    clean = re.sub(r'rowspan="\d+" \|', "", notes).strip()
    clean = re.sub(r"\s*\|-\s*$", "", clean).strip()

    # Extract rate:X%|Y%|Z% (three versions) or rate:X% (single)
    rate_match = re.search(r"rate:([\d%-]+(?:\|[\d%-]+)*)", clean)
    if rate_match:
        parts = rate_match.group(1).split("|")
        if len(parts) == 3:
            labels = ["v1", "v2", "v3"]
            result["encounter_rates"] = {
                labels[i]: (p.strip() if p.strip() != "-" else None)
                for i, p in enumerate(parts)
            }
        else:
            r = parts[0].strip()
            result["encounter_rate"] = r if r != "-" else None
        clean = clean[: rate_match.start()].strip(" |") + clean[rate_match.end():].strip(" |")

    # Extract lv:X or lv:X-Y
    lv_match = re.search(r"lv:(\d+)(?:-(\d+))?", clean)
    if lv_match:
        lo = int(lv_match.group(1))
        hi = int(lv_match.group(2)) if lv_match.group(2) else lo
        result["level_min"] = lo
        result["level_max"] = hi
        clean = clean[: lv_match.start()].strip(" |") + clean[lv_match.end():].strip(" |")

    # Extract respawn: tags
    respawns = re.findall(r"respawn:([\w]+)", clean)
    if respawns:
        result["respawn"] = respawns
        clean = re.sub(r"\s*\|\s*respawn:\w+", "", clean).strip()

    # Remaining text = condition
    condition = clean.strip(" |").strip()
    if condition:
        result["condition"] = condition

    return result


def _pokemon_payload(p: Pokemon, db: Session | None = None) -> dict:
    locations: list[dict] = []
    if db is not None:
        locs = get_pokemon_locations(db, p.id)
        locations = [
            {
                "location": loc.location.name_en,
                "method": loc.method,
                **_parse_location_notes(loc.notes),
            }
            for loc in locs
        ]
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
        "locations": locations,
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
        return _pokemon_payload(p, db)
    full = get_pokemon_by_id(db, p.id)
    return _pokemon_payload(full, db) if full else {"error": f"Pokémon id={p.id} vanished"}


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


async def _get_triple_fusion(db: Session, args: dict) -> dict:
    name_or_id = args.get("name_or_id")
    if name_or_id is None:
        return {"error": "Missing required arg 'name_or_id'"}

    tf = None
    if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and str(name_or_id).isdigit()):
        tf = get_triple_fusion(db, int(name_or_id))
    else:
        needle = str(name_or_id).lower().strip()
        for candidate in list_triple_fusions(db):
            if (candidate.name_en or "").lower() == needle or (candidate.name_fr or "").lower() == needle:
                tf = get_triple_fusion(db, candidate.id)
                break
        if tf is None:
            for candidate in list_triple_fusions(db):
                if needle in (candidate.name_en or "").lower() or needle in (candidate.name_fr or "").lower():
                    tf = get_triple_fusion(db, candidate.id)
                    break

    if tf is None:
        return {"error": f"No triple fusion matching '{name_or_id}'. Known triple fusions: Zapmolcuno, Enraicune, Kyodonquaza, Paldiatina, Zekyushiram, Celemewchi, Deosectwo, Regiregi, and starter trios."}

    return {
        "id": tf.id,
        "name_en": tf.name_en,
        "name_fr": tf.name_fr,
        "how_to_obtain": (
            "Triple fusions are post-game only. "
            "1) Bring the Black Stone and White Stone to Colress at the Lake of Rage. "
            "2) Catch Kyurem. "
            "3) Find Colress at Mt. Moon. "
            "4) Have the 3 required Pokémon in your party — Colress clones them and gives you an egg. "
            "Can only be done once per trio. Starter trios give an unevolved form that can evolve."
        ),
        "components": [
            {"position": c.position, "pokemon_id": c.pokemon_id, "name_en": c.pokemon.name_en, "name_fr": c.pokemon.name_fr}
            for c in sorted(tf.components, key=lambda x: x.position)
        ],
        "types": [
            {"name_en": t.type.name_en, "name_fr": t.type.name_fr, "is_special": t.type.is_triple_fusion_type}
            for t in sorted(tf.types, key=lambda x: x.slot)
        ],
        "stats": {
            "hp": tf.hp, "attack": tf.attack, "defense": tf.defense,
            "sp_attack": tf.sp_attack, "sp_defense": tf.sp_defense, "speed": tf.speed,
            "total": tf.hp + tf.attack + tf.defense + tf.sp_attack + tf.sp_defense + tf.speed,
        },
        "abilities": [
            {"name_en": a.ability.name_en, "name_fr": a.ability.name_fr, "is_hidden": a.is_hidden}
            for a in sorted(tf.abilities, key=lambda x: x.slot)
        ],
        "evolution_level": tf.evolution_level,
    }


async def _search_pokemon_locations(db: Session, args: dict) -> dict:
    condition = args.get("condition")
    method    = args.get("method")
    if not condition and not method:
        return {"error": "Provide at least one of 'condition' or 'method'"}
    rows = search_pokemon_locations(db, condition=condition, method=method)
    if not rows:
        return {"found": False, "condition": condition, "method": method, "results": []}
    return {
        "found": True,
        "count": len(rows),
        "results": [
            {
                "pokemon_id":   r.pokemon.id,
                "name_en":      r.pokemon.name_en,
                "name_fr":      r.pokemon.name_fr,
                "location":     r.location.name_en,
                "method":       r.method,
                **_parse_location_notes(r.notes),
            }
            for r in rows
        ],
    }


# ─── Tool instances ───────────────────────────────────────────────────────────

get_pokemon_tool = Tool(
    name="get_pokemon",
    description=(
        "Returns the Pokédex entry for an Infinite Fusion Pokémon: types, "
        "abilities (including hidden), base stats, generation, and encounter "
        "locations (where to find it in the game). Accepts a name (EN or FR) "
        "or an IF ID. Always call this first for any question about a specific Pokémon."
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
        "Search for an item by English name within the covered categories: "
        "fusion items (DNA Splicers, ...), evolution items (Fire Stone, ...), "
        "valuables (Heart Scale, Nugget, ...). Returns the effect and buy/sell "
        "prices. IMPORTANT: only English names are indexed — always translate "
        "French names before calling (e.g. 'pierre feu' → 'Fire Stone')."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Item name in English, partial match accepted"},
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

search_pokemon_locations_tool = Tool(
    name="search_pokemon_locations",
    description=(
        "Searches the game database for Pokémon filtered by encounter method and/or a condition keyword. "
        "Use for questions like 'where are the legendaries', 'what gift Pokémon exist', "
        "'which Pokémon can I get by trade', 'what can I catch fishing'. "
        "method values: 'wild' (random encounter), 'static' (one-time overworld), "
        "'gift' (NPCs that give you a Pokémon), 'trade' (NPC trades), 'fishing', 'headbutt'. "
        "condition keyword examples: 'Legendary' (all legendaries with respawn info), "
        "'Starter', 'Quest'. "
        "Returns each Pokémon's name, location, level, encounter rate, respawn rules, and notes."
    ),
    parameters={
        "type": "object",
        "properties": {
            "condition": {
                "type": "string",
                "description": "Keyword in encounter notes, e.g. 'Legendary', 'Quest', 'Starter'",
            },
            "method": {
                "type": "string",
                "description": "Encounter method: 'wild', 'static', 'gift', 'trade', 'fishing', 'headbutt'",
            },
        },
        "required": [],
    },
    handler=_search_pokemon_locations,
)

get_triple_fusion_tool = Tool(
    name="get_triple_fusion",
    description=(
        "Returns data on a Triple Fusion — secret legendary Pokémon exclusive to "
        "Infinite Fusion, obtained by fusing three Pokémon simultaneously (legendary trios "
        "or generation starters). Returns components (the 3 base Pokémon), types (including "
        "unique IF-exclusive types), stats, and abilities. "
        "Accepts a name (EN or FR) or an ID (1–23). "
        "Known examples: Zapmolcuno, Enraicune, Kyodonquaza, Paldiatina, Zekyushiram, "
        "Celemewchi, Deosectwo, Regiregi, and the starter trios (Venustoizard, Megaligasion, etc.)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name_or_id": {
                "type": ["string", "integer"],
                "description": "Triple fusion name (EN or FR) or ID (1–23), e.g. 'Zapmolcuno' or 1",
            }
        },
        "required": ["name_or_id"],
    },
    handler=_get_triple_fusion,
)
