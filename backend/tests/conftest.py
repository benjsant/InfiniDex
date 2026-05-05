"""Shared pytest fixtures.

Two modes:
  - DB-free (CI smoke job): only test_ai.py + test_llm_providers.py
  - Full  (CI full job + local dev): all tests against PostgreSQL populated
    with backend/tests/fixtures/{schema,data,sprites_sample}.sql

Local run (from repo root):
    POSTGRES_PASSWORD=changeme backend/.venv/bin/pytest backend/tests/

POSTGRES_HOST  defaults to 'localhost'.
POSTGRES_PORT  defaults to FUSIONDEX_DB_PORT env var, fallback 55432.
SPRITES_DIR    defaults to 'data/sprites'; set to 'tests/fixtures/sprites'
               in CI to serve the minimal test PNG without the full dataset.
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
