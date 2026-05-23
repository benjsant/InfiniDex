"""Block execution until PostgreSQL is ready to accept connections."""

import os
import sys
import time

import psycopg2
from psycopg2 import OperationalError

DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "infinidex_db")
DB_USER = os.getenv("POSTGRES_USER", "infinidex_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "infinidex_password")

MAX_RETRIES = 30
RETRY_INTERVAL = 2


def wait_for_db() -> bool:
    print(f"[WAIT] Waiting for PostgreSQL at {DB_HOST}:{DB_PORT}...", flush=True)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                connect_timeout=3,
            )
            conn.close()
            print(f"[OK] PostgreSQL ready (attempt {attempt}/{MAX_RETRIES})", flush=True)
            return True
        except OperationalError as e:
            print(f"[WAIT] {attempt}/{MAX_RETRIES}: not ready ({e})", flush=True)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_INTERVAL)

    print("[ERROR] PostgreSQL unreachable after all retries", flush=True)
    return False


if __name__ == "__main__":
    sys.exit(0 if wait_for_db() else 1)
