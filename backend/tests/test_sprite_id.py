"""Contract of Pokemon.sprite_id — the PokeAPI id used for the base sprite.

Regression: forms without a national_id used to fall back to their IF id on
the frontend, and PokeAPI served ANOTHER species (IF #431 Oricorio Pom-Pom
rendered as Glameow). The API must never hand out the IF id as a sprite id.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.db.models import Pokemon


def test_form_id_wins_over_national_id():
    p = Pokemon(id=578, national_id=None, pokeapi_form_id=10019)
    assert p.sprite_id == 10019


def test_base_form_uses_national_id():
    p = Pokemon(id=25, national_id=25, pokeapi_form_id=None)
    assert p.sprite_id == 25


def test_never_falls_back_to_the_if_id():
    p = Pokemon(id=431, national_id=None, pokeapi_form_id=None)
    assert p.sprite_id is None


def test_list_exposes_sprite_id_and_never_the_if_id(client: TestClient) -> None:
    r = client.get("/pokemon/?limit=600")
    assert r.status_code == 200
    for p in r.json():
        assert "sprite_id" in p
        if p["national_id"] is None:
            # No national id: either a form id (10xxx / shared species id) or
            # nothing — but never the IF id, unless it coincides by design.
            assert p["sprite_id"] is None or p["sprite_id"] != p["id"]
