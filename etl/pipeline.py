"""
FusionDex ETL pipeline orchestrator.

Steps:
  1.   extract_pokedex_if       — 572 Pokémon from IF wiki (501 in-game + 71 Hoenn-only)
  2a.  extract_stats_pokeapi    — stats + name_fr + evolutions from PokeAPI
  2b.  extract_pokepedia_names  — name_en → Pokepedia slug + gen7 URL mapping
  3.   extract_moves_if         — 676 moves + 121 TMs + 40 tutors + 57 expert tutors from IF wiki
  3b.  enrich_moves_fr          — add name_fr + description_fr to moves via PokeAPI
  4.   extract_abilities_if     — 178 abilities from IF wiki
  4b.  enrich_abilities_fr      — add name_fr + description_fr to abilities via PokeAPI
  5.   extract_encounters_if    — wild/static/legendary encounters (location + method + level)
  6.   scrapy (if_movesets)     — movesets from Pokepedia (USUL Gen 7)
                                   level_up (USUL col) + tm + breeding + tutor
  7.   transform_merge_movesets — merge base movesets + IF overrides
  8.   load_db                  — load all data into PostgreSQL
  8b.  fix_pokemon_types        — fix Pokémon types from PokeAPI (overrides wiki data)
  8c.  enrich_evolution_movesets — inherit moves from pre-evolutions
  8d.  fix_national_ids         — fix national_id (IF dex diverges from national after #251)
  8e.  fix_stats_and_fr_names   — re-sync stats + name_fr with corrected national_ids
  8f.  fix_tms_from_pokeapi     — fill TM learnability gaps from PokeAPI
  9.   seed_type_effectiveness  — 18×18 type chart with FR names from table_type.csv
  9b.  load_encounters          — load locations + pokemon_location from encounters_if.json
  9c.  enrich_pokemon_fr        — enrich pokemon.pokepedia_url from Pokepedia mapping
  9d.  load_items               — fusion + evolution + valuable items from IF wiki
  9e.  load_move_tutors         — move tutors (NPC teachers) from IF wiki
  9e-bis. fix_tutors_from_pokeapi — fill tutor learnability gaps from PokeAPI
  9f.  load_tm_locations        — TM locations from IF wiki
  9g.  fix_move_experts         — move_expert_move (Knot Island + Boon Island) from IF wiki
  10.  extract_sprites          — download spritesheets from infinitefusion.net
                                   crop 96×96 cells → data/sprites/{h}.{b}.png
  11a. extract_triple_fusions   — 23 post-game triple fusions from IF wiki
  11b. load_triple_fusions      — triple_fusion + components + types + abilities
  12.  load_sprite_credits      — 7k creators + 166k fusion_sprite + 172k joins
                                   from data/sprite_credits.csv

Usage:
  python etl/pipeline.py          # skip if data already loaded
  python etl/pipeline.py --force  # force full re-run
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

BASE_DIR    = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "scripts"
SCRAPER_DIR = BASE_DIR / "pokepedia_scraper"


def run(cmd: Sequence[str], label: str, cwd: Path | None = None) -> None:
    print(f"\n▶ {label}", flush=True)
    result = subprocess.run(cmd, shell=False, check=False, cwd=cwd)
    if result.returncode != 0:
        print(f"[FAIL] {label}", flush=True)
        sys.exit(1)


def check_already_loaded() -> bool:
    """Return True if the DB already contains a full load.

    Checks four tables to detect a partial or empty load:
      - pokemon      ≥ 500   (572 expected)
      - move         ≥ 600   (676 expected)
      - ability      ≥ 150   (178 expected)
      - pokemon_move ≥ 30000 (≈40 000 expected)
    """
    THRESHOLDS = {
        "pokemon":       500,
        "move":          600,
        "ability":       150,
        "pokemon_move":  30_000,
        "fusion_sprite": 100_000,
        "creator":       5_000,
        "triple_fusion": 20,
    }
    try:
        import psycopg2  # noqa: PLC0415

        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "db"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            dbname=os.getenv("POSTGRES_DB", "fusiondex_db"),
            user=os.getenv("POSTGRES_USER", "fusiondex_user"),
            password=os.getenv("POSTGRES_PASSWORD", "fusiondex_password"),
            connect_timeout=5,
        )
        cur = conn.cursor()
        for table, threshold in THRESHOLDS.items():
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            count = cur.fetchone()[0]
            if count < threshold:
                print(f"[ETL] {table}: {count} < {threshold} — reloading")
                cur.close()
                conn.close()
                return False
        cur.close()
        conn.close()
        return True
    except Exception:
        return False


def main(force: bool = False) -> None:
    if check_already_loaded() and not force:
        print("[ETL] Data already loaded. Skipping (use --force to rerun).")
        return

    print("[ETL] Starting FusionDex pipeline...", flush=True)

    # Step 1 — Pokédex list from IF wiki
    run(
        ["python", str(SCRIPTS_DIR / "extract_pokedex_if.py")],
        "Step 1/8 — Extract Pokédex from IF wiki",
    )

    # Step 2a — Stats + name_fr + evolutions from PokeAPI
    run(
        ["python", str(SCRIPTS_DIR / "extract_stats_pokeapi.py")],
        "Step 2a/8 — Enrich via PokeAPI (stats, FR names, evolutions)",
    )

    # Step 2b — Pokepedia name mapping (name_en → slug + gen7 URL)
    run(
        ["python", str(SCRIPTS_DIR / "extract_pokepedia_names.py")],
        "Step 2b/8 — Build Pokepedia name mapping",
    )

    # Step 3 — Moves, TMs, tutors from IF wiki
    run(
        ["python", str(SCRIPTS_DIR / "extract_moves_if.py")],
        "Step 3/10 — Extract moves/TMs/tutors from IF wiki",
    )

    # Step 3b — Enrich moves with FR names via PokeAPI
    run(
        ["python", str(SCRIPTS_DIR / "enrich_moves_fr.py")],
        "Step 3b/10 — Enrich moves with FR names (PokeAPI)",
    )

    # Step 4 — Abilities from IF wiki
    run(
        ["python", str(SCRIPTS_DIR / "extract_abilities_if.py")],
        "Step 4/10 — Extract abilities from IF wiki",
    )

    # Step 4b — Enrich abilities with FR names + descriptions via PokeAPI
    run(
        ["python", str(SCRIPTS_DIR / "enrich_abilities_fr.py")],
        "Step 4b/10 — Enrich abilities with FR names + descriptions (PokeAPI)",
    )

    # Step 5 — Wild/static/legendary encounters (replaces extract_locations_if.py)
    run(
        ["python", str(SCRIPTS_DIR / "extract_encounters_if.py")],
        "Step 5/10 — Extract encounters from IF wiki (wild + static + legendary)",
    )

    # Step 6 — Pokepedia moveset scraper (USUL, Gen 7)
    # Scrapes: level_up (USUL column) + tm + breeding + tutor for ALL Pokémon
    run(
        ["scrapy", "crawl", "if_movesets"],
        "Step 6/10 — Scrape Pokepedia movesets (USUL Gen 7 — level/tm/breeding/tutor)",
        cwd=SCRAPER_DIR,
    )

    # Step 7 — Merge base movesets with IF-specific overrides
    run(
        ["python", str(SCRIPTS_DIR / "transform_merge_movesets.py")],
        "Step 7/10 — Merge movesets (base + IF overrides)",
    )

    # Step 8 — Load everything into PostgreSQL
    run(
        ["python", str(SCRIPTS_DIR / "load_db.py")],
        "Step 8/10 — Load all data into PostgreSQL",
    )

    # Step 8b — Fix Pokémon types from PokeAPI (overrides potentially wrong wiki data)
    run(
        ["python", str(SCRIPTS_DIR / "fix_pokemon_types.py")],
        "Step 8b/10 — Fix Pokémon types from PokeAPI",
    )

    # Step 8c — Inherit moves from pre-evolutions (Charizard ← Charmeleon ← Charmander)
    run(
        ["python", str(SCRIPTS_DIR / "enrich_evolution_movesets.py")],
        "Step 8c/10 — Inherit moves from pre-evolutions",
    )

    # Step 8d — Fix national_id (IF dex diverges from national dex after #251)
    run(
        ["python", str(SCRIPTS_DIR / "fix_national_ids.py")],
        "Step 8d — Fix pokemon.national_id via PokeAPI name lookup",
    )

    # Step 8e — Re-sync stats + name_fr + base_experience with corrected national_ids
    run(
        ["python", str(SCRIPTS_DIR / "fix_stats_and_fr_names.py")],
        "Step 8e — Re-sync stats + FR names after national_id correction",
    )

    # Step 8f — Fill TM learnability gaps from PokeAPI
    run(
        ["python", str(SCRIPTS_DIR / "fix_tms_from_pokeapi.py")],
        "Step 8f — Fill TM learners from PokeAPI (idempotent)",
    )

    # Step 9 — Seed types FR + type effectiveness (après load_db pour DO UPDATE name_fr)
    run(
        ["python", str(SCRIPTS_DIR / "seed_type_effectiveness.py")],
        "Step 9/10 — Seed types FR + type effectiveness chart (Gen 7 / IF)",
    )

    # Step 9b — Load encounters (locations + pokemon_location)
    run(
        ["python", str(SCRIPTS_DIR / "load_encounters.py")],
        "Step 9b/10 — Load encounters into location + pokemon_location",
    )

    # Step 9c — Enrich pokemon.pokepedia_url from pokepedia_names.json
    run(
        ["python", str(SCRIPTS_DIR / "enrich_pokemon_fr.py")],
        "Step 9c/10 — Enrich pokemon.pokepedia_url from Pokepedia mapping",
    )

    # Step 9d — Load items (fusion + evolution + valuables) from IF wiki
    run(
        ["python", str(SCRIPTS_DIR / "load_items.py")],
        "Step 9d — Load items (fusion/evolution/valuable) from IF wiki",
    )

    # Step 9e — Load move tutors from IF wiki
    run(
        ["python", str(SCRIPTS_DIR / "load_move_tutors.py")],
        "Step 9e — Load move tutors from IF wiki",
    )

    # Step 9e-bis — Fill tutor learnability gaps from PokeAPI (needs tutors in DB)
    run(
        ["python", str(SCRIPTS_DIR / "fix_tutors_from_pokeapi.py")],
        "Step 9e-bis — Fill tutor learners from PokeAPI (idempotent)",
    )

    # Step 9f — Load TM locations from IF wiki
    run(
        ["python", str(SCRIPTS_DIR / "load_tm_locations.py")],
        "Step 9f — Load TM locations from IF wiki",
    )

    # Step 9g — Load move expert moves (Knot Island + Boon Island) from IF wiki
    run(
        ["python", str(SCRIPTS_DIR / "fix_move_experts.py")],
        "Step 9g — Load move_expert_move from IF wiki",
    )

    # Step 10 — Download & extract fusion sprites from infinitefusion.net
    run(
        ["python", str(SCRIPTS_DIR / "extract_sprites.py")],
        "Step 10/12 — Download spritesheets & extract sprites (infinitefusion.net)",
    )

    # Step 11a — Extract triple fusions from IF wiki
    run(
        ["python", str(SCRIPTS_DIR / "extract_triple_fusions.py")],
        "Step 11a/12 — Extract triple fusions from IF wiki (23 entries)",
    )

    # Step 11b — Load triple fusions (+ components + types + abilities)
    run(
        ["python", str(SCRIPTS_DIR / "load_triple_fusions.py")],
        "Step 11b/12 — Load triple_fusion + components + types + abilities",
    )

    # Step 12 — Load sprite credits (creator + fusion_sprite + fusion_sprite_creator)
    run(
        ["python", str(SCRIPTS_DIR / "load_sprite_credits.py")],
        "Step 12/12 — Load sprite credits from data/sprite_credits.csv",
    )

    print("\n[ETL] Pipeline completed successfully.", flush=True)


if __name__ == "__main__":
    main(force="--force" in sys.argv)
