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

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, aliased, joinedload

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

# ── In-process static caches ─────────────────────────────────────────────────
# Pokémon data never changes between deploys — cleared automatically on restart.
# _pokemon_cache is bounded by the 572-Pokémon warmup (exact size known).
# _fusion_cache is bounded at _FUSION_CACHE_MAX to prevent unbounded growth
# across all 501×501 = ~251k combinations; eviction clears the whole dict
# (LRU would be better but adds complexity — clear-on-full is sufficient here).
_FUSION_CACHE_MAX = 4096
_pokemon_cache: dict[int, Pokemon | None] = {}
_fusion_cache: dict[tuple[int, int], dict | None] = {}


def _batch_warm_cache(db: Session, ids: set[int]) -> None:
    """Load a set of Pokémon with types into _pokemon_cache in one query."""
    missing = [pid for pid in ids if pid not in _pokemon_cache]
    if not missing:
        return
    rows = (
        db.query(Pokemon)
        .options(joinedload(Pokemon.types).joinedload(PokemonType.type))
        .filter(Pokemon.id.in_(missing))
        .all()
    )
    for p in rows:
        _pokemon_cache[p.id] = p
    for pid in missing:
        _pokemon_cache.setdefault(pid, None)


def load_pokemon_with_types(db: Session, pid: int) -> Pokemon | None:
    """Load a Pokémon + types (slot1/slot2) eagerly loaded. Public: reused by `fusion_route`."""
    if pid in _pokemon_cache:
        return _pokemon_cache[pid]
    result = (
        db.query(Pokemon)
        .options(joinedload(Pokemon.types).joinedload(PokemonType.type))
        .filter(Pokemon.id == pid)
        .first()
    )
    _pokemon_cache[pid] = result
    return result


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


def fusion_stats(head, body) -> dict[str, int]:
    """Single source of truth for the fusion base-stat formula.

    Physical (HP/Atk/Def/Spe) = floor(body*2/3 + head/3)
    Special  (SpA/SpD)        = floor(head*2/3 + body/3)

    `head`/`body` are any objects exposing the six stat attributes
    (Pokemon ORM rows or aliased query rows).
    """
    return {
        "hp":         math.floor(body.hp         * 2 / 3 + head.hp         / 3),
        "attack":     math.floor(body.attack     * 2 / 3 + head.attack     / 3),
        "defense":    math.floor(body.defense    * 2 / 3 + head.defense    / 3),
        "speed":      math.floor(body.speed      * 2 / 3 + head.speed      / 3),
        "sp_attack":  math.floor(head.sp_attack  * 2 / 3 + body.sp_attack  / 3),
        "sp_defense": math.floor(head.sp_defense * 2 / 3 + body.sp_defense / 3),
    }


def fusion_bst_expr(head, body):
    """SQL expression for fusion BST — same formula as fusion_stats(), summed.

    `head`/`body` are mapped classes or aliased() entities.
    """
    return (
        func.floor(body.hp        * 2.0 / 3 + head.hp        * 1.0 / 3)
        + func.floor(body.attack  * 2.0 / 3 + head.attack    * 1.0 / 3)
        + func.floor(body.defense * 2.0 / 3 + head.defense   * 1.0 / 3)
        + func.floor(head.sp_attack  * 2.0 / 3 + body.sp_attack  * 1.0 / 3)
        + func.floor(head.sp_defense * 2.0 / 3 + body.sp_defense * 1.0 / 3)
        + func.floor(body.speed   * 2.0 / 3 + head.speed     * 1.0 / 3)
    )


def compute_fusion_from_objects(head: Pokemon, body: Pokemon) -> dict:
    """Same as compute_fusion but takes already-loaded Pokemon objects.

    Avoids two extra load_pokemon_with_types queries when the caller
    already has the objects (e.g. the AI agent tool).
    """
    type1_obj, type2_obj = compute_fusion_types(head, body)

    return {
        "head_id":      head.id,
        "body_id":      body.id,
        "head_name_en": head.name_en,
        "head_name_fr": head.name_fr,
        "body_name_en": body.name_en,
        "body_name_fr": body.name_fr,
        **fusion_stats(head, body),
        "type1":        type1_obj,
        "type2":        type2_obj,
        "sprite_path":  f"{head.id}.{body.id}.png",
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

    # Push all three conditions to PostgreSQL using native ARRAY operators:
    #   overlap (&&)       → at least one element in common
    #   contained_by (<@)  → all elements are in the reference set
    pokemon_cond = or_(
        MoveExpertMove.required_pokemon_ids == [],
        MoveExpertMove.required_pokemon_ids.overlap([head.id, body.id]),
    )
    type_cond = (
        or_(
            MoveExpertMove.required_type_ids == [],
            MoveExpertMove.required_type_ids.contained_by(list(fusion_type_ids)),
        )
        if fusion_type_ids
        else MoveExpertMove.required_type_ids == []
    )
    move_cond = (
        or_(
            MoveExpertMove.required_move_ids == [],
            MoveExpertMove.required_move_ids.overlap(list(learned_move_ids)),
        )
        if learned_move_ids
        else MoveExpertMove.required_move_ids == []
    )

    rows = (
        db.query(MoveExpertMove)
        .options(joinedload(MoveExpertMove.move).joinedload(Move.type))
        .filter(pokemon_cond, type_cond, move_cond)
        .all()
    )

    qualified: dict[int, dict] = {}  # move_id → entry
    for row in rows:
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


def list_featured_fusions(db: Session, limit: int = 50) -> list[dict]:
    """Random sample of fusions that have at least one custom sprite.

    Replaces the BST-based top list to avoid always surfacing legendaries
    and to avoid spoiling which legendary Pokémon are available in IF.
    """
    from backend.db.models import FusionSprite

    # DISTINCT + ORDER BY random() is invalid in PostgreSQL unless random()
    # is in the SELECT list. Use a subquery to shuffle after deduplication.
    subq = (
        db.query(FusionSprite.head_id, FusionSprite.body_id)
        .filter(FusionSprite.is_custom.is_(True))
        .distinct()
        .subquery()
    )
    pairs = (
        db.query(subq.c.head_id, subq.c.body_id)
        .order_by(func.random())
        .limit(limit)
        .all()
    )

    all_ids = {hid for hid, bid in pairs} | {bid for hid, bid in pairs}
    _batch_warm_cache(db, all_ids)

    result = []
    for head_id, body_id in pairs:
        head = load_pokemon_with_types(db, head_id)
        body = load_pokemon_with_types(db, body_id)
        if not head or not body:
            continue
        type1, type2 = compute_fusion_types(head, body)
        result.append({
            "head_id":      head_id,
            "body_id":      body_id,
            "head_name_en": head.name_en,
            "head_name_fr": head.name_fr,
            "body_name_en": body.name_en,
            "body_name_fr": body.name_fr,
            "type1":        type1,
            "type2":        type2,
            "sprite_path":  f"{head_id}.{body_id}.png",
        })
    return result


def list_top_fusions(db: Session, limit: int = 50) -> list[dict]:
    """Top fusions ranked by BST, computed entirely in SQL via cross-join.

    Returns at most `limit` rows. Cross-join over 501 Pokémon = 251,001 rows,
    trivially handled by PostgreSQL with ORDER BY + LIMIT.
    """
    Head = aliased(Pokemon, name="head")
    Body = aliased(Pokemon, name="body")

    bst_expr = fusion_bst_expr(Head, Body)

    rows = (
        db.query(Head, Body, bst_expr.label("bst"))
        .filter(Head.id != Body.id)
        .order_by(bst_expr.desc())
        .limit(limit)
        .all()
    )

    _batch_warm_cache(db, {head.id for head, body, bst in rows} | {body.id for head, body, bst in rows})

    result = []
    for rank, (head, body, bst) in enumerate(rows, start=1):
        h_full = load_pokemon_with_types(db, head.id)
        b_full = load_pokemon_with_types(db, body.id)
        type1, type2 = compute_fusion_types(h_full, b_full)
        result.append({
            "rank":         rank,
            "head_id":      head.id,
            "body_id":      body.id,
            "head_name_en": head.name_en,
            "head_name_fr": head.name_fr,
            "body_name_en": body.name_en,
            "body_name_fr": body.name_fr,
            **fusion_stats(head, body),
            "bst":          int(bst),
            "type1":        type1,
            "type2":        type2,
            "sprite_path":  f"{head.id}.{body.id}.png",
        })
    return result


def list_top_fusions_for_pokemon(db: Session, pokemon_id: int, limit: int = 5) -> list[dict]:
    """Best fusions involving a specific Pokémon (as head OR body), ranked by BST.

    Computes BST for all (pokemon as head, q as body) and (q as head, pokemon as body)
    across all Pokémon q ≠ pokemon. Returns top `limit` unique pairs.
    """
    Partner = aliased(Pokemon, name="partner")
    Fixed   = aliased(Pokemon, name="fixed")

    # pokemon as head
    as_head_bst = fusion_bst_expr(Fixed, Partner)
    as_head = (
        db.query(Fixed, Partner, as_head_bst.label("bst"))
        .filter(Fixed.id == pokemon_id, Partner.id != pokemon_id)
        .all()
    )

    # pokemon as body
    as_body_bst = fusion_bst_expr(Partner, Fixed)
    as_body = (
        db.query(Partner, Fixed, as_body_bst.label("bst"))
        .filter(Fixed.id == pokemon_id, Partner.id != pokemon_id)
        .all()
    )

    all_ids = (
        {fixed.id for fixed, partner, _ in as_head}
        | {partner.id for fixed, partner, _ in as_head}
        | {partner.id for partner, fixed, _ in as_body}
        | {fixed.id for partner, fixed, _ in as_body}
    )
    _batch_warm_cache(db, all_ids)

    combined = []
    for fixed, partner, bst in as_head:
        combined.append(("head", fixed, partner, int(bst)))
    for partner, fixed, bst in as_body:
        combined.append(("body", partner, fixed, int(bst)))

    combined.sort(key=lambda x: x[3], reverse=True)
    top = combined[:limit]

    result = []
    for rank, (role, head, body, bst) in enumerate(top, start=1):
        h_full = load_pokemon_with_types(db, head.id)
        b_full = load_pokemon_with_types(db, body.id)
        type1, type2 = compute_fusion_types(h_full, b_full)
        result.append({
            "rank":         rank,
            "head_id":      head.id,
            "body_id":      body.id,
            "head_name_en": head.name_en,
            "head_name_fr": head.name_fr,
            "body_name_en": body.name_en,
            "body_name_fr": body.name_fr,
            **fusion_stats(head, body),
            "bst":          bst,
            "type1":        type1,
            "type2":        type2,
            "sprite_path":  f"{head.id}.{body.id}.png",
            "role":         role,
        })
    return result


def random_fusion_ids(db: Session) -> tuple[int, int]:
    """Pick two distinct random Pokémon IDs for a random fusion.

    Uses ORDER BY RANDOM() LIMIT 2 so only 2 rows are transferred instead
    of loading all 501 IDs into Python memory. DISTINCT is guaranteed by
    fetching 2 separate rows from the DB shuffle.
    """
    from sqlalchemy import func
    rows = db.query(Pokemon.id).order_by(func.random()).limit(2).all()
    if len(rows) < 2:
        raise ValueError("Not enough Pokémon in the database for a random fusion")
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
    key = (head_id, body_id)
    if key in _fusion_cache:
        return _fusion_cache[key]

    head = load_pokemon_with_types(db, head_id)
    body = load_pokemon_with_types(db, body_id)

    if not head or not body:
        return None

    type1_obj, type2_obj = compute_fusion_types(head, body)

    result = {
        "head_id":      head_id,
        "body_id":      body_id,
        "head_name_en": head.name_en,
        "head_name_fr": head.name_fr,
        "body_name_en": body.name_en,
        "body_name_fr": body.name_fr,
        **fusion_stats(head, body),
        "type1":        type1_obj,
        "type2":        type2_obj,
        "sprite_path":  f"{head_id}.{body_id}.png",
    }
    if len(_fusion_cache) >= _FUSION_CACHE_MAX:
        _fusion_cache.clear()
    _fusion_cache[key] = result
    return result
