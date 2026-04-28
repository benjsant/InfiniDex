"""Fusion stat computation service.

Formulas (Pokémon Infinite Fusion):
  Physical stats (HP, Attack, Defense, Speed) = floor(Body×2/3 + Head×1/3)
  Special stats (Sp.Atk, Sp.Def)              = floor(Head×2/3 + Body×1/3)

Types — canonical rules derived from the IF script `FusedSpecies.rb`
(calculate_type1 / calculate_type2):
  type1 = head.type1
         Exception: if head is pure Normal/Flying → use type2 (Flying) instead.
  type2 = body.type2 if defined (or body.type1 for mono-types),
         unless that value is identical to type1 — in which case we
         fall back to body.type1.
  If type2 ends up identical to type1 → omit it (mono-type fusion).
"""

from __future__ import annotations

import math
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from backend.db.models import (
    Move,
    MoveExpertMove,
    Pokemon,
    PokemonAbility,
    PokemonMove,
    PokemonType,
    Type,
    TypeEffectiveness,
)


def load_pokemon_with_types(db: Session, pid: int) -> Pokemon | None:
    """Load a Pokémon + types (slot1/slot2) eagerly loaded. Public: reused by `fusion_route`."""
    return (
        db.query(Pokemon)
        .options(joinedload(Pokemon.types).joinedload(PokemonType.type))
        .filter(Pokemon.id == pid)
        .first()
    )


def load_pokemon_for_fusion(db: Session, pid: int) -> Pokemon | None:
    """Load a Pokémon with types (→ Type) AND abilities (→ Ability) in a single query.

    Used by the AI agent tool to avoid separate loads for stat computation,
    type resolution, and ability listing.
    """
    return (
        db.query(Pokemon)
        .options(
            joinedload(Pokemon.types).joinedload(PokemonType.type),
            joinedload(Pokemon.abilities).joinedload(PokemonAbility.ability),
        )
        .filter(Pokemon.id == pid)
        .first()
    )


def compute_fusion_from_objects(head: Pokemon, body: Pokemon) -> dict:
    """Same as compute_fusion but takes already-loaded Pokemon objects.

    Avoids two extra load_pokemon_with_types queries when the caller
    already has the objects (e.g. the AI agent tool).
    """
    def phys(b: int, h: int) -> int:
        return math.floor(b * 2 / 3 + h * 1 / 3)

    def spec(h: int, b: int) -> int:
        return math.floor(h * 2 / 3 + b * 1 / 3)

    type1_obj, type2_obj = compute_fusion_types(head, body)

    return {
        "head_id":       head.id,
        "body_id":       body.id,
        "head_name_en":  head.name_en,
        "head_name_fr":  head.name_fr,
        "body_name_en":  body.name_en,
        "body_name_fr":  body.name_fr,
        "hp":            phys(body.hp,        head.hp),
        "attack":        phys(body.attack,    head.attack),
        "defense":       phys(body.defense,   head.defense),
        "speed":         phys(body.speed,     head.speed),
        "sp_attack":     spec(head.sp_attack,  body.sp_attack),
        "sp_defense":    spec(head.sp_defense, body.sp_defense),
        "type1":         type1_obj,
        "type2":         type2_obj,
        "sprite_path":   f"{head.id}.{body.id}.png",
    }


NORMAL_TYPE_EN = "Normal"
FLYING_TYPE_EN = "Flying"

# Uniform price per expert (source: IF wiki — List_of_Move_Expert_Moves).
# Knot Island = 2 Heart Scales/move, Boon Island = 10 Heart Scales/move.
MOVE_EXPERT_PRICES_HEART_SCALES: dict[str, int] = {
    "knot_island": 2,
    "boon_island": 10,
}


def _slot_types(p: Pokemon) -> tuple[Type | None, Type | None]:
    """Return (type_slot1, type_slot2) for a Pokémon (type2 is None for mono-type)."""
    by_slot = {pt.slot: pt.type for pt in p.types}
    return by_slot.get(1), by_slot.get(2)


def compute_fusion_types(head: Pokemon, body: Pokemon) -> tuple[Type | None, Type | None]:
    """Compute (type1, type2) according to Infinite Fusion rules.

    See the module docstring for the full specification.
    """
    head_t1, head_t2 = _slot_types(head)
    body_t1, body_t2 = _slot_types(body)

    # type1 = head.type1, with Normal/Flying exception → Flying
    if (
        head_t1 is not None
        and head_t2 is not None
        and head_t1.name_en == NORMAL_TYPE_EN
        and head_t2.name_en == FLYING_TYPE_EN
    ):
        type1 = head_t2
    else:
        type1 = head_t1

    # type2 = body.type2 (or body.type1 for mono-types), unless it
    # duplicates type1 → fall back to body.type1.
    body_secondary = body_t2 if body_t2 is not None else body_t1
    if body_secondary is not None and type1 is not None and body_secondary.id == type1.id:
        type2 = body_t1
    else:
        type2 = body_secondary

    # Final dedup: mono-type fusion if type2 == type1
    if type1 is not None and type2 is not None and type1.id == type2.id:
        type2 = None

    return type1, type2


def compute_fusion_weaknesses(db: Session, head: Pokemon, body: Pokemon) -> list[dict]:
    """Damage multipliers against the fusion's type combination."""
    type1, type2 = compute_fusion_types(head, body)
    defending_ids = [t.id for t in (type1, type2) if t]
    if not defending_ids:
        return []

    multipliers: dict[int, Decimal] = defaultdict(lambda: Decimal("1.0"))
    rows = (
        db.query(TypeEffectiveness)
        .filter(TypeEffectiveness.defending_type_id.in_(defending_ids))
        .all()
    )
    for eff in rows:
        multipliers[eff.attacking_type_id] *= eff.multiplier

    # Only fetch the attacking types that actually appear — never all 18.
    type_map = {t.id: t for t in db.query(Type).filter(Type.id.in_(multipliers.keys())).all()}
    return [
        {
            "attacking_type_id":      tid,
            "attacking_type_name_en": type_map[tid].name_en,
            "attacking_type_name_fr": type_map[tid].name_fr,
            "multiplier":             float(mult),
        }
        for tid, mult in sorted(multipliers.items())
        if mult != Decimal("1.0") and tid in type_map
    ]


def compute_fusion_moves(db: Session, head_id: int, body_id: int) -> list[dict]:
    """Union of head + body movesets, one row per move_id, origin labelled."""
    rows = (
        db.query(PokemonMove)
        .options(joinedload(PokemonMove.move).joinedload(Move.type))
        .filter(PokemonMove.pokemon_id.in_((head_id, body_id)))
        .all()
    )
    # Group by move_id, track origin + prefer lowest level_up row
    by_move: dict[int, dict] = {}
    origins: dict[int, set[str]] = defaultdict(set)
    for r in rows:
        origins[r.move_id].add("head" if r.pokemon_id == head_id else "body")
        existing = by_move.get(r.move_id)
        if existing is None:
            by_move[r.move_id] = {"row": r}
            continue
        prev = existing["row"]
        if r.method == "level_up" and (prev.method != "level_up" or (r.level or 9999) < (prev.level or 9999)):
            by_move[r.move_id] = {"row": r}

    out = []
    for move_id, entry in by_move.items():
        r = entry["row"]
        src = origins[move_id]
        origin = "both" if len(src) == 2 else next(iter(src))
        out.append({
            "move_id":  move_id,
            "name_en":  r.move.name_en,
            "name_fr":  r.move.name_fr,
            "category": r.move.category,
            "power":    r.move.power,
            "accuracy": r.move.accuracy,
            "pp":       r.move.pp,
            "type":     r.move.type,
            "method":   r.method,
            "level":    r.level,
            "source":   r.source,
            "origin":   origin,
        })
    out.sort(key=lambda m: (m["method"], m["level"] or 0, m["name_en"]))
    return out


def compute_fusion_abilities(db: Session, head: Pokemon, body: Pokemon) -> list[dict]:
    """
    Fusion abilities follow the IF rule:
      - Head's slot-1 ability → fusion slot 1
      - Body's slot-1 ability → fusion slot 2 (only if different)
      - Hidden abilities of both are listed as hidden options
    """
    rows = (
        db.query(PokemonAbility)
        .options(joinedload(PokemonAbility.ability))
        .filter(PokemonAbility.pokemon_id.in_((head.id, body.id)))
        .order_by(PokemonAbility.pokemon_id, PokemonAbility.slot)
        .all()
    )
    head_abilities = [a for a in rows if a.pokemon_id == head.id]
    body_abilities = [a for a in rows if a.pokemon_id == body.id]

    head_slot1 = next((a for a in head_abilities if not a.is_hidden), None)
    body_slot1 = next((a for a in body_abilities if not a.is_hidden), None)
    head_hidden = next((a for a in head_abilities if a.is_hidden), None)
    body_hidden = next((a for a in body_abilities if a.is_hidden), None)

    result: list[dict] = []
    seen: set[int] = set()

    def add(a: PokemonAbility | None, origin: str, hidden: bool) -> None:
        if a is None or a.ability_id in seen:
            return
        seen.add(a.ability_id)
        result.append({
            "ability_id": a.ability_id,
            "name_en":    a.ability.name_en,
            "name_fr":    a.ability.name_fr,
            "is_hidden":  hidden,
            "origin":     origin,
        })

    add(head_slot1, "head", False)
    add(body_slot1, "body", False)
    add(head_hidden, "head", True)
    add(body_hidden, "body", True)
    return result


def compute_fusion_expert_moves(
    db: Session, head: Pokemon, body: Pokemon
) -> list[dict]:
    """Moves teachable to this fusion by Move Experts (Knot + Boon Islands).

    A fusion qualifies for a move if AT LEAST ONE row in
    `move_expert_move` satisfies all 3 conditions (AND within a row):
      - required_pokemon_ids non-empty ⇒ head.id OR body.id ∈ list
      - required_type_ids    non-empty ⇒ ALL those types ∈ fusion's types
      - required_move_ids    non-empty ⇒ the fusion knows ≥1 of those moves
    An empty array means no constraint on that axis.

    Returns one entry per qualifying move, with the list of locations
    ('knot_island' / 'boon_island') that teach it.
    """
    type1, type2 = compute_fusion_types(head, body)
    fusion_type_ids = {t.id for t in (type1, type2) if t}

    # Moves known by the fusion (head ∪ body movepool)
    learned_move_ids: set[int] = {
        mid for (mid,) in db.query(PokemonMove.move_id)
        .filter(PokemonMove.pokemon_id.in_((head.id, body.id)))
        .distinct()
        .all()
    }

    rows = (
        db.query(MoveExpertMove)
        .options(joinedload(MoveExpertMove.move).joinedload(Move.type))
        .all()
    )

    qualified: dict[int, dict] = {}  # move_id → entry
    for row in rows:
        # AND: Pokémon check
        if row.required_pokemon_ids:
            if head.id not in row.required_pokemon_ids and body.id not in row.required_pokemon_ids:
                continue
        # AND: all required types must be present in the fusion
        if row.required_type_ids:
            if not set(row.required_type_ids).issubset(fusion_type_ids):
                continue
        # AND: ≥1 prerequisite move must be known
        if row.required_move_ids:
            if not (set(row.required_move_ids) & learned_move_ids):
                continue

        entry = qualified.get(row.move_id)
        if entry is None:
            m = row.move
            entry = {
                "move_id":   row.move_id,
                "name_en":   m.name_en,
                "name_fr":   m.name_fr,
                "category":  m.category,
                "power":     m.power,
                "accuracy":  m.accuracy,
                "pp":        m.pp,
                "type":      m.type,
                "locations": set(),
            }
            qualified[row.move_id] = entry
        entry["locations"].add(row.expert_location)

    out = []
    for entry in qualified.values():
        entry["locations"] = sorted(entry["locations"])
        entry["prices_heart_scales"] = {
            loc: MOVE_EXPERT_PRICES_HEART_SCALES[loc] for loc in entry["locations"]
        }
        out.append(entry)
    out.sort(key=lambda e: (e["locations"][0], e["name_en"]))
    return out


def list_fusions_involving(
    db: Session, pokemon_id: int, *, limit: int | None = None, offset: int = 0
) -> list[dict]:
    """All fusions where this Pokémon is head OR body.

    Uses `fusion_sprite` as the canonical source (one row per sprite variant).
    We collapse to one row per (head_id, body_id) pair.
    """
    from backend.db.models import FusionSprite

    pairs = (
        db.query(FusionSprite.head_id, FusionSprite.body_id)
        .filter((FusionSprite.head_id == pokemon_id) | (FusionSprite.body_id == pokemon_id))
        .distinct()
        .order_by(FusionSprite.head_id, FusionSprite.body_id)
    )
    if limit is not None:
        pairs = pairs.limit(limit)
    pairs = pairs.offset(offset)

    partner_ids = set()
    rows = []
    for h, b in pairs.all():
        partner_id = b if h == pokemon_id else h
        role = "head" if h == pokemon_id else "body"
        partner_ids.add(partner_id)
        rows.append({"head_id": h, "body_id": b, "role": role, "partner_id": partner_id})

    names = {
        p.id: (p.name_en, p.name_fr)
        for p in db.query(Pokemon).filter(Pokemon.id.in_(partner_ids)).all()
    }
    for r in rows:
        n = names.get(r["partner_id"], (None, None))
        r["partner_name_en"], r["partner_name_fr"] = n
    return rows


def random_fusion_ids(db: Session) -> tuple[int, int]:
    """Pick two distinct random Pokémon IDs for a random fusion.

    Uses ORDER BY RANDOM() LIMIT 2 so only 2 rows are transferred instead
    of loading all 501 IDs into Python memory. DISTINCT is guaranteed by
    fetching 2 separate rows from the DB shuffle.
    """
    from sqlalchemy import func
    rows = db.query(Pokemon.id).order_by(func.random()).limit(2).all()
    return rows[0][0], rows[1][0]


def compute_fusion(
    db: Session,
    head_id: int,
    body_id: int,
) -> dict | None:
    """
    Returns a dict with computed fusion stats, types, and sprite path.
    Returns None if either Pokémon is not found.
    """
    head = load_pokemon_with_types(db, head_id)
    body = load_pokemon_with_types(db, body_id)

    if not head or not body:
        return None

    # ── Stats ────────────────────────────────────────────────────────────────
    def phys(b: int, h: int) -> int:
        return math.floor(b * 2 / 3 + h * 1 / 3)

    def spec(h: int, b: int) -> int:
        return math.floor(h * 2 / 3 + b * 1 / 3)

    hp       = phys(body.hp,        head.hp)
    attack   = phys(body.attack,    head.attack)
    defense  = phys(body.defense,   head.defense)
    speed    = phys(body.speed,     head.speed)
    sp_attack  = spec(head.sp_attack,  body.sp_attack)
    sp_defense = spec(head.sp_defense, body.sp_defense)

    type1_obj, type2_obj = compute_fusion_types(head, body)

    return {
        "head_id":       head_id,
        "body_id":       body_id,
        "head_name_en":  head.name_en,
        "head_name_fr":  head.name_fr,
        "body_name_en":  body.name_en,
        "body_name_fr":  body.name_fr,
        "hp":            hp,
        "attack":        attack,
        "defense":       defense,
        "sp_attack":     sp_attack,
        "sp_defense":    sp_defense,
        "speed":         speed,
        "type1":         type1_obj,
        "type2":         type2_obj,
        "sprite_path":   f"{head_id}.{body_id}.png",
    }
