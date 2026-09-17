"""Cross-file version alignment that no single Dependabot PR can guarantee.

The Prefect worker is built from etl/uv.lock; the Prefect server runs the
image pinned in docker-compose.yml. They must match, and Dependabot only
bumps one file per PR: this test makes the uv PR fail until the compose tag
is bumped in the same branch (and keeps pre-release tags out).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "etl" / "uv.lock"
COMPOSE = ROOT / "docker-compose.yml"


def _locked(name: str) -> str:
    m = re.search(rf'\[\[package\]\]\nname = "{name}"\nversion = "([^"]+)"', LOCK.read_text())
    assert m, f"{name} absent de etl/uv.lock"
    return m.group(1)


def _compose_image(repo: str) -> str:
    m = re.search(rf"image:\s*{re.escape(repo)}:(\S+)", COMPOSE.read_text())
    assert m, f"image {repo} absente de docker-compose.yml"
    return m.group(1)


@pytest.mark.skipif(not COMPOSE.exists(), reason="docker-compose.yml non monté")
def test_prefect_server_image_matches_etl_lock():
    tag = _compose_image("prefecthq/prefect")
    assert tag == f"{_locked('prefect')}-python3.12", (
        f"docker-compose.yml épingle prefecthq/prefect:{tag} mais etl/uv.lock "
        f"verrouille prefect {_locked('prefect')} - bumper les deux ensemble"
    )
    assert not re.search(r"dev|rc|alpha|beta", tag), f"tag de pré-release : {tag}"
