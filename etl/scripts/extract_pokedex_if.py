"""
ETL Step 1 — Extract Pokédex from Infinite Fusion wiki (MediaWiki API).

Fetches the Pokédex subpages and parses all 572 Pokémon entries:
  - IF internal ID
  - Name (EN)
  - Type1, Type2
  - Generation
  - Location (raw string)
  - Hoenn-only flag (present in Hoenn/Classic but absent from Kanto/Classic)

Output: data/pokedex_if.json
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from etl.utils.io import save_json
from etl.utils.logging import setup_logging
from etl.utils.wikitext import clean_wikitext, fetch_wikitext

LOGGER = setup_logging(__name__)

OUTPUT = Path("data/pokedex_if.json")

# The IF wiki restructured its Pokédex: the "Pokédex" page is now a hub linking
# to four subpages, and holds no data at all. The full 572-entry table lives in
# the page below (Kanto + Hoenn additions), which still uses PokedexTable/Data.
PAGE = "Pokédex/Hoenn/Classic"

# The restructure also dropped the "Not in game" / "Hoenn" markers that used to
# flag Hoenn-only Pokémon. That information is now encoded structurally: the
# Kanto page lists 501 entries, the Hoenn page 572 — the 71 extra ids are the
# Hoenn-only set. We fetch the Kanto page too and take the set difference.
KANTO_PAGE = "Pokédex/Kanto/Classic"

# Template pattern inside wikitext:
# {{PokedexTable/Data|index|id|name|form|type1|type2|location|notes}}
#
# `form` was added by the same restructure and is empty for all but 14 entries
# (Oricorio "Baile Style", Lycanroc "Midday Form", Castform "Sunny", ...). It is
# NOT captured into the output: the DB has no column for it, and each form
# already has its own IF id. But it MUST be matched — otherwise every field
# shifts left and Bulbasaur comes out as Grass/(none) instead of Grass/Poison.
ENTRY_RE = re.compile(
    r"\{\{PokedexTable/Data\s*\|"
    r"\s*(?P<index>\d+)\s*\|"
    r"\s*(?P<id>\d+)\s*\|"
    r"\s*(?P<name>[^|]+?)\s*\|"
    r"\s*(?P<form>[^|]*?)\s*\|"
    r"\s*(?P<type1>[^|]*?)\s*\|"
    r"\s*(?P<type2>[^|]*?)\s*\|"
    r"\s*(?P<location>[^|]*?)\s*\|?"
    r"(?P<notes>[^}]*)?\}\}",
    re.IGNORECASE,
)

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
    entries = []
    seen_ids: set[int] = set()

    for match in ENTRY_RE.finditer(wikitext):
        index    = int(match.group("index"))
        if_id    = int(match.group("id"))
        name     = clean_wikitext(match.group("name"))
        type1_raw = clean_wikitext(match.group("type1")).lower() or None
        type2_raw = clean_wikitext(match.group("type2")).lower() or None

        type1 = type1_raw if type1_raw in STANDARD_TYPES else None
        type2 = type2_raw if type2_raw in STANDARD_TYPES else None

        # IF wiki convention: alternate-form rows put the form name in the
        # type1 column (e.g. "pom-pom style", "midnight form", "sunny") and
        # the form's single real type in type2. Promote type2 → type1 so
        # these mono-type forms keep a primary type instead of none.
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
        location = clean_wikitext(match.group("location"))
        notes    = clean_wikitext(match.group("notes") or "")

        if if_id in seen_ids:
            continue
        seen_ids.add(if_id)

        if not name or name.startswith("{{"):
            continue

        is_hoenn_only = bool(HOENN_ONLY_RE.search(notes) or HOENN_ONLY_RE.search(location))

        entries.append({
            "if_id":        if_id,
            "index":        index,
            "name_en":      name,
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
    return {int(m.group("id")) for m in ENTRY_RE.finditer(wikitext)}


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


if __name__ == "__main__":
    main()
