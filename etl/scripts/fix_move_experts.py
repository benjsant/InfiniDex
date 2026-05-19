"""
ETL script — populates the `move_expert_move` table.

Infinite Fusion's Move Experts (Knot Island and Boon Island) teach
signature moves of Pokémon absent from the game, but ONLY to fusions
that satisfy precise conditions. Example: a head-Umbreon fusion can
learn "Parting Shot" thanks to the Knot Island Move Expert.

Source: https://infinitefusion.fandom.com/wiki/List_of_Move_Expert_Moves

Wiki format:
  Each move occupies ONE cell, possibly with `rowspan="N"` if several
  prerequisite combinations exist (OR between rows). Within a row, the
  next three columns form a conjunction (AND):
    - Required Fusions: list of Pokémon (OR) — head OR body must match
    - Required Type(s): 1+ types — the fusion must have them ALL (AND)
    - Must learn one of these moves: list of moves (OR)
  A "- " in a column = no constraint on that axis.

Idempotent: purges and re-inserts the `move_expert_move` rows each run.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

import requests

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

WIKI_API = "https://infinitefusion.fandom.com/api.php"
WIKI_UA  = "InfiniDexETL/1.0 (github.com/benjsant/InfiniDex-IA)"
WIKI_PAGE = "List_of_Move_Expert_Moves"


# ─── Normalization helpers ────────────────────────────────────────────────────

_NORM_STRIP = str.maketrans("", "", "-.' ")

# Wiki typo fixes (key = normalized wiki-side name)
WIKI_POKEMON_ALIASES: dict[str, str] = {
    "flaafy": "flaaffy",  # the IF wiki spells it "Flaafy" (1 f)
}


def norm(s: str) -> str:
    """Normalize a name for comparison (case-insensitive, no punctuation).

        "Porygon-Z"  → "porygonz"
        "PorygonZ"   → "porygonz"
        "Farfetch'd" → "farfetchd"
        "Ho-oh"      → "hooh"
    """
    return s.lower().translate(_NORM_STRIP)


def norm_pokemon(s: str) -> str:
    """Normalize + apply the wiki typo aliases."""
    n = norm(s)
    return WIKI_POKEMON_ALIASES.get(n, n)


# ─── Wiki parser ──────────────────────────────────────────────────────────────

@dataclass
class ExpertRow:
    """One alternative (row) for a move taught by an expert."""
    move_name: str
    location: str                   # 'knot_island' | 'boon_island'
    pokemon_names: list[str] = field(default_factory=list)  # OR between them
    type_names:    list[str] = field(default_factory=list)  # AND between them
    move_names:    list[str] = field(default_factory=list)  # OR between them (learn ≥1)


MOVE_LINK_RE = re.compile(r"\[\[bulbapedia:[^|\]]+\|(?P<name>[^\]]+)\]\]")
ROWSPAN_RE   = re.compile(r'rowspan="(\d+)"', re.IGNORECASE)


def fetch_wikitext() -> str:
    resp = requests.get(
        WIKI_API,
        params={
            "action": "parse",
            "page":   WIKI_PAGE,
            "prop":   "wikitext",
            "format": "json",
        },
        headers={"User-Agent": WIKI_UA},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["parse"]["wikitext"]["*"]


def parse_cell(raw: str) -> str:
    """Extract a table cell's value (without the leading `|`)."""
    s = raw.strip()
    # Strip a possible prefix `rowspan="N" |` / `colspan="N" |` / `attr | `
    # Format: `rowspan="2" | [[...]]` or `[[...]]`
    if "|" in s:
        # Split only once: the first `|` separates attrs and content.
        # Beware internal `|` of wikilinks `[[x|y]]` → split only if the
        # part before `|` looks like an HTML attribute.
        head, _, tail = s.partition("|")
        if re.fullmatch(r'\s*(?:rowspan|colspan|style|class)="[^"]*"\s*', head):
            s = tail.strip()
    # "empty" cell: a single "-"
    if s == "-":
        return ""
    return s


def parse_pokemon_list(cell: str) -> list[str]:
    if not cell:
        return []
    return [p.strip() for p in cell.split(",") if p.strip()]


def parse_type_list(cell: str) -> list[str]:
    """Split on ', ' or ' and ' — the page uses "Grass and Ghost"."""
    if not cell:
        return []
    # normalize the separators
    parts = re.split(r"\s*,\s*|\s+and\s+", cell)
    return [p.strip() for p in parts if p.strip()]


def parse_move_list(cell: str) -> list[str]:
    """"Must learn one of these moves" cell — comma-separated."""
    if not cell:
        return []
    return [m.strip() for m in cell.split(",") if m.strip()]


def split_sections(wikitext: str) -> list[tuple[str, str]]:
    """Return [(location, table_body), ...] — one entry per table."""
    sections: list[tuple[str, str]] = []
    for header, loc in (
        ("Move Expert (Knot Island)",            "knot_island"),
        ("Legendary Move Expert (Boon Island)",  "boon_island"),
    ):
        pat = re.compile(
            rf"==\s*{re.escape(header)}\s*==\s*\n(?P<body>.*?)(?=\n==|\Z)",
            re.DOTALL,
        )
        m = pat.search(wikitext)
        if not m:
            LOGGER.warning("Section not found: %s", header)
            continue
        sections.append((loc, m.group("body")))
    return sections


def parse_table(body: str, location: str) -> list[ExpertRow]:
    """Parse a table and return the list of alternatives (one per row)."""
    # The whole table is between `{| ... |}`
    start = body.find("{|")
    end   = body.find("|}", start)
    if start == -1 or end == -1:
        LOGGER.warning("Table not found for %s", location)
        return []
    table = body[start + 2 : end]

    # Split into rows via the `|-` separators
    raw_rows = re.split(r"^\s*\|-\s*$", table, flags=re.MULTILINE)
    # First "row" = headers (`!...`) → discard it
    data_rows = [r for r in raw_rows if r.strip() and not r.strip().startswith("!")]

    out: list[ExpertRow] = []
    # To handle rowspan: when a "move" cell spans N rows, reuse it for the
    # following (N-1) rows that only have 3 columns.
    current_move: str | None = None
    move_rows_remaining = 0

    for rr in data_rows:
        # Each cell starts with `|` at the beginning of the line.
        cells = [c for c in re.split(r"^\s*\|", rr, flags=re.MULTILINE) if c.strip()]
        # `cells` holds either 4 cells (new move) or 3 (continuation).

        if len(cells) == 4:
            move_cell_raw = cells[0]
            rowspan_m = ROWSPAN_RE.search(move_cell_raw)
            rowspan_n = int(rowspan_m.group(1)) if rowspan_m else 1
            move_cell = parse_cell(move_cell_raw)
            m = MOVE_LINK_RE.search(move_cell)
            if not m:
                LOGGER.debug("Move cell without bulbapedia link, skipped: %r", move_cell_raw)
                continue
            current_move = m.group("name").strip()
            move_rows_remaining = rowspan_n - 1
            pk_cell, ty_cell, mv_cell = cells[1], cells[2], cells[3]
        elif len(cells) == 3 and move_rows_remaining > 0 and current_move:
            move_rows_remaining -= 1
            pk_cell, ty_cell, mv_cell = cells[0], cells[1], cells[2]
        else:
            LOGGER.debug("Row skipped (%d cells): %r", len(cells), rr[:80])
            continue

        row = ExpertRow(
            move_name     = current_move,
            location      = location,
            pokemon_names = parse_pokemon_list(parse_cell(pk_cell)),
            type_names    = parse_type_list(parse_cell(ty_cell)),
            move_names    = parse_move_list(parse_cell(mv_cell)),
        )
        out.append(row)

    return out


# ─── DB resolution ────────────────────────────────────────────────────────────

def load_pokemon_index(cur) -> dict[str, int]:
    cur.execute("SELECT id, name_en FROM pokemon")
    return {norm(name_en): pid for pid, name_en in cur.fetchall()}


def load_move_index(cur) -> dict[str, int]:
    cur.execute("SELECT id, name_en FROM move")
    return {norm(name_en): mid for mid, name_en in cur.fetchall()}


def load_type_index(cur) -> dict[str, int]:
    cur.execute("SELECT id, name_en FROM type WHERE is_triple_fusion_type = FALSE")
    return {norm(name_en): tid for tid, name_en in cur.fetchall()}


# ─── Main ─────────────────────────────────────────────────────────────────────

def run(conn) -> None:
    cur = conn.cursor()

    pokemon_idx = load_pokemon_index(cur)
    move_idx    = load_move_index(cur)
    type_idx    = load_type_index(cur)

    LOGGER.info("DB: %d Pokémon, %d moves, %d types loaded",
                len(pokemon_idx), len(move_idx), len(type_idx))

    wikitext = fetch_wikitext()
    LOGGER.info("Wiki: %d characters fetched", len(wikitext))

    all_rows: list[ExpertRow] = []
    for location, body in split_sections(wikitext):
        rows = parse_table(body, location)
        LOGGER.info("  %s: %d alternatives parsed", location, len(rows))
        all_rows.extend(rows)

    # Resolution → IDs
    inserts: list[tuple[int, str, list[int], list[int], list[int]]] = []
    unresolved_moves:    set[str] = set()
    unresolved_pokemon:  set[str] = set()
    unresolved_types:    set[str] = set()
    unresolved_premoves: set[str] = set()

    for row in all_rows:
        mid = move_idx.get(norm(row.move_name))
        if mid is None:
            unresolved_moves.add(row.move_name)
            continue

        pk_ids: list[int] = []
        for name in row.pokemon_names:
            pid = pokemon_idx.get(norm_pokemon(name))
            if pid is None:
                unresolved_pokemon.add(name)
            else:
                pk_ids.append(pid)

        ty_ids: list[int] = []
        for name in row.type_names:
            tid = type_idx.get(norm(name))
            if tid is None:
                unresolved_types.add(name)
            else:
                ty_ids.append(tid)

        mv_ids: list[int] = []
        for name in row.move_names:
            pre_mid = move_idx.get(norm(name))
            if pre_mid is None:
                unresolved_premoves.add(name)
            else:
                mv_ids.append(pre_mid)

        inserts.append((mid, row.location, pk_ids, ty_ids, mv_ids))

    if unresolved_moves:
        LOGGER.warning("Unknown moves (skipped): %s", sorted(unresolved_moves))
    if unresolved_pokemon:
        LOGGER.warning("Unknown Pokémon: %s", sorted(unresolved_pokemon))
    if unresolved_types:
        LOGGER.warning("Unknown types: %s", sorted(unresolved_types))
    if unresolved_premoves:
        LOGGER.warning("Unknown prerequisite moves: %s", sorted(unresolved_premoves))

    # Purge and re-insert (idempotent)
    cur.execute("TRUNCATE move_expert_move RESTART IDENTITY")
    for mid, loc, pk_ids, ty_ids, mv_ids in inserts:
        cur.execute(
            """
            INSERT INTO move_expert_move
                (move_id, expert_location, required_pokemon_ids,
                 required_type_ids, required_move_ids)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (mid, loc, pk_ids, ty_ids, mv_ids),
        )

    conn.commit()
    cur.close()
    LOGGER.info("Done — %d rows inserted into move_expert_move",
                len(inserts))


def main() -> None:
    with pg_connection() as conn:
        run(conn)


if __name__ == "__main__":
    sys.exit(main() or 0)
