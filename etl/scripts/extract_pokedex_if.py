"""
ETL Step 1 — Extract Pokédex from Infinite Fusion wiki (MediaWiki API).

Fetches the Pokédex subpages and parses every Pokémon entry:
  - IF internal ID
  - Name (EN)
  - Type1, Type2
  - Generation
  - Location (raw string)
  - Hoenn-only flag (present in Hoenn/Classic but absent from Kanto/Classic)

Output: data/pokedex_if.json
        data/pokedex_baseline.txt (committed entry count, read by check_sources)
"""

from __future__ import annotations

import re
from pathlib import Path

from etl.utils.io import save_json
from etl.utils.logging import setup_logging
from etl.utils.wikitext import clean_wikitext, fetch_wikitext, parse_template_calls

LOGGER = setup_logging(__name__)

OUTPUT = Path("data/pokedex_if.json")
# Committed entry count of the last successful extraction. check_sources.py
# compares the live wiki to it, so the weekly CI watch notices NEW Pokémon too
# (a `>= 572` floor let 10 additions pass unnoticed in 2026-09).
BASELINE = Path("data/pokedex_baseline.txt")

# The IF wiki restructured its Pokédex: the "Pokédex" page is now a hub linking
# to four subpages, and holds no data at all. The full table lives in the page
# below (Kanto + Hoenn additions), which still uses PokedexTable/Data.
PAGE = "Pokédex/Hoenn/Classic"

# The restructure also dropped the "Not in game" / "Hoenn" markers that used to
# flag Hoenn-only Pokémon. That information is now encoded structurally: the
# Kanto page lists the classic 501, the Hoenn page adds the rest — the extra ids
# are the Hoenn-only set. We fetch the Kanto page too and take the set difference.
KANTO_PAGE = "Pokédex/Kanto/Classic"

# Template inside wikitext, parsed with MediaWiki positional semantics:
# {{PokedexTable/Data|index|id|name|form|type1|type2|location|notes}}
#
# `form` was added by the 2026-07 restructure and is empty for most rows
# (Oricorio "Baile Style", Castform "Sunny", Shellos "East", ...). It is carried
# into the output JSON: fix_form_pokemon.py resolves the PokeAPI form slug from
# it, since those rows share a name and can't get a national_id (UNIQUE).
TEMPLATE = "PokedexTable/Data"

# Legacy "Not in game" / "Hoenn only" markers. The restructured pages no longer
# carry them (the Kanto/Hoenn set difference is authoritative now) but they are
# kept as a safety net in case the wiki reintroduces per-row notes.
HOENN_ONLY_RE = re.compile(r"not in game|hoenn", re.IGNORECASE)

# The 18 standard Pokémon types (lowercase)
STANDARD_TYPES = {
    "normal", "fire", "water", "electric", "grass", "ice", "fighting",
    "poison", "ground", "flying", "psychic", "bug", "rock", "ghost",
    "dragon", "dark", "steel", "fairy",
}

# Generation boundaries (IF Pokédex index → gen number)
# Gen 1: index 1-151 / Gen 2: 152-251 / Gen 3+: 252+
GEN_BOUNDARIES = [
    (1,   151, 1),
    (152, 251, 2),
    (252, 999, 3),   # Gen 3-7 grouped initially; refined later via PokeAPI national_id
]


def detect_generation(index: int) -> int:
    for start, end, gen in GEN_BOUNDARIES:
        if start <= index <= end:
            return gen
    return 3


def parse_entries(wikitext: str) -> list[dict]:
    """Parse every PokedexTable/Data row of a Pokédex subpage.

    Template params (MediaWiki positions): 1=index 2=id 3=name 4=form
    5=type1 6=type2 7=location 8=notes. Parsed with `parse_template_calls`
    rather than a fixed-arity regex: since 2026-09 some rows skip empty
    columns with a named param (`|Water|7=Route 119 (Egg, Team Aqua)}}`),
    which made the old regex run past `}}` and swallow the following row
    (Gastrodon East/West silently disappeared).
    """
    entries = []
    seen_ids: set[int] = set()

    for params in parse_template_calls(wikitext, TEMPLATE):
        try:
            index = int(params.get(1, ""))
            if_id = int(params.get(2, ""))
        except ValueError:
            LOGGER.warning("Unparseable PokedexTable/Data row skipped: %r", params)
            continue

        name      = clean_wikitext(params.get(3, ""))
        type1_raw = clean_wikitext(params.get(5, "")).lower() or None
        type2_raw = clean_wikitext(params.get(6, "")).lower() or None

        type1 = type1_raw if type1_raw in STANDARD_TYPES else None
        type2 = type2_raw if type2_raw in STANDARD_TYPES else None

        # Legacy IF wiki convention (pre-`form` column): alternate-form rows
        # put the form name in the type1 column and the real type in type2.
        # Promote type2 → type1 so these mono-type forms keep a primary type.
        if type1 is None and type1_raw and type2 is not None:
            LOGGER.info(
                "Form label %r in type1 for #%d %s — promoting %r to primary type",
                type1_raw, if_id, name, type2,
            )
            type1, type2 = type2, None
        else:
            if type1_raw and not type1:
                LOGGER.warning("Invalid type1 %r for #%d %s — set to None", type1_raw, if_id, name)
            if type2_raw and not type2:
                LOGGER.warning("Invalid type2 %r for #%d %s — set to None", type2_raw, if_id, name)
        location = clean_wikitext(params.get(7, ""))
        notes    = clean_wikitext(params.get(8, ""))

        if if_id in seen_ids:
            continue
        seen_ids.add(if_id)

        if not name or name.startswith("{{"):
            continue

        # Legacy marker only, and only in the notes column: free-text
        # locations may legitimately mention Hoenn. The Kanto/Hoenn page
        # diff (mark_hoenn_only) is the real authority.
        is_hoenn_only = bool(HOENN_ONLY_RE.search(notes))

        entries.append({
            "if_id":        if_id,
            "index":        index,
            "name_en":      name,
            "form":         clean_wikitext(params.get(4, "")) or None,
            "type1":        type1,
            "type2":        type2 if type2 else None,
            "generation":   detect_generation(index),
            "location_raw": location,
            "is_hoenn_only": is_hoenn_only,
        })

    LOGGER.info("Parsed %d Pokémon entries", len(entries))
    return sorted(entries, key=lambda e: e["if_id"])


def extract_ids(wikitext: str) -> set[int]:
    """IF ids present in a Pokédex subpage — used for the Kanto/Hoenn diff."""
    ids: set[int] = set()
    for params in parse_template_calls(wikitext, TEMPLATE):
        raw = params.get(2, "")
        if raw.isdigit():
            ids.add(int(raw))
    return ids


def mark_hoenn_only(entries: list[dict], kanto_ids: set[int]) -> int:
    """Flag entries absent from the Kanto page as Hoenn-only. Returns the count."""
    flagged = 0
    for e in entries:
        e["is_hoenn_only"] = e["is_hoenn_only"] or e["if_id"] not in kanto_ids
        flagged += e["is_hoenn_only"]
    return flagged


def main() -> None:
    LOGGER.info("Fetching Pokédex wikitext from Infinite Fusion wiki (%s)...", PAGE)
    wikitext = fetch_wikitext(PAGE)
    entries  = parse_entries(wikitext)

    # Fail loudly instead of silently loading an empty Pokédex. Previously an
    # upstream page restructure made this parse 0 entries, the pipeline still
    # reported success, and the whole DB ended up empty (0 Pokémon, 0 sprites).
    if not entries:
        raise RuntimeError(
            f"Parsed 0 Pokémon from '{PAGE}' — the wiki page or the "
            f"PokedexTable/Data template has likely changed upstream again."
        )

    LOGGER.info("Fetching Kanto Pokédex for the Hoenn-only diff (%s)...", KANTO_PAGE)
    kanto_ids = extract_ids(fetch_wikitext(KANTO_PAGE))
    if not kanto_ids:
        raise RuntimeError(
            f"Parsed 0 Pokémon from '{KANTO_PAGE}' — cannot derive the "
            f"Hoenn-only flag; the wiki has likely changed upstream again."
        )
    flagged = mark_hoenn_only(entries, kanto_ids)
    LOGGER.info("Hoenn-only flags: %d (Kanto page has %d ids)", flagged, len(kanto_ids))

    save_json(OUTPUT, entries)
    LOGGER.info("Saved %d entries → %s", len(entries), OUTPUT)

    BASELINE.write_text(f"{len(entries)}\n", encoding="utf-8")
    LOGGER.info("Baseline Pokédex → %d (%s)", len(entries), BASELINE.name)


if __name__ == "__main__":
    main()
