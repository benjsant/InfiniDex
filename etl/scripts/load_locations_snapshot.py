"""
ETL — Load the committed pokemon_location snapshot as a gap-filling fallback.

The 2026-07 wiki restructure reset most Location fields of the Pokédex page to
"TBA": load_pokedex_locations.py now recovers ~7 tuples where it used to
recover ~2 448. This script replays a snapshot of the pre-restructure
pokemon_location table (etl/data/snapshots/pokemon_location_snapshot.json,
dumped 2026-07-13) so a full rebuild does not lose that coverage.

Runs AFTER load_encounters.py / fix_pokemon_locations.py /
load_pokedex_locations.py and uses ON CONFLICT DO NOTHING everywhere — live
wiki data always wins, the snapshot only fills the gaps it left.
"""

from __future__ import annotations

import json
from pathlib import Path

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

SNAPSHOT = Path(__file__).resolve().parent.parent / "data" / "snapshots" / "pokemon_location_snapshot.json"


def load_snapshot() -> list[dict]:
    if not SNAPSHOT.exists():
        raise FileNotFoundError(
            f"{SNAPSHOT} not found — the committed snapshot should ship with the repo."
        )
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    entries = data.get("entries") or []
    if not entries:
        raise RuntimeError(f"{SNAPSHOT} holds 0 entries — refusing to silently load nothing.")
    LOGGER.info("Snapshot %s: %d entries (dumped %s)", SNAPSHOT.name, len(entries), data.get("snapshot_date"))
    return entries


def load_locations_snapshot(conn) -> None:
    cur = conn.cursor()

    cur.execute("SELECT id FROM pokemon")
    valid_ids: set[int] = {row[0] for row in cur.fetchall()}

    entries = load_snapshot()

    # ── Ensure every location exists ──────────────────────────────────────────
    for loc_name in sorted({e["location"] for e in entries}):
        cur.execute(
            "INSERT INTO location (name_en) VALUES (%s) ON CONFLICT (name_en) DO NOTHING",
            (loc_name,),
        )

    cur.execute("SELECT id, name_en FROM location")
    loc_id_map: dict[str, int] = {name: lid for lid, name in cur.fetchall()}

    # ── Insert pokemon_location rows (gap-fill only) ──────────────────────────
    inserted = skipped_poke = skipped_conflict = 0

    for e in entries:
        if e["pokemon_id"] not in valid_ids:
            skipped_poke += 1
            continue
        cur.execute(
            """INSERT INTO pokemon_location (pokemon_id, location_id, method, notes)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (pokemon_id, location_id, method) DO NOTHING""",
            (e["pokemon_id"], loc_id_map[e["location"]], e["method"], e["notes"]),
        )
        if cur.rowcount:
            inserted += 1
        else:
            skipped_conflict += 1

    conn.commit()
    LOGGER.info(
        "Done — %d inserted from snapshot | %d already present | %d unknown pokemon",
        inserted, skipped_conflict, skipped_poke,
    )


def main() -> None:
    with pg_connection() as conn:
        load_locations_snapshot(conn)


if __name__ == "__main__":
    main()
