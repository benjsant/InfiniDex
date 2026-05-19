"""ETL script — populates the `move_tutor` table from the IF wiki.

Source: https://infinitefusion.fandom.com/wiki/List_of_Tutors

Scope: classic tutors only (one NPC = one move). The first 3 rows of
the wiki table (Move Relearner, Move Deleter, Egg Move Tutor) are
special services not tied to a single move — they are excluded from
`move_tutor` and documented separately.

Currencies:
    'pokedollars' → `price` = amount (₽)
    'free'        → unconditionally free
    'quest'       → free after a quest (details in `npc_description`)

Idempotent: TRUNCATE + INSERT each run.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging
from etl.utils.wikitext import fetch_wikitext

LOGGER = setup_logging(__name__)

WIKI_PAGE = "List_of_Tutors"

# The first 3 rows of the wiki table are special cases that we exclude
# (not attachable to a single move).
SPECIAL_ROW_COUNT = 3


# ─── Mapping of wiki locations to the `location` table ───────────────────────
#
# The values are existing `location.name_en` names. Missing places
# (`Pewter City`, `Fuchsia City`) are created by `ensure_city` below.
LOCATION_ALIASES: dict[str, str] = {
    "Pokémon Tower":                "Lavender Town",
    "Silph Co. Head Office":        "Saffron City",
    "Goldenrod Train Station":      "Goldenrod City",
    "Radio Tower":                  "Goldenrod City",
    "Ruins of Alph Hidden Chamber": "Ruins of Alph",
}

# Cities to create if absent from the DB (named in the wiki but with no
# `pokemon_location` row → absent from `location`).
CITIES_TO_ENSURE: list[tuple[str, str | None]] = [
    ("Pewter City",   "Kanto"),
    ("Fuchsia City",  "Kanto"),
]


# ─── Parsers ─────────────────────────────────────────────────────────────────

@dataclass
class TutorRow:
    move_name:       str
    location_name:   str
    npc_description: str
    price:           int | None
    currency:        str  # 'pokedollars' | 'free' | 'quest'


# Matches [[bulbapedia:Bug_Bite (move)|Bug Bite]] OR [[bulbapedia:Foo|Foo]]
# OR external link [https://.../Superpower_(move) Superpower]
_WIKILINK_RE = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
_EXTLINK_RE  = re.compile(r"\[https?://\S+\s+([^\]]+)\]")
_ABBR_RE     = re.compile(r"<abbr[^>]*>(.*?)</abbr>", re.IGNORECASE | re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_PRICE_RE    = re.compile(r"₽\s*([\d,]+)")


def strip_wiki_markup(cell: str) -> str:
    """Remove wiki/HTML markup, keep plain display text."""
    s = _WIKILINK_RE.sub(r"\1", cell)
    s = _EXTLINK_RE.sub(r"\1", s)
    s = _ABBR_RE.sub(r"\1", s)
    s = _HTML_TAG_RE.sub("", s)
    return s.strip()


def extract_move_name(cell: str) -> str:
    """Move name is the display text of the bulbapedia link."""
    # Strip " (move)" suffix that sometimes leaks from the wiki
    name = strip_wiki_markup(cell)
    name = re.sub(r"\s*\(move\)\s*$", "", name, flags=re.IGNORECASE)
    return name.strip()


def extract_location_name(cell: str) -> str:
    """Location = first wikilink's display text, e.g. '[[Celadon City]]' → 'Celadon City'."""
    return strip_wiki_markup(cell)


def parse_price(cell: str) -> tuple[int | None, str]:
    """Returns (price, currency).

    Cases handled:
      '₽5,000'                              → (5000, 'pokedollars')
      'Free'                                → (None, 'free')
      '<abbr title="Free">Do his quest</abbr>' → (None, 'quest')
      '<abbr title="Free">Defeat her</abbr>'   → (None, 'quest')
    """
    raw = cell.strip()
    # Drop abbr wrapper but remember that it implies a quest if text != 'Free'
    is_abbr = bool(_ABBR_RE.search(raw))
    clean = strip_wiki_markup(raw)

    m = _PRICE_RE.search(clean)
    if m:
        return int(m.group(1).replace(",", "")), "pokedollars"
    if clean.lower() == "free":
        return None, "free"
    if is_abbr or "quest" in clean.lower() or "defeat" in clean.lower():
        return None, "quest"
    LOGGER.warning("Unrecognized price, treated as 'quest': %r", raw)
    return None, "quest"


def parse_wikitext(text: str) -> list[TutorRow]:
    """Extract one TutorRow per data line (after skipping the 3 special cases)."""
    # Each data block is separated by `|-`. The first block is the header.
    blocks = text.split("|-")
    all_rows: list[list[str]] = []
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip().startswith("|")]
        cells = [l[1:].strip() for l in lines]
        if len(cells) >= 4:
            all_rows.append(cells[:4])

    # Skip the first SPECIAL_ROW_COUNT rows (Move Relearner / Deleter / Egg tutor)
    data_rows = all_rows[SPECIAL_ROW_COUNT:]

    tutors: list[TutorRow] = []
    for cells in data_rows:
        move_cell, loc_cell, info_cell, price_cell = cells
        price, currency = parse_price(price_cell)
        tutors.append(TutorRow(
            move_name       = extract_move_name(move_cell),
            location_name   = extract_location_name(loc_cell),
            npc_description = strip_wiki_markup(info_cell),
            price           = price,
            currency        = currency,
        ))
    return tutors


# ─── DB resolution ───────────────────────────────────────────────────────────

def load_move_index(cur) -> dict[str, int]:
    cur.execute("SELECT id, name_en FROM move")
    # Simple normalization: lowercase + strip — IF moves use proper names,
    # no need for aliases (unlike Pokémon).
    return {name_en.lower().strip(): mid for mid, name_en in cur.fetchall()}


def load_location_index(cur) -> dict[str, int]:
    cur.execute("SELECT id, name_en FROM location")
    return {name_en: lid for lid, name_en in cur.fetchall()}


def ensure_city(cur, name_en: str, region: str | None) -> int:
    """Insert a location row if missing, return its id."""
    cur.execute("SELECT id FROM location WHERE name_en = %s", (name_en,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO location (name_en, region) VALUES (%s, %s) RETURNING id",
        (name_en, region),
    )
    new_id = cur.fetchone()[0]
    LOGGER.info("  + Location created: %s (id=%d)", name_en, new_id)
    return new_id


# ─── Main ────────────────────────────────────────────────────────────────────

def run(conn) -> None:
    cur = conn.cursor()

    # Create the missing cities BEFORE loading the index
    for city, region in CITIES_TO_ENSURE:
        ensure_city(cur, city, region)

    move_idx = load_move_index(cur)
    loc_idx  = load_location_index(cur)

    LOGGER.info("DB: %d moves, %d locations loaded", len(move_idx), len(loc_idx))

    wikitext = fetch_wikitext(WIKI_PAGE)
    LOGGER.info("Wiki: %d characters fetched", len(wikitext))

    tutors = parse_wikitext(wikitext)
    LOGGER.info("Wiki: %d classic tutors parsed (3 special cases excluded)", len(tutors))

    inserts: list[tuple[int, int, int | None, str, str]] = []
    unresolved_moves:     set[str] = set()
    unresolved_locations: set[str] = set()

    for t in tutors:
        mid = move_idx.get(t.move_name.lower().strip())
        if mid is None:
            unresolved_moves.add(t.move_name)
            continue

        # Apply aliases then lookup
        canonical_loc = LOCATION_ALIASES.get(t.location_name, t.location_name)
        lid = loc_idx.get(canonical_loc)
        if lid is None:
            unresolved_locations.add(t.location_name)
            continue

        inserts.append((mid, lid, t.price, t.currency, t.npc_description))

    if unresolved_moves:
        LOGGER.warning("Unknown moves (skipped): %s", sorted(unresolved_moves))
    if unresolved_locations:
        LOGGER.warning("Unknown locations (skipped): %s", sorted(unresolved_locations))

    cur.execute("TRUNCATE move_tutor RESTART IDENTITY")
    for mid, lid, price, currency, desc in inserts:
        cur.execute(
            """
            INSERT INTO move_tutor
                (move_id, location_id, price, currency, npc_description)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (mid, lid, price, currency, desc),
        )

    conn.commit()
    cur.close()
    LOGGER.info("Done — %d rows inserted into move_tutor", len(inserts))


def main() -> None:
    with pg_connection() as conn:
        run(conn)


if __name__ == "__main__":
    sys.exit(main() or 0)
