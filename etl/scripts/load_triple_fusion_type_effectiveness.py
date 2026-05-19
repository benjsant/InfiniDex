"""
ETL — Seed type_effectiveness rows for the 8 unique IF triple-fusion types.

These custom types are not derived mathematically from their component type
names — they have hand-defined effectiveness profiles published on the IF wiki:
https://infinitefusion.fandom.com/wiki/Triple_Fusions

Each entry in CUSTOM_TYPE_EFFECTIVENESS maps:
  custom_type_name_en → { attacking_standard_type_name_en: multiplier, ... }

Only non-x1 entries need to be listed (the service treats missing entries as x1).
Derived by cross-referencing wiki <abbr title="..."> attributes with standard
type chart values for any secondary standard type.

Idempotence: uses ON CONFLICT DO UPDATE.
"""

from __future__ import annotations
from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging
from etl.utils.sql import load_id_map

LOGGER = setup_logging(__name__)

# attacking_type_name_en → multiplier
CUSTOM_TYPE_EFFECTIVENESS: dict[str, dict[str, float]] = {

    # Zapmolcuno has [Ice/Fire/Electric]/Flying.
    # Derived by dividing Zapmolcuno combined by Flying individual effectiveness,
    # then cross-validated with Zekyushiram (Dragon/[Ice/Fire/Electric]).
    "Ice/Fire/Electric": {
        "Ground":   2.0,
        "Water":    2.0,
        "Fighting": 2.0,
        "Flying":   0.5,
        "Bug":      0.5,
        "Steel":    0.5,
        "Fire":     0.5,
        "Grass":    0.5,
        "Electric": 0.5,
        "Ice":      0.5,
        "Fairy":    0.5,
    },

    # Enraicune is solo Fire/Water/Electric — values taken directly from wiki.
    "Fire/Water/Electric": {
        "Ground":   2.0,
        "Rock":     2.0,
        "Bug":      0.5,
        "Ice":      0.5,
        "Fairy":    0.5,
        "Steel":    0.5,
        "Fire":     0.5,
        "Flying":   0.5,
    },

    # Kyodonquaza is solo Water/Ground/Flying — values taken directly from wiki
    # (custom-type attackers like [Ice/Fire/Electric] are excluded).
    "Water/Ground/Flying": {
        "Grass":    2.0,
        "Ice":      2.0,
        "Electric": 0.0,
        "Ground":   0.0,
        "Steel":    0.5,
        "Fire":     0.5,
        "Poison":   0.5,
        "Fighting": 0.5,
        "Bug":      0.5,
    },

    # Paldiatina is Dragon/[Ghost/Steel/Water].
    # Derived by dividing combined by Dragon individual effectiveness.
    "Ghost/Steel/Water": {
        "Ground":   2.0,
        "Electric": 2.0,
        "Normal":   0.0,
        "Fighting": 0.0,
        "Poison":   0.0,
        "Flying":   0.5,
        "Rock":     0.5,
        "Bug":      0.5,
        "Psychic":  0.5,
        "Water":    0.5,
        "Steel":    0.5,
        "Ice":      0.5,
        "Dragon":   0.5,
        "Fairy":    0.5,
    },

    # Deosectwo is solo Bug/Steel/Psychic — wiki values directly.
    "Bug/Steel/Psychic": {
        "Fire":     2.0,
        "Poison":   0.0,
        "Psychic":  0.5,
        "Normal":   0.5,
        "Steel":    0.5,
        "Grass":    0.5,
        "Ice":      0.5,
        "Dragon":   0.5,
        "Fairy":    0.5,
        "Fighting": 0.5,
    },

    # Regiregi is solo Ice/Rock/Steel — wiki values directly.
    "Ice/Rock/Steel": {
        "Ground":   2.0,
        "Fire":     2.0,
        "Water":    2.0,
        "Rock":     2.0,
        "Poison":   0.0,
        "Psychic":  0.5,
        "Normal":   0.5,
        "Grass":    0.5,
        "Ice":      0.5,
        "Dragon":   0.5,
        "Fairy":    0.5,
    },

    # Celemewchi is Psychic/[Grass/Steel].
    # Derived by dividing combined by Psychic individual effectiveness.
    "Grass/Steel": {
        "Fire":     2.0,
        "Fighting": 2.0,
        "Poison":   0.0,
        "Normal":   0.5,
        "Rock":     0.5,
        "Steel":    0.5,
        "Water":    0.5,
        "Grass":    0.5,
        "Electric": 0.5,
        "Dragon":   0.5,
        "Fairy":    0.5,
        "Psychic":  0.5,
        "Ghost":    0.5,
        "Dark":     0.5,
    },

    # All starter triple fusions share Fire/Water/Grass — wiki values directly.
    "Fire/Water/Grass": {
        "Rock":     2.0,
        "Flying":   2.0,
        "Poison":   2.0,
        "Fire":     0.5,
        "Ice":      0.5,
        "Fairy":    0.5,
        "Steel":    0.5,
        "Water":    0.5,
        "Grass":    0.5,
    },
}


def main() -> None:
    LOGGER.info("Connecting to PostgreSQL…")
    with pg_connection() as conn:
        type_by_name = load_id_map(conn, "type", lower=False)

        inserted = 0
        skipped = 0

        with conn.cursor() as cur:
            for custom_type_name, effectiveness in CUSTOM_TYPE_EFFECTIVENESS.items():
                defending_id = type_by_name.get(custom_type_name)
                if defending_id is None:
                    LOGGER.warning("Custom type not found in DB: %r", custom_type_name)
                    skipped += 1
                    continue

                for atk_name, mult in effectiveness.items():
                    attacking_id = type_by_name.get(atk_name)
                    if attacking_id is None:
                        LOGGER.warning("Attacking type not found: %r", atk_name)
                        skipped += 1
                        continue

                    cur.execute(
                        """INSERT INTO type_effectiveness (attacking_type_id, defending_type_id, multiplier)
                           VALUES (%s, %s, %s)
                           ON CONFLICT (attacking_type_id, defending_type_id)
                           DO UPDATE SET multiplier = EXCLUDED.multiplier""",
                        (attacking_id, defending_id, mult),
                    )
                    inserted += 1

            conn.commit()

        LOGGER.info("Done: %d rows upserted, %d skipped", inserted, skipped)


if __name__ == "__main__":
    main()
