"""Idempotent schema migrations applied by the ETL container on every start.

The project has no migration tool: `docker/init_postgres.sql` only runs on a
fresh volume, so a column added there never reaches an existing database.
`pipeline.py` calls `ensure_schema()` before anything else — including when the
data is already loaded and the run is skipped — and the backend service waits
for the ETL container to complete (docker-compose `service_completed_successfully`).
An existing DB is therefore migrated before the backend queries the new column.

Every statement MUST be idempotent (`IF NOT EXISTS`). Append, never edit.
"""

from __future__ import annotations

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

MIGRATIONS: list[tuple[str, str]] = [
    (
        "2026-09 pokemon.pokeapi_form_id (sprite of alternate forms)",
        "ALTER TABLE pokemon ADD COLUMN IF NOT EXISTS pokeapi_form_id INTEGER",
    ),
]


def ensure_schema() -> None:
    with pg_connection() as conn:
        with conn.cursor() as cur:
            for label, sql in MIGRATIONS:
                cur.execute(sql)
                LOGGER.info("Schema OK — %s", label)
        conn.commit()


if __name__ == "__main__":
    ensure_schema()
