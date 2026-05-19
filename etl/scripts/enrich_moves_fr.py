"""
ETL Step 3b — Enrich moves with French names from PokeAPI.

For each move in moves_if.json, query PokeAPI /move/{slug} to fetch the
FR name.
Slug = name_en.lower().replace(" ", "-"), e.g. "Bug Bite" → "bug-bite"

Updates moves_if.json in place with name_fr filled in.
Idempotent: skips moves that already have a name_fr.

Output: data/moves_if.json (modified in-place with name_fr)
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

POKEAPI_MOVE  = "https://pokeapi.co/api/v2/move/{}"
MOVES_FILE    = Path("data/moves_if.json")
MAX_WORKERS   = 4
REQUEST_DELAY = 0.05   # seconds per worker

# Version priority for the FR description — take the most recent available
VERSION_PRIO = [
    "ultra-sun-ultra-moon", "sun-moon", "omega-ruby-alpha-sapphire", "x-y",
    "black-2-white-2", "black-white",
    "lets-go-pikachu-lets-go-eevee", "sword-shield",  # fallback Gen 8+ moves
]

# Manual fixes: IF wiki name → exact PokeAPI slug
MANUAL_SLUGS: dict[str, str] = {
    "Smelling Salts":      "smelling-salts",
    "Vice Grip":           "vice-grip",
    "SolarBeam":           "solar-beam",
    "SonicBoom":           "sonic-boom",
    "ThunderPunch":        "thunder-punch",
    "ThunderShock":        "thunder-shock",
    "FirePunch":           "fire-punch",
    "IcePunch":            "ice-punch",
    "ExtremeSpeed":        "extreme-speed",
    "DynamicPunch":        "dynamic-punch",
    "DoubleSlap":          "double-slap",
    "Softboiled":          "soft-boiled",
    "PoisonPowder":        "poison-powder",
    "PinMissile":          "pin-missile",
    "TwinNeedle":          "twineedle",
    "Hi Jump Kick":        "high-jump-kick",
    "Smokescreen":         "smokescreen",
    "Sand-Attack":         "sand-attack",
    "Growl":               "growl",
    "Tail Whip":           "tail-whip",
}


def to_slug(name_en: str) -> str:
    """Convert move name to PokeAPI slug."""
    if name_en in MANUAL_SLUGS:
        return MANUAL_SLUGS[name_en]
    return name_en.lower().replace(" ", "-").replace("'", "").replace(".", "")


def _enrich_one(move: dict) -> tuple[dict, str | None, str | None]:
    slug = to_slug(move["name_en"])
    name_fr, desc_fr = fetch_fr_translation(
        POKEAPI_MOVE.format(slug), VERSION_PRIO, logger=LOGGER,
    )
    sleep_between_requests(REQUEST_DELAY)
    return move, name_fr, desc_fr


def main() -> None:
    if not MOVES_FILE.exists():
        raise FileNotFoundError("data/moves_if.json not found — run extract_moves_if.py first")

    moves = load_json(MOVES_FILE)
    to_enrich = [m for m in moves if not m.get("name_fr") or not m.get("description_fr")]
    LOGGER.info("%d moves to enrich in FR (out of %d)", len(to_enrich), len(moves))

    def save() -> None:
        save_json(MOVES_FILE, moves)

    found, not_found = enrich_items_parallel(
        to_enrich,
        _enrich_one,
        save=save,
        logger=LOGGER,
        save_every=100,
        max_workers=MAX_WORKERS,
        label="moves",
    )

    LOGGER.info("Done — %d FR found | %d not found", found, len(not_found))

    missing = [m["name_en"] for m in moves if not m.get("name_fr")]
    if missing:
        LOGGER.warning("%d moves without an FR name: %s", len(missing), missing[:20])


if __name__ == "__main__":
    main()
