"""Shared pytest fixtures.

Tests run against the live dev Postgres (data loaded by the ETL pipeline).
They assume the database is populated with the canonical 572 Pokémon dataset.

Run from the repo root (required — SPRITES_DIR is relative to cwd):
    POSTGRES_PASSWORD=changeme backend/.venv/bin/pytest backend/tests/

POSTGRES_HOST defaults to 'localhost'.
POSTGRES_PORT defaults to the value of FUSIONDEX_DB_PORT from the environment
(set in .env), falling back to 55432, so the custom Docker-exposed port is
picked up automatically without requiring an extra env var at the CLI.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", os.environ.get("FUSIONDEX_DB_PORT", "55432"))

from backend.main import app  # noqa: E402  (env must be set before import)


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)
