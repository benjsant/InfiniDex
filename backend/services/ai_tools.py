"""AI tools — specs + handlers exposés à un LLM via function calling.

Contient :
- `TOOL_SPECS` : liste de définitions JSON Schema (format OpenAI / DeepSeek)
  passée au modèle pour qu'il sache quels tools il peut appeler.
- `TOOL_HANDLERS` : mapping `tool_name → callable(db, args) -> dict`. Chaque
  handler renvoie un payload JSON-serializable qui sera ré-injecté dans
  la conversation côté LLM.
- `dispatch_tool(db, name, args)` : entry-point unique.

Conception :
- Les handlers s'appuient sur les services existants (pokemon/fusion/
  move/item), **pas** directement sur SQLAlchemy.
- Les payloads restent compacts mais auto-suffisants (noms EN + FR, IDs,
  prix, types), pour éviter des tool calls en cascade inutiles.
- Les tools acceptent *name OR id* pour s'adapter à l'usage LLM (qui
  manipule plus facilement des noms que des IDs).
- Toute erreur (Pokémon inexistant, move ambigu, …) est renvoyée comme
  dict `{"error": "..."}` plutôt que via une exception → le LLM peut
  raisonner dessus et informer l'utilisateur.
"""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy.orm import Session

from backend.services.wiki_service import fetch_wiki

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


# ─── Helpers internes ────────────────────────────────────────────────────────

def _resolve_pokemon(db: Session, name_or_id: str | int) -> Pokemon | dict:
    """Accept int (id) or str (name). Return Pokemon or {'error': ...} dict."""
    if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
        pid = int(name_or_id)
        p = get_pokemon_by_id(db, pid)
        if not p:
            return {"error": f"No Pokémon with id={pid}"}
        return p
    # string → name search (ILIKE, returns list)
    needle = str(name_or_id).lower().strip()
    matches = search_pokemon(db, str(name_or_id))
    if not matches:
        return {"error": f"No Pokémon matching name '{name_or_id}'"}
    # Prefer an exact name match (EN or FR) if one exists.
    for p in matches:
        if (p.name_en or "").lower() == needle or (p.name_fr or "").lower() == needle:
            return p
    return matches[0]


def _resolve_move(db: Session, name_or_id: str | int) -> Move | dict:
    if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
        mid = int(name_or_id)
        m = db.query(Move).filter(Move.id == mid).first()
        if not m:
            return {"error": f"No move with id={mid}"}
        return m
    needle = str(name_or_id).lower().strip()
    matches = search_moves(db, str(name_or_id))
    if not matches:
        return {"error": f"No move matching name '{name_or_id}'"}
    # Prefer an exact name match (EN or FR) if one exists, else top partial.
    for m in matches:
        if (m.name_en or "").lower() == needle or (m.name_fr or "").lower() == needle:
            return m
    return matches[0]


def _pokemon_to_payload(p: Pokemon) -> dict:
    """Compact dict for LLM consumption."""
    return {
        "id": p.id,
        "name_en": p.name_en,
        "name_fr": p.name_fr,
        "types": [pt.type.name_en for pt in sorted(p.types, key=lambda x: x.slot)],
        "abilities": [
            {
                "name_en": pa.ability.name_en,
                "is_hidden": pa.is_hidden,
            }
            for pa in sorted(p.abilities, key=lambda x: x.slot)
        ],
        "stats": {
            "hp": p.hp,
            "attack": p.attack,
            "defense": p.defense,
            "sp_attack": p.sp_attack,
            "sp_defense": p.sp_defense,
            "speed": p.speed,
        },
        "generation_id": p.generation_id,
    }


# ─── Handlers ────────────────────────────────────────────────────────────────

def get_pokemon(db: Session, args: dict) -> dict:
    """Return Pokémon sheet (types, abilities, stats)."""
    name_or_id = args.get("name_or_id")
    if name_or_id is None:
        return {"error": "Missing required arg 'name_or_id'"}
    p = _resolve_pokemon(db, name_or_id)
    if isinstance(p, dict):
        return p
    # Full sheet requires abilities eager-loaded
    full = get_pokemon_by_id(db, p.id)
    if full is None:
        return {"error": f"Pokémon id={p.id} vanished mid-lookup"}
    return _pokemon_to_payload(full)


def get_fusion(db: Session, args: dict) -> dict:
    """Return fusion stats, types, abilities, and Move Expert moves (with prices)."""
    head = args.get("head")
    body = args.get("body")
    if head is None or body is None:
        return {"error": "Missing required args 'head' and/or 'body'"}

    head_p = _resolve_pokemon(db, head)
    body_p = _resolve_pokemon(db, body)
    if isinstance(head_p, dict):
        return {"error": f"head: {head_p.get('error')}"}
    if isinstance(body_p, dict):
        return {"error": f"body: {body_p.get('error')}"}

    # Load types for fusion math
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
            "hp":         fusion["hp"],
            "attack":     fusion["attack"],
            "defense":    fusion["defense"],
            "sp_attack":  fusion["sp_attack"],
            "sp_defense": fusion["sp_defense"],
            "speed":      fusion["speed"],
        },
        "types": [t.name_en for t in (fusion["type1"], fusion["type2"]) if t],
        "abilities": [
            {"name_en": a["name_en"], "origin": a["origin"], "is_hidden": a["is_hidden"]}
            for a in abilities
        ],
        "expert_moves": [
            {
                "name_en": m["name_en"],
                "type": m["type"].name_en,
                "locations": m["locations"],
                "prices_heart_scales": m["prices_heart_scales"],
            }
            for m in expert_moves
        ],
        "expert_pricing_note": f"Heart Scales per move: {MOVE_EXPERT_PRICES_HEART_SCALES}",
    }


def search_move(db: Session, args: dict) -> dict:
    """Search moves by name (accent-insensitive). Returns top match with TM + tutor info."""
    name = args.get("name")
    if not name:
        return {"error": "Missing required arg 'name'"}

    m = _resolve_move(db, name)
    if isinstance(m, dict):
        return m

    tm = get_tm_for_move(db, m.id)
    tutors = list_tutors_for_move(db, m.id)

    return {
        "id": m.id,
        "name_en": m.name_en,
        "name_fr": m.name_fr,
        "type": m.type.name_en,
        "category": m.category,
        "power": m.power,
        "accuracy": m.accuracy,
        "pp": m.pp,
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
            {
                "location": t.location.name_en,
                "price": t.price,
                "currency": t.currency,
                "npc": t.npc_description,
            }
            for t in tutors
        ],
    }


def get_item(db: Session, args: dict) -> dict:
    """Return item info (effect, prices)."""
    name = args.get("name")
    if not name:
        return {"error": "Missing required arg 'name'"}

    matches: list[Item] = search_items(db, str(name))
    if not matches:
        return {"error": f"No item matching '{name}'"}

    it = matches[0]
    return {
        "id": it.id,
        "name_en": it.name_en,
        "category": it.category,
        "effect": it.effect,
        "price_buy": it.price_buy,
        "price_sell": it.price_sell,
    }


def get_move_tutors(db: Session, args: dict) -> dict:
    """List classic Move Tutors for a given move name/id."""
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
            {
                "location": t.location.name_en,
                "price": t.price,
                "currency": t.currency,
                "npc": t.npc_description,
            }
            for t in tutors
        ],
    }


# ─── Specs JSON Schema (format OpenAI / DeepSeek) ────────────────────────────

TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_pokemon",
            "description": (
                "Retourne la fiche d'un Pokémon d'Infinite Fusion : types, "
                "abilities (dont hidden), stats de base, génération. Accepte "
                "un nom (EN ou FR) ou un ID IF."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name_or_id": {
                        "type": ["string", "integer"],
                        "description": "Nom EN/FR (ex: 'Pikachu') ou ID IF (ex: 25)",
                    }
                },
                "required": ["name_or_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fusion",
            "description": (
                "Calcule une fusion head × body : stats, types, abilities, et "
                "moves enseignables par les Move Experts avec les prix en "
                "Heart Scales (Knot = 2, Boon = 10). Paramètres : nom ou ID "
                "de chaque Pokémon."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "head": {
                        "type": ["string", "integer"],
                        "description": "Pokémon tête (nom EN/FR ou ID IF)",
                    },
                    "body": {
                        "type": ["string", "integer"],
                        "description": "Pokémon corps (nom EN/FR ou ID IF)",
                    },
                },
                "required": ["head", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_move",
            "description": (
                "Cherche un move par nom (EN/FR, insensible aux accents). "
                "Retourne le détail (type, catégorie, puissance, précision, "
                "PP, description), plus les infos TM (si ce move est une CT) "
                "et la liste des Move Tutors classiques qui l'enseignent."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Nom du move (EN ou FR), partiel accepté",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_item",
            "description": (
                "Cherche un item par nom dans les catégories couvertes : "
                "fusion items (DNA Splicers, ...), evolution items (Fire "
                "Stone, ...), valuables (Heart Scale, Nugget, ...). Retourne "
                "l'effet et les prix d'achat/revente."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Nom de l'item (EN), partiel accepté",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_move_tutors",
            "description": (
                "Liste les Move Tutors classiques (NPCs) qui enseignent un "
                "move donné, avec leur lieu et leur prix (en Pokédollars, "
                "gratuit, ou quête). Ne couvre pas les Move Experts des "
                "Knot/Boon Islands qui sont exposés via get_fusion."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "move_name": {
                        "type": "string",
                        "description": "Nom du move (EN ou FR)",
                    }
                },
                "required": ["move_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_wiki",
            "description": (
                "Cherche une page sur le wiki officiel de Pokémon Infinite "
                "Fusion (infinitefusion.fandom.com). À utiliser quand les "
                "tools BDD ne couvrent pas la question : mécaniques de jeu, "
                "lore, quêtes, patches, fonctionnalités spécifiques au "
                "fan-game. Retourne l'intro de la meilleure page trouvée."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Termes de recherche en anglais (le wiki est en EN). "
                            "Ex: 'Safari Zone', 'Wonder Trade', 'Randomizer mode'"
                        ),
                    }
                },
                "required": ["query"],
            },
        },
    },
]


TOOL_HANDLERS: dict[str, Callable[[Session, dict], dict]] = {
    "get_pokemon":      get_pokemon,
    "get_fusion":       get_fusion,
    "search_move":      search_move,
    "get_item":         get_item,
    "get_move_tutors":  get_move_tutors,
}


# ─── Async handlers (tools requiring I/O outside the DB) ─────────────────────

async def _search_wiki(db: Session, args: dict) -> dict:
    """Async handler — proxies to wiki_service.fetch_wiki."""
    query = args.get("query")
    if not query:
        return {"error": "Missing required arg 'query'"}
    return await fetch_wiki(str(query))


ASYNC_TOOL_HANDLERS: dict[str, Callable] = {
    "search_wiki": _search_wiki,
}


async def dispatch_tool(db: Session, name: str, args: dict[str, Any]) -> dict:
    """Central entry-point : resolve `name` to a handler and invoke it.

    Async because some tools (search_wiki) perform network I/O.
    Returns `{"error": "..."}` if the tool name is unknown.
    """
    async_handler = ASYNC_TOOL_HANDLERS.get(name)
    if async_handler is not None:
        return await async_handler(db, args)
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool '{name}'"}
    return handler(db, args)
