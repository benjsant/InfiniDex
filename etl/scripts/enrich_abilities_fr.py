"""
ETL — Enrich abilities with French names and descriptions from PokeAPI.

Reads  : data/abilities_if.json  (178 abilities, name_en only)
Writes : data/abilities_if.json  (in-place, adds name_fr + description_fr)

Slug rule: name_en.lower().replace(' ', '-')
Version priority for description: ultra-sun-ultra-moon > sun-moon > omega-ruby-alpha-sapphire > x-y
"""

from __future__ import annotations

from pathlib import Path

from etl.utils.io import load_json, save_json
from etl.utils.logging import setup_logging
from etl.utils.pokeapi import (
    enrich_items_parallel,
    fetch_fr_translation,
    sleep_between_requests,
)

LOGGER = setup_logging(__name__)

POKEAPI      = "https://pokeapi.co/api/v2/ability/{slug}"
DATA_FILE    = Path("data/abilities_if.json")
SAVE_EVERY   = 50
MAX_WORKERS  = 2       # PokeAPI fair-use: keep concurrency low
REQUEST_DELAY = 0.2    # ~10 req/s peak with 2 workers
VERSION_PRIO = ["ultra-sun-ultra-moon", "sun-moon", "omega-ruby-alpha-sapphire", "x-y"]

# Manual slug overrides for cases where IF wiki name differs from PokeAPI slug
MANUAL_SLUGS: dict[str, str] = {}


def slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "")


def _enrich_one(ability: dict) -> tuple[dict, str | None, str | None]:
    name_en = ability["name_en"]
    slug    = MANUAL_SLUGS.get(name_en, slugify(name_en))
    name_fr, desc_fr = fetch_fr_translation(
        POKEAPI.format(slug=slug), VERSION_PRIO, logger=LOGGER,
    )
    sleep_between_requests(REQUEST_DELAY)
    return ability, name_fr, desc_fr


def main() -> None:
    abilities: list[dict] = load_json(DATA_FILE)

    to_enrich = [a for a in abilities if a.get("name_fr") is None]
    LOGGER.info("%d abilities to enrich (out of %d)", len(to_enrich), len(abilities))

    def save() -> None:
        save_json(DATA_FILE, abilities)

    found, not_found = enrich_items_parallel(
        to_enrich,
        _enrich_one,
        save=save,
        logger=LOGGER,
        save_every=SAVE_EVERY,
        max_workers=MAX_WORKERS,
        label="abilities",
    )

    LOGGER.info("Done — %d FR found | %d not found", found, len(not_found))
    if not_found:
        LOGGER.warning("Not found: %s", not_found)


if __name__ == "__main__":
    main()
