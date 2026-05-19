"""Shared pytest fixtures.

Two modes:
  - DB-free (CI smoke job): only test_ai.py + test_llm_providers.py
  - Full  (CI full job + local dev): all tests against PostgreSQL populated
    with backend/tests/fixtures/{schema,data,sprites_sample}.sql

Local run (from repo root):
    POSTGRES_PASSWORD=changeme backend/.venv/bin/pytest backend/tests/

Via Docker Compose (uses dev DB):
    docker compose --profile test run --rm test-backend

POSTGRES_HOST  defaults to 'localhost'.
POSTGRES_PORT  defaults to FUSIONDEX_DB_PORT env var, fallback 55432.
SPRITES_DIR    defaults to 'data/sprites'; set to 'tests/fixtures/sprites'
               in CI to serve the minimal test PNG without the full dataset.
FUSIONDEX_TEST_DOCKER=1  set by the test-backend Compose service to allow
               connecting to the internal 'db' hostname.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", os.environ.get("FUSIONDEX_DB_PORT", "55432"))
# session.py now requires POSTGRES_PASSWORD at import (no insecure default).
# The DB-free smoke job never connects, so a dummy lets import/collection
# succeed; CI full job and local runs inject the real value (no-op here).
os.environ.setdefault("POSTGRES_PASSWORD", "changeme")

_host = os.environ["POSTGRES_HOST"]
_docker_mode = os.environ.get("FUSIONDEX_TEST_DOCKER") == "1"
if not _docker_mode and _host not in ("localhost", "127.0.0.1"):
    raise RuntimeError(
        f"Tests must run against a local DB (got POSTGRES_HOST={_host!r}). "
        "Use the test Docker container (docker compose --profile test run --rm test-backend) "
        "or set POSTGRES_HOST=localhost."
    )

from backend.main import app  # noqa: E402  (env must be set before import)


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)
