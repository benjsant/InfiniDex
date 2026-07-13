"""Shared PokeAPI move-cross-reference helpers.

Used by `fix_tms_from_pokeapi.py` and `fix_tutors_from_pokeapi.py` to look up
which Pokémon (and their pre-evolution descendants) learn a given move
according to the official games, then materialize that into IF's
`pokemon_move` table.

The two callers differ only in the table source label and the WHERE clause
on the wiki side — the PokeAPI cross-reference + DB joins + descendant
walk are identical.
"""

from __future__ import annotations

from collections import defaultdict
from logging import Logger

from etl.utils.http import get_json

POKEAPI = "https://pokeapi.co/api/v2"


_ACCENT_MAP = str.maketrans({
    "é": "e", "è": "e", "ê": "e", "ë": "e",
    "à": "a", "â": "a", "ä": "a",
    "ô": "o", "ö": "o",
    "û": "u", "ü": "u",
    "î": "i", "ï": "i",
    "ç": "c",
})


def pokeapi_move_slug(name_en: str) -> str:
    """Convert a Pokémon or move name (EN) to its PokeAPI URL slug.

    Handles:
      - case → lowercase
      - apostrophes, dots, colons → stripped
      - ♀ → '-f', ♂ → '-m'
      - accents → ASCII equivalents
      - spaces → '-'

    Examples:
      "Mime Jr."     → "mime-jr"
      "Nidoran♀"     → "nidoran-f"
      "Type: Null"   → "type-null"
      "Flabébé"      → "flabebe"
      "Farfetch'd"   → "farfetchd"
      "Ho-Oh"        → "ho-oh"
      "Porygon-Z"    → "porygon-z"
    """
    s = name_en.translate(_ACCENT_MAP).lower()
    s = (
        s.replace("♀", "-f")
         .replace("♂", "-m")
         .replace("'", "")
         .replace("’", "")
         .replace(".", "")
         .replace(":", "")
         .replace(" ", "-")
    )
    # Collapse accidental double hyphens introduced by " -" or "- " etc.
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")


def fetch_move_detail(
    name_en: str,
    *,
    logger: Logger,
) -> tuple[bool, list[str]] | None:
    """Return `(is_official_tm, learner_slugs)` from PokeAPI, or None on failure.

    `is_official_tm` is True iff the move has at least one entry in
    `machines` (i.e. it's a TM/HM in at least one official game). Callers
    decide what to do with that flag (see the two fix scripts).
    """
    slug = pokeapi_move_slug(name_en)
    data = get_json(f"{POKEAPI}/move/{slug}")
    if data is None:
        logger.warning("PokeAPI fetch failed for move %s (slug=%s)", name_en, slug)
        return None
    is_official_tm = bool(data.get("machines"))
    learners = [p["name"] for p in data.get("learned_by_pokemon", [])]
    return is_official_tm, learners


def load_move_ids(cur, names: list[str]) -> dict[str, int]:
    """name_en → move.id, restricted to moves actually in the DB."""
    cur.execute("SELECT id, name_en FROM move WHERE name_en = ANY(%s)", (names,))
    return {name: mid for mid, name in cur.fetchall()}


def load_pokemon_ids(cur) -> dict[str, int]:
    """PokeAPI-like slug → pokemon.id (matches the slug PokeAPI returns)."""
    cur.execute("SELECT id, name_en FROM pokemon")
    return {pokeapi_move_slug(name_en): pid for pid, name_en in cur.fetchall()}


def load_evolution_forward(cur) -> dict[int, list[int]]:
    """pokemon_id → list of direct descendants (forward evolution edges)."""
    cur.execute("SELECT pokemon_id, evolves_into_id FROM pokemon_evolution")
    out: dict[int, list[int]] = defaultdict(list)
    for src, tgt in cur.fetchall():
        out[src].append(tgt)
    return out


def all_descendants(start: int, edges: dict[int, list[int]]) -> set[int]:
    """BFS of a Pokémon's evolution descendants (excluding `start`)."""
    seen: set[int] = set()
    queue = list(edges.get(start, []))
    while queue:
        nxt = queue.pop()
        if nxt in seen:
            continue
        seen.add(nxt)
        queue.extend(edges.get(nxt, []))
    return seen
