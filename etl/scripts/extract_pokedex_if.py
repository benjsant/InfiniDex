"""
ETL Step 1 — Extract Pokédex from Infinite Fusion wiki (MediaWiki API).

Fetches the Pokédex page and parses all 501 Pokémon entries:
  - IF internal ID
  - Name (EN)
  - Type1, Type2
  - Generation
  - Location (raw string)
  - Hoenn-only flag

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

# Template pattern inside wikitext:
# {{PokedexTable/Data|index|id|name|type1|type2|location|notes}}
ENTRY_RE = re.compile(
    r"\{\{PokedexTable/Data\s*\|"
    r"\s*(?P<index>\d+)\s*\|"
    r"\s*(?P<id>\d+)\s*\|"
    r"\s*(?P<name>[^|]+?)\s*\|"
    r"\s*(?P<type1>[^|]*?)\s*\|"
    r"\s*(?P<type2>[^|]*?)\s*\|"
    r"\s*(?P<location>[^|]*?)\s*\|?"
    r"(?P<notes>[^}]*)?\}\}",
    re.IGNORECASE,
)

# Pokémon marked "Not in game" / "Hoenn only"
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


def main() -> None:
    LOGGER.info("Fetching Pokédex wikitext from Infinite Fusion wiki...")
    wikitext = fetch_wikitext("Pokédex")
    entries  = parse_entries(wikitext)

    save_json(OUTPUT, entries)
    LOGGER.info("Saved %d entries → %s", len(entries), OUTPUT)


if __name__ == "__main__":
    main()
