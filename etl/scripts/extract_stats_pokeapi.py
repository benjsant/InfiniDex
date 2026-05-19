"""
ETL Step 2 — Enrich Pokémon with PokeAPI data.

For each Pokémon in data/pokedex_if.json that has a national_id equivalent,
fetches from PokeAPI:
  - Base stats (HP, Atk, Def, SpAtk, SpDef, Vit)
  - base_experience
  - national_id (for cross-referencing)
  - name_fr (from species endpoint)
  - Evolution chain (official, to be overridden by IF-specific rules)

Inspired by lets-go-predictiondex/etl_pokemon/scripts/etl_enrich_pokeapi.py
but adapted for Gen 1-7 and 501 Pokémon with evolution chains.

Output: data/pokemon_stats.json, data/evolutions_base.json
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from etl.utils.http import get_json
from etl.utils.io import load_json, save_json
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

POKEAPI_BASE    = "https://pokeapi.co/api/v2"
INPUT_FILE      = Path("data/pokedex_if.json")
OUTPUT_STATS    = Path("data/pokemon_stats.json")
OUTPUT_EVOS     = Path("data/evolutions_base.json")

MAX_WORKERS     = 2      # PokeAPI fair-use: keep concurrency low
REQUEST_DELAY   = 0.2    # seconds between requests per thread (~10 req/s peak)

STAT_MAP = {
    "hp":              "hp",
    "attack":          "attack",
    "defense":         "defense",
    "special-attack":  "sp_attack",
    "special-defense": "sp_defense",
    "speed":           "speed",
}


# ─── PokeAPI helpers ──────────────────────────────────────────────────────────

def fetch_pokemon(national_id: int) -> dict | None:
    data = get_json(f"{POKEAPI_BASE}/pokemon/{national_id}")
    time.sleep(REQUEST_DELAY)
    return data


def fetch_species(national_id: int) -> dict | None:
    data = get_json(f"{POKEAPI_BASE}/pokemon-species/{national_id}")
    time.sleep(REQUEST_DELAY)
    return data


def fetch_evolution_chain(url: str) -> dict | None:
    data = get_json(url)
    time.sleep(REQUEST_DELAY)
    return data


def extract_name_fr(species_data: dict) -> str | None:
    for entry in species_data.get("names", []):
        if entry["language"]["name"] == "fr":
            return entry["name"]
    return None


def extract_stats(pokemon_data: dict) -> dict:
    return {
        STAT_MAP[s["stat"]["name"]]: s["base_stat"]
        for s in pokemon_data["stats"]
        if s["stat"]["name"] in STAT_MAP
    }


# ─── Evolution chain parsing ──────────────────────────────────────────────────

def _parse_chain_node(node: dict, results: list[dict]) -> None:
    """
    Recursively walk an evolution chain node and extract all evolutions.
    Each evolution becomes a dict:
      { from_name, into_name, trigger, min_level, item }
    """
    species_name = node["species"]["name"]

    for evo in node.get("evolves_to", []):
        into_name = evo["species"]["name"]
        for detail in evo.get("evolution_details", []):
            trigger   = detail.get("trigger", {}).get("name", "other")
            min_level = detail.get("min_level")
            item      = (detail.get("item") or {}).get("name")

            # Map PokeAPI trigger names to our schema
            trigger_map = {
                "level-up":   "level_up",
                "use-item":   "use_item",
                "trade":      "trade",
                "shed":       "other",
                "spin":       "other",
                "tower-of-darkness": "other",
                "tower-of-waters":   "other",
                "agile-style-move":  "other",
                "strong-style-move": "other",
                "recoil-damage":     "other",
                "take-damage":       "other",
                "other":      "other",
            }
            results.append({
                "from_name":  species_name,
                "into_name":  into_name,
                "trigger":    trigger_map.get(trigger, "other"),
                "min_level":  min_level,
                "item":       item,
            })

        _parse_chain_node(evo, results)


def parse_evolution_chain(chain_data: dict) -> list[dict]:
    results: list[dict] = []
    _parse_chain_node(chain_data["chain"], results)
    return results


# ─── Per-Pokémon worker ───────────────────────────────────────────────────────

def process_pokemon(entry: dict) -> tuple[dict | None, list[dict]]:
    """
    Fetch stats + name_fr + evolution chain for one Pokémon.
    Returns (stats_record, evolution_list).
    national_id = if_id for Gen 1-2 (1-251); beyond that we try anyway.
    """
    if_id       = entry["if_id"]
    national_id = if_id   # assumption: Gen 1-2 IDs are identical; others may fail gracefully

    pokemon_data = fetch_pokemon(national_id)
    if not pokemon_data:
        LOGGER.warning("[SKIP] #%d %s — not found in PokeAPI", if_id, entry["name_en"])
        return None, []

    species_data = fetch_species(national_id)
    name_fr      = extract_name_fr(species_data) if species_data else None
    evolutions: list[dict] = []

    if species_data:
        chain_url = species_data.get("evolution_chain", {}).get("url")
        if chain_url:
            chain_data = fetch_evolution_chain(chain_url)
            if chain_data:
                evolutions = parse_evolution_chain(chain_data)

    stats_record = {
        "if_id":          if_id,
        "national_id":    pokemon_data["id"],
        "name_fr":        name_fr,
        "base_experience": pokemon_data.get("base_experience"),
        **extract_stats(pokemon_data),
    }

    LOGGER.info("  [OK] #%d %s", if_id, entry["name_en"])
    return stats_record, evolutions


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"{INPUT_FILE} not found — run extract_pokedex_if.py first")

    entries = load_json(INPUT_FILE)
    force = "--force" in sys.argv

    # Idempotence: reuse already-fetched stats so re-runs don't re-hammer
    # PokeAPI. `--force` re-fetches everything.
    all_stats:  list[dict] = []
    all_evos:   list[dict] = []
    seen_chains: set[str]  = set()
    if not force and OUTPUT_STATS.exists():
        all_stats = load_json(OUTPUT_STATS)
        if OUTPUT_EVOS.exists():
            all_evos = load_json(OUTPUT_EVOS)
            seen_chains = {
                f"{e['from_name']}→{e['into_name']}→{e['trigger']}→{e['item']}"
                for e in all_evos
            }
    done_ids = {r["if_id"] for r in all_stats}
    todo = [e for e in entries if e["if_id"] not in done_ids]

    LOGGER.info(
        "Enriching %d/%d Pokémon via PokeAPI (threads=%d, %d cached)...",
        len(todo), len(entries), MAX_WORKERS, len(done_ids),
    )
    if not todo:
        LOGGER.info("All Pokémon already enriched — nothing to fetch.")
        save_json(OUTPUT_STATS, sorted(all_stats, key=lambda x: x["if_id"]))
        save_json(OUTPUT_EVOS, all_evos)
        return

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_pokemon, e): e for e in todo}
        for future in as_completed(futures):
            stats, evos = future.result()
            if stats:
                all_stats.append(stats)
            for evo in evos:
                key = f"{evo['from_name']}→{evo['into_name']}→{evo['trigger']}→{evo['item']}"
                if key not in seen_chains:
                    seen_chains.add(key)
                    all_evos.append(evo)

    all_stats.sort(key=lambda x: x["if_id"])

    save_json(OUTPUT_STATS, all_stats)
    save_json(OUTPUT_EVOS,  all_evos)

    LOGGER.info("Saved %d stat records → %s", len(all_stats), OUTPUT_STATS)
    LOGGER.info("Saved %d evolutions   → %s", len(all_evos),  OUTPUT_EVOS)


if __name__ == "__main__":
    main()
