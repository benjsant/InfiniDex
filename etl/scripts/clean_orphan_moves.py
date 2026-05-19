"""ETL — Suppression des moves vraiment orphelins.

Un move est orphelin s'il n'est référencé nulle part :
  - pokemon_move (aucun Pokémon ne l'apprend)
  - tm           (pas de CT associée)
  - move_tutor   (pas de tuteur classique)
  - move_expert_move (pas de Move Expert)

Ces moves correspondent à des attaques Gen 7+ qui n'existent pas dans IF.
Les supprimer allège la DB et évite qu'ils apparaissent dans des filtres.

Usage :
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
            log.info("Aucun move orphelin trouvé.")
            return

        log.info("%d moves orphelins détectés :", len(orphans))
        for mid, name in orphans:
            log.info("  #%d %s", mid, name)

        ids = [r[0] for r in orphans]
        cur.execute("DELETE FROM move WHERE id = ANY(%s)", (ids,))
        conn.commit()

        log.info("✅ %d moves supprimés.", len(ids))


if __name__ == "__main__":
    main()
