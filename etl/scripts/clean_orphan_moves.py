"""ETL — Delete truly orphan moves.

A move is orphan if it is referenced nowhere:
  - pokemon_move (no Pokémon learns it)
  - tm           (no associated TM)
  - move_tutor   (no classic tutor)
  - move_expert_move (no Move Expert)

These moves correspond to Gen 7+ attacks that do not exist in IF.
Deleting them lightens the DB and avoids them showing up in filters.

Usage:
    docker compose run --rm etl python -m etl.scripts.clean_orphan_moves
"""

from __future__ import annotations

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging

log = setup_logging("clean_orphan_moves")

ORPHAN_QUERY = """
    SELECT m.id, m.name_en
    FROM move m
    WHERE NOT EXISTS (SELECT 1 FROM pokemon_move pm WHERE pm.move_id = m.id)
      AND NOT EXISTS (SELECT 1 FROM tm t WHERE t.move_id = m.id)
      AND NOT EXISTS (SELECT 1 FROM move_tutor mt WHERE mt.move_id = m.id)
      AND NOT EXISTS (SELECT 1 FROM move_expert_move mem WHERE mem.move_id = m.id)
    ORDER BY m.id
"""


def main() -> None:
    with pg_connection() as conn:
        cur = conn.cursor()

        cur.execute(ORPHAN_QUERY)
        orphans = cur.fetchall()

        if not orphans:
            log.info("No orphan move found.")
            return

        log.info("%d orphan moves detected:", len(orphans))
        for mid, name in orphans:
            log.info("  #%d %s", mid, name)

        ids = [r[0] for r in orphans]
        cur.execute("DELETE FROM move WHERE id = ANY(%s)", (ids,))
        conn.commit()

        log.info("✅ %d moves deleted.", len(ids))


if __name__ == "__main__":
    main()
