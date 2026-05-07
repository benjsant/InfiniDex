"""Tests for /fusion routes."""

from fastapi.testclient import TestClient


def test_fusion_bulba_charmander(client: TestClient) -> None:
    r = client.get("/fusion/1/4")
    assert r.status_code == 200
    f = r.json()
    assert f["head_name_en"] == "Bulbasaur"
    assert f["body_name_en"] == "Charmander"
    assert f["type1"]["name_en"] == "Grass"
    assert f["type2"]["name_en"] == "Fire"
    assert f["sprite_path"] == "1.4.png"
    # Physical: body*2/3 + head*1/3 — Charmander HP=39, Bulbasaur HP=45
    # floor(39*2/3 + 45/3) = floor(26 + 15) = 41
    assert f["hp"] == 41


def test_fusion_not_found(client: TestClient) -> None:
    r = client.get("/fusion/999/1")  # 999 is within valid range but not in IF
    assert r.status_code == 404


def test_fusion_same_type_drops_type2(client: TestClient) -> None:
    # Pikachu (Electric mono) × Pikachu → mono Electric fusion → type2 dropped
    r = client.get("/fusion/25/25")
    assert r.status_code == 200
    body = r.json()
    assert body["type1"]["name_en"] == "Electric"
    assert body["type2"] is None


def test_fusion_body_secondary_type(client: TestClient) -> None:
    # Canonical IF rule: body's secondary type wins over body's primary.
    # Bulbasaur (Grass/Poison) head × Charizard (Fire/Flying) body → Grass/Flying
    r = client.get("/fusion/1/6")
    assert r.status_code == 200
    body = r.json()
    assert body["type1"]["name_en"] == "Grass"
    assert body["type2"]["name_en"] == "Flying"


def test_fusion_normal_flying_head_shifts_to_flying(client: TestClient) -> None:
    # Special IF rule: a pure Normal/Flying head (e.g. Pidgey #16) uses
    # Flying as type1. Pidgey × Bulbasaur → Flying/Poison.
    r = client.get("/fusion/16/1")
    assert r.status_code == 200
    body = r.json()
    assert body["type1"]["name_en"] == "Flying"
    assert body["type2"]["name_en"] == "Poison"


def test_fusion_moves_origin_split(client: TestClient) -> None:
    r = client.get("/fusion/1/4/moves")
    assert r.status_code == 200
    moves = r.json()
    origins = {m["origin"] for m in moves}
    assert origins <= {"head", "body", "both"}
    assert "head" in origins and "body" in origins


def test_fusion_moves_deduped(client: TestClient) -> None:
    r = client.get("/fusion/1/4/moves")
    move_ids = [m["move_id"] for m in r.json()]
    assert len(move_ids) == len(set(move_ids)), "moves must be deduped by move_id"


def test_fusion_abilities_combine(client: TestClient) -> None:
    r = client.get("/fusion/1/4/abilities")
    assert r.status_code == 200
    names = {a["name_en"] for a in r.json()}
    # Head=Bulbasaur → Overgrow, Body=Charmander → Blaze
    assert "Overgrow" in names
    assert "Blaze" in names
    # Both have hidden abilities
    assert any(a["is_hidden"] for a in r.json())


def test_fusion_weaknesses(client: TestClient) -> None:
    # Grass/Fire fusion
    r = client.get("/fusion/1/4/weaknesses")
    assert r.status_code == 200
    data = {w["attacking_type_name_en"]: float(w["multiplier"]) for w in r.json()}
    # Grass/Fire is 2x weak to Flying, Poison, Rock, Ground
    assert data.get("Flying") == 2.0


def test_fusion_random(client: TestClient) -> None:
    r = client.get("/fusion/random")
    assert r.status_code == 200
    f = r.json()
    assert "head_name_en" in f and "body_name_en" in f
    assert "sprite_path" in f


def test_fusion_self(client: TestClient) -> None:
    """Self-fusion (head_id == body_id) is valid in Infinite Fusion."""
    r = client.get("/fusion/25/25")  # Pikachu × Pikachu
    assert r.status_code == 200
    f = r.json()
    assert f["head_name_en"] == "Pikachu"
    assert f["body_name_en"] == "Pikachu"
    # Self-fusion with mono-type → type2 is null
    assert f["type2"] is None
    # Stats are well-defined
    assert f["hp"] > 0


def test_fusion_weaknesses_include_immunities(client: TestClient) -> None:
    """Immunities (multiplier=0.0) appear in fusion weaknesses.
    Ghost/Poison fusion is immune to Normal and Fighting."""
    # Gengar (94) head × Bulbasaur (1) body → Ghost/Poison
    r = client.get("/fusion/94/1/weaknesses")
    assert r.status_code == 200
    by_type = {w["attacking_type_name_en"]: float(w["multiplier"]) for w in r.json()}
    assert by_type.get("Normal") == 0.0
    assert by_type.get("Fighting") == 0.0


def test_fusion_expert_moves_heart_scale_prices(client: TestClient) -> None:
    """Expert moves expose Heart Scale prices per location (Knot=2, Boon=10)."""
    # Umbreon (197) × Bulbasaur (1) — docs example, qualifies for several rules
    r = client.get("/fusion/197/1/expert-moves")
    assert r.status_code == 200
    moves = r.json()
    assert len(moves) > 0
    for m in moves:
        assert m["prices_heart_scales"]
        for loc, price in m["prices_heart_scales"].items():
            assert loc in ("knot_island", "boon_island")
            assert price == (2 if loc == "knot_island" else 10)
        # Keys of prices_heart_scales must match locations list
        assert set(m["prices_heart_scales"].keys()) == set(m["locations"])
