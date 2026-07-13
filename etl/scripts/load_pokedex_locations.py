"""
ETL — Load wild + quest encounter locations from the IF Pokédex wiki page.

Source: https://infinitefusion.fandom.com/wiki/Pokédex/Hoenn/Classic
(the top-level "Pokédex" page became a data-less hub after the wiki
restructure — the full 572-entry table lives in the Hoenn/Classic subpage).

Parses the {{PokedexTable/Data|...}} template format and extracts:
  - Wild encounters  (plain [[Location]] links) → method='wild'
  - Quest encounters ('''''[[Loc]]''''' [[Quests|(quest)]]) → method='static'
  - Static encounters for non-legendary Pokémon → method='static'

Static/gift/trade legendary data from fix_pokemon_locations.py takes priority;
this script uses ON CONFLICT DO NOTHING so it never overwrites existing entries.
"""

from __future__ import annotations

import re
import time

import httpx
import psycopg2

from etl.scripts.extract_pokedex_if import PAGE as POKEDEX_PAGE
from etl.utils.db import pg_connection
from etl.utils.http import USER_AGENT
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

WIKI_API = "https://infinitefusion.fandom.com/api.php"

# Links whose page name starts with these prefixes are meta-links, not locations
_META_PREFIXES = (
    "List of", "Quests", "Pokéradar", "Field Moves",
    "List_of", "Category:", "File:", "Template:",
)

# Method tag → DB method value
_METHOD_TAG_MAP = {
    "(static)":    "static",
    "(gift)":      "gift",
    "(starter)":   "gift",
    "(trade)":     "trade",
    "(quest)":     "static",     # quest encounters are one-time static
    "(fishing)":   "fishing",
    "(Pokéradar)": "wild",       # Pokéradar-chained encounters are still wild
}


def _is_meta_link(page_name: str) -> bool:
    return any(page_name.startswith(p) for p in _META_PREFIXES)


def _canonical_name(raw: str) -> str:
    """Extract canonical page name from [[Page|Display]] or [[Page]]."""
    return raw.split("|")[0].strip()


def _parse_location_field(field: str) -> list[tuple[str, str, str | None]]:
    """
    Parse one PokedexTable/Data location field.

    Returns list of (canonical_location_name, method, notes).
    Wild encounters have notes=None; others may have a short note.
    """
    results: list[tuple[str, str, str | None]] = []

    # ── Bold+method groups: '''''[[Loc]]''''' [[..|(method)]] ────────────────
    # These indicate a special encounter type (static / gift / trade / quest).
    bold_re = re.compile(
        r"'''''\[\[([^\]]+)\]\]'''''"   # bold wiki link
        r"((?:\s*\[\[[^\]]+\]\])*)"     # zero or more trailing [[...]] tags
    )
    bold_positions: list[tuple[int, int]] = []

    for m in bold_re.finditer(field):
        bold_positions.append((m.start(), m.end()))
        page_raw = m.group(1)
        tags_str = m.group(2)

        page_parts = page_raw.split("|", 1)
        page_name = page_parts[0].strip()
        display_name = page_parts[1].strip() if len(page_parts) > 1 else page_name

        if _is_meta_link(page_name):
            # For "List of …" pages the display text describes the find mechanic
            # (e.g. "Trash Cans", "Destroying Sandcastles") — use it as the location.
            # For other meta prefixes (Field Moves, Quests …) there is no useful name.
            if not page_name.startswith(("List of", "List_of")) or not display_name:
                continue
            loc = display_name
        else:
            loc = page_name

        # Determine method from tag(s)
        method = "static"  # default for bold entries
        for tag_str, tag_method in _METHOD_TAG_MAP.items():
            if tag_str in tags_str:
                method = tag_method
                break

        results.append((loc, method, None))

    # ── Remove bold segments + evolution strings → remaining = wild links ────
    cleaned = bold_re.sub(" ", field)
    cleaned = re.sub(r"Evolve\s[^,\[]+", " ", cleaned)
    cleaned = re.sub(r"\[\[(?:List of|Quests|Pokéradar|Field Moves)[^\]]*\]\]", " ", cleaned)

    # ── Extract plain [[...]] links as wild encounters ────────────────────────
    plain_re = re.compile(r"\[\[([^\]]+)\]\]")
    for m in plain_re.finditer(cleaned):
        loc = _canonical_name(m.group(1))
        if not loc or _is_meta_link(loc):
            continue
        results.append((loc, "wild", None))

    return results


def fetch_pokedex_content() -> str:
    LOGGER.info("Fetching IF Pokédex wiki page...")
    r = httpx.get(
        WIKI_API,
        params={
            "action": "query",
            "titles": POKEDEX_PAGE,
            "prop": "revisions",
            "rvprop": "content",
            "format": "json",
            "formatversion": "2",
        },
        follow_redirects=True,
        timeout=30,
        headers={"User-Agent": USER_AGENT},
    )
    r.raise_for_status()
    pages = r.json()["query"]["pages"]
    content = pages[0]["revisions"][0]["content"]
    LOGGER.info("Fetched %d chars", len(content))
    return content


def parse_pokedex(content: str) -> list[tuple[int, str, str, str | None]]:
    """
    Returns list of (if_id, location_name, method, notes).
    """
    entries: list[tuple[int, str, str, str | None]] = []
    lines = [l for l in content.split("\n") if l.startswith("{{PokedexTable/Data")]

    # Fail loudly instead of silently loading nothing: when the wiki moved the
    # table off the top-level "Pokédex" page, this parsed 0 lines and the step
    # still reported success.
    if not lines:
        raise RuntimeError(
            f"Parsed 0 PokedexTable/Data lines from '{POKEDEX_PAGE}' — the "
            f"wiki page has likely changed upstream again."
        )

    for line in lines:
        # Strip template markers and split on |
        inner = line.removeprefix("{{PokedexTable/Data|").rstrip("}").rstrip("|")
        parts = inner.split("|")
        # parts[0]=IF_ID, parts[1]=NAT_ID, parts[2]=Name, parts[3]=Form (usually empty),
        # parts[4]=Type1, parts[5]=Type2(or empty), parts[6..]=Location field
        # NOTE: wiki links like [[Page|Display]] contain | which breaks the split.
        # Fix: rejoin from parts[6] and trim after the last ]] to recover the full field.
        if len(parts) < 7:
            continue
        try:
            if_id = int(parts[0].strip())
        except ValueError:
            continue
        raw_tail = "|".join(parts[6:])
        last_bracket = raw_tail.rfind("]]")
        if last_bracket == -1:
            continue  # no wiki links → evolution-only or no location
        location_field = raw_tail[: last_bracket + 2].strip()
        if not location_field:
            continue

        for loc_name, method, notes in _parse_location_field(location_field):
            entries.append((if_id, loc_name, method, notes))

    LOGGER.info("Parsed %d (pokemon, location, method) tuples from %d lines", len(entries), len(lines))
    return entries


def load_pokedex_locations(conn) -> None:
    cur = conn.cursor()

    # ── Fetch pokemon IF_ID → DB pokemon_id map ──────────────────────────────
    cur.execute("SELECT id FROM pokemon ORDER BY id")
    valid_ids: set[int] = {row[0] for row in cur.fetchall()}

    content = fetch_pokedex_content()
    entries = parse_pokedex(content)

    # ── Collect all location names and ensure they exist ─────────────────────
    location_names: set[str] = {loc for _, loc, _, _ in entries}
    for loc_name in sorted(location_names):
        cur.execute(
            "INSERT INTO location (name_en) VALUES (%s) ON CONFLICT (name_en) DO NOTHING",
            (loc_name,),
        )

    cur.execute("SELECT id, name_en FROM location")
    loc_id_map: dict[str, int] = {name: lid for lid, name in cur.fetchall()}

    # ── Insert pokemon_location rows ──────────────────────────────────────────
    inserted = skipped_poke = skipped_loc = skipped_conflict = 0

    for if_id, loc_name, method, notes in entries:
        if if_id not in valid_ids:
            skipped_poke += 1
            continue
        lid = loc_id_map.get(loc_name)
        if lid is None:
            skipped_loc += 1
            LOGGER.warning("Location not found after insert: %r", loc_name)
            continue

        cur.execute(
            """INSERT INTO pokemon_location (pokemon_id, location_id, method, notes)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (pokemon_id, location_id, method) DO NOTHING""",
            (if_id, lid, method, notes),
        )
        if cur.rowcount:
            inserted += 1
        else:
            skipped_conflict += 1

    conn.commit()
    LOGGER.info(
        "Done — %d inserted | %d already present | %d unknown pokemon | %d unknown location",
        inserted, skipped_conflict, skipped_poke, skipped_loc,
    )


def main() -> None:
    with pg_connection() as conn:
        load_pokedex_locations(conn)


if __name__ == "__main__":
    main()
