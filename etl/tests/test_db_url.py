"""The ETL engine must name its driver: SQLAlchemy 2.1 maps a bare
`postgresql://` to psycopg (v3), which is not installed. The ETL CI never
touches a database, so without this test a SQLAlchemy bump goes green there
and breaks the pipeline at runtime.
"""

from __future__ import annotations

from etl.utils.db import get_engine


def test_engine_uses_installed_psycopg2_driver(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "x")
    engine = get_engine()  # create_engine ne se connecte pas
    try:
        assert engine.dialect.driver == "psycopg2"
    finally:
        engine.dispose()
