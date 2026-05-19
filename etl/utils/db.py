"""Database connection utilities shared across ETL scripts."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _require_password() -> str:
    """Return POSTGRES_PASSWORD or raise — no insecure default fallback."""
    pwd = os.getenv("POSTGRES_PASSWORD")
    if not pwd:
        raise RuntimeError(
            "Missing required environment variable(s): POSTGRES_PASSWORD. "
            "Set them in your .env file or Docker environment."
        )
    return pwd


def get_pg_connection():
    """Raw psycopg2 connection — for bulk inserts."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "db"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "fusiondex_db"),
        user=os.getenv("POSTGRES_USER", "fusiondex_user"),
        password=_require_password(),
    )


@contextmanager
def pg_connection() -> Iterator[psycopg2.extensions.connection]:
    """Context manager around get_pg_connection.

    Automatically rolls back on exception and always closes the connection.

        with pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
            conn.commit()
    """
    conn = get_pg_connection()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_engine():
    url = (
        f"postgresql://{os.getenv('POSTGRES_USER', 'fusiondex_user')}"
        f":{_require_password()}"
        f"@{os.getenv('POSTGRES_HOST', 'db')}"
        f":{os.getenv('POSTGRES_PORT', '5432')}"
        f"/{os.getenv('POSTGRES_DB', 'fusiondex_db')}"
    )
    return create_engine(url)


def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
