"""
InfiniDex ETL pipeline orchestrator.

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
  8c.  enrich_evolution_movesets — inherit moves from pre-evolutions
  8d.  fix_national_ids         — fix national_id (IF dex diverges from national after #251)
  8e.  fix_stats_and_fr_names   — re-sync stats + name_fr with corrected national_ids
  8e-ter. fix_evolutions        — re-fetch evolution chains with corrected national_ids
  8e-quater. fix_form_pokemon   — stats/name_fr/abilities of alt forms via PokeAPI form slugs
  8f.  fix_tms_from_pokeapi     — fill TM learnability gaps from PokeAPI
  9.   seed_type_effectiveness  — 18×18 type chart with FR names from table_type.csv
  9b.  load_encounters          — load locations + pokemon_location from encounters_if.json
  9b-bis. fix_pokemon_locations — correct legendary/gift/trade locations from IF wiki
  9b-ter. load_pokedex_locations — wild/quest locations from IF Pokédex wiki page
  9b-quater. load_locations_snapshot — replay pre-restructure snapshot (gap-fill)
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
  python etl/pipeline.py                 # skip if data already loaded
  python etl/pipeline.py --force         # force full re-run
  python etl/pipeline.py --from 9b-bis   # resume from a step (bypasses the
                                         # already-loaded short-circuit)
  python etl/pipeline.py --list          # list step names + labels and exit
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple, Sequence

from etl.utils.db import _require_password

BASE_DIR    = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "scripts"
SCRAPER_DIR = BASE_DIR / "pokepedia_scraper"


class Step(NamedTuple):
    """One ordered pipeline step. `name` is the stable id used by --from/--list."""
    name:  str
    label: str
    cmd:   list[str]
    cwd:   Path | None = None


def _py(script: str) -> list[str]:
    return ["python", str(SCRIPTS_DIR / script)]


# Strict ordered DAG — encoded as a sequence. Order is load-bearing
# (later steps depend on earlier ones); do not reorder.
STEPS: list[Step] = [
    Step("1",      "Step 1/8 — Extract Pokédex from IF wiki",
         _py("extract_pokedex_if.py")),
    Step("2a",     "Step 2a/8 — Enrich via PokeAPI (stats, FR names, evolutions)",
         _py("extract_stats_pokeapi.py")),
    Step("2b",     "Step 2b/8 — Build Pokepedia name mapping",
         _py("extract_pokepedia_names.py")),
    Step("3",      "Step 3/10 — Extract moves/TMs/tutors from IF wiki",
         _py("extract_moves_if.py")),
    Step("3b",     "Step 3b/10 — Enrich moves with FR names (PokeAPI)",
         _py("enrich_moves_fr.py")),
    Step("4",      "Step 4/10 — Extract abilities from IF wiki",
         _py("extract_abilities_if.py")),
    Step("4b",     "Step 4b/10 — Enrich abilities with FR names + descriptions (PokeAPI)",
         _py("enrich_abilities_fr.py")),
    Step("5",      "Step 5/10 — Extract encounters from IF wiki (wild + static + legendary)",
         _py("extract_encounters_if.py")),
    Step("6",      "Step 6/10 — Scrape Pokepedia movesets (USUL Gen 7 — level/tm/breeding/tutor)",
         ["scrapy", "crawl", "if_movesets"], SCRAPER_DIR),
    Step("7",      "Step 7/10 — Merge movesets (base + IF overrides)",
         _py("transform_merge_movesets.py")),
    Step("8",      "Step 8/10 — Load all data into PostgreSQL",
         _py("load_db.py")),
    Step("8c",     "Step 8c/10 — Inherit moves from pre-evolutions",
         _py("enrich_evolution_movesets.py")),
    Step("8d",     "Step 8d — Fix pokemon.national_id via PokeAPI name lookup",
         _py("fix_national_ids.py")),
    Step("8e",     "Step 8e — Re-sync stats + FR names after national_id correction",
         _py("fix_stats_and_fr_names.py")),
    Step("8e-bis", "Step 8e-bis — Re-sync types after national_id correction",
         _py("fix_pokemon_types.py")),
    Step("8e-ter", "Step 8e-ter — Re-fetch evolution chains after national_id correction",
         _py("fix_evolutions.py")),
    Step("8e-quater", "Step 8e-quater — Fix alt-form Pokémon (stats, name_fr, abilities) via form slugs",
         _py("fix_form_pokemon.py")),
    Step("8f",     "Step 8f — Fill TM learners from PokeAPI (idempotent)",
         _py("fix_tms_from_pokeapi.py")),
    Step("9",      "Step 9/10 — Seed types FR + type effectiveness chart (Gen 7 / IF)",
         _py("seed_type_effectiveness.py")),
    Step("9b",     "Step 9b/10 — Load encounters into location + pokemon_location",
         _py("load_encounters.py")),
    Step("9b-bis", "Step 9b-bis — Fix legendary/gift/trade Pokémon locations (wiki-sourced)",
         _py("fix_pokemon_locations.py")),
    Step("9b-ter", "Step 9b-ter — Load wild/quest encounter locations from IF Pokédex wiki",
         _py("load_pokedex_locations.py")),
    Step("9b-quater", "Step 9b-quater — Replay pre-restructure pokemon_location snapshot (gap-fill)",
         _py("load_locations_snapshot.py")),
    Step("9c",     "Step 9c/10 — Enrich pokemon.pokepedia_url from Pokepedia mapping",
         _py("enrich_pokemon_fr.py")),
    Step("9d",     "Step 9d — Load items (fusion/evolution/valuable) from IF wiki",
         _py("load_items.py")),
    Step("9d-bis", "Step 9d-bis — Extract item locations from IF wiki",
         _py("extract_item_locations.py")),
    Step("9e",     "Step 9e — Load move tutors from IF wiki",
         _py("load_move_tutors.py")),
    Step("9e-bis", "Step 9e-bis — Fill tutor learners from PokeAPI (idempotent)",
         _py("fix_tutors_from_pokeapi.py")),
    Step("9f",     "Step 9f — Load TM locations from IF wiki",
         _py("load_tm_locations.py")),
    Step("9g",     "Step 9g — Load move_expert_move from IF wiki",
         _py("fix_move_experts.py")),
    Step("10",     "Step 10/12 — Download spritesheets & extract sprites (infinitefusion.net)",
         _py("extract_sprites.py")),
    Step("11a",    "Step 11a/12 — Extract triple fusions from IF wiki (23 entries)",
         _py("extract_triple_fusions.py")),
    Step("11b",    "Step 11b/12 — Load triple_fusion + components + types + abilities",
         _py("load_triple_fusions.py")),
    Step("11c",    "Step 11c/12 — Seed type_effectiveness for custom IF triple-fusion types",
         _py("load_triple_fusion_type_effectiveness.py")),
    Step("12",     "Step 12/12 — Load sprite credits from data/sprite_credits.csv",
         _py("load_sprite_credits.py")),
    Step("13",     "Step 13 — Clean orphan moves (no pokemon_move/tm/tutor/expert reference)",
         _py("clean_orphan_moves.py")),
    Step("14",     "Step 14 — Enrich missing abilities via PokeAPI",
         _py("enrich_missing_abilities.py")),
    Step("audit",  "Step 15 — Data consistency audit (gate: fails on blocking issues)",
         _py("audit_db.py")),
]


def run(cmd: Sequence[str], label: str, cwd: Path | None = None) -> None:
    print(f"\n▶ {label}", flush=True)
    result = subprocess.run(cmd, shell=False, check=False, cwd=cwd)
    if result.returncode != 0:
        print(f"[FAIL] {label} (returncode={result.returncode})", flush=True)
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
    # Resolve the password before the try block so a missing POSTGRES_PASSWORD
    # raises the clear RuntimeError (consistent with etl/utils/db.py) instead
    # of being swallowed by the broad except below.
    pwd = _require_password()
    try:
        import psycopg2  # noqa: PLC0415

        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "db"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            dbname=os.getenv("POSTGRES_DB", "infinidex_db"),
            user=os.getenv("POSTGRES_USER", "infinidex_user"),
            password=pwd,
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
    except psycopg2.OperationalError as e:
        print(f"[ETL] Cannot connect to DB: {e}", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"[ETL] check_already_loaded unexpected error: {e}", flush=True)
        return False


def main(argv: Sequence[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    force = "--force" in argv

    if "--list" in argv:
        for s in STEPS:
            print(f"  {s.name:<8} {s.label}")
        return

    from_step: str | None = None
    if "--from" in argv:
        i = argv.index("--from")
        if i + 1 >= len(argv):
            print("[ETL] --from requires a step name (see --list).", flush=True)
            sys.exit(2)
        from_step = argv[i + 1]
        names = [s.name for s in STEPS]
        if from_step not in names:
            print(f"[ETL] Unknown step '{from_step}'. Valid: {', '.join(names)}", flush=True)
            sys.exit(2)

    # --from is an explicit resume → bypass the already-loaded short-circuit.
    # Otherwise preserve original behaviour: always probe the DB (so a
    # DB-down condition still exits non-zero) then skip unless --force.
    if from_step is None:
        loaded = check_already_loaded()
        if loaded and not force:
            print("[ETL] Data already loaded. Skipping "
                  "(use --force to rerun, or --from <step> to resume).")
            return

    print("[ETL] Starting InfiniDex pipeline...", flush=True)
    started = from_step is None
    for s in STEPS:
        if not started:
            if s.name == from_step:
                started = True
            else:
                print(f"[ETL] ⏭  skip {s.name} ({s.label})", flush=True)
                continue
        run(s.cmd, s.label, s.cwd)

    print("\n[ETL] Pipeline completed successfully.", flush=True)
    print(
        "[ETL] Reminder: the backend warms _pokemon_cache/_fusion_cache at "
        "startup. Recreate it so it reloads from the rebuilt DB, otherwise "
        "it silently serves stale data:\n"
        "      docker compose up backend -d --force-recreate",
        flush=True,
    )


if __name__ == "__main__":
    main()
