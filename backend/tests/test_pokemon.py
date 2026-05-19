"""Tests for /pokemon routes."""

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}


def test_list_pagination(client: TestClient) -> None:
    r = client.get("/pokemon/?limit=3")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 3
    assert [p["id"] for p in items] == [1, 2, 3]
    assert items[0]["name_en"] == "Bulbasaur"


def test_list_offset(client: TestClient) -> None:
    r = client.get("/pokemon/?offset=500&limit=5")
    assert r.status_code == 200
    assert [p["id"] for p in r.json()] == [501, 502, 503, 504, 505]


def test_filter_by_type(client: TestClient) -> None:
    # type_id 7 = Fire — Charmander is one of them
    r = client.get("/pokemon/?type_id=7")
    assert r.status_code == 200
    names = {p["name_en"] for p in r.json()}
    assert "Charmander" in names
    assert "Charizard" in names
    assert "Bulbasaur" not in names


def test_filter_by_generation(client: TestClient) -> None:
    r = client.get("/pokemon/?generation_id=1")
    assert r.status_code == 200
    assert len(r.json()) >= 151


def test_filter_include_hoenn_false(client: TestClient) -> None:
    all_count = len(client.get("/pokemon/").json())
    no_hoenn = len(client.get("/pokemon/?include_hoenn=false").json())
    assert no_hoenn < all_count


def test_detail_charizard(client: TestClient) -> None:
    r = client.get("/pokemon/6")
    assert r.status_code == 200
    p = r.json()
    assert p["name_en"] == "Charizard"
    assert p["name_fr"] == "Dracaufeu"
    types = {t["name_en"] for t in p["types"]}
    assert types == {"Fire", "Flying"}
    assert any(a["name_en"] == "Blaze" for a in p["abilities"])


def test_detail_not_found(client: TestClient) -> None:
    r = client.get("/pokemon/9999")
    assert r.status_code == 404
    assert "9999" in r.json()["detail"]


def test_search_accent_insensitive(client: TestClient) -> None:
    r = client.get("/pokemon/search?q=draca")
    assert r.status_code == 200
    names = [p["name_fr"] for p in r.json()]
    assert "Dracaufeu" in names


def test_moves_endpoint(client: TestClient) -> None:
    r = client.get("/pokemon/6/moves")
    assert r.status_code == 200
    moves = r.json()
    assert len(moves) > 0
    methods = {m["method"] for m in moves}
    assert methods & {"level_up", "tm"}


def test_evolutions_endpoint(client: TestClient) -> None:
    # Charmander -> Charmeleon
    r = client.get("/pokemon/4/evolutions")
    assert r.status_code == 200
    data = r.json()
    assert any(e["evolves_into_name_en"] == "Charmeleon" for e in data)


def test_weaknesses_endpoint(client: TestClient) -> None:
    # Charizard: weak to Rock (4x), Electric (2x), Water (2x)
    r = client.get("/pokemon/6/weaknesses")
    assert r.status_code == 200
    data = r.json()
    rock = next((w for w in data if w["attacking_type_name_en"] == "Rock"), None)
    assert rock is not None
    assert float(rock["multiplier"]) == 4.0


def test_locations_endpoint_structure(client: TestClient) -> None:
    r = client.get("/pokemon/1/locations")
    assert r.status_code == 200
    locs = r.json()
    assert isinstance(locs, list)
    # Bulbasaur is a gift in Pallet Town — fixture confirms this
    assert any(loc["method"] == "gift" for loc in locs)
    for loc in locs:
        assert "location_name" in loc
        assert "method" in loc


def test_locations_endpoint_gift_starter(client: TestClient) -> None:
    """Bulbasaur (#1), Charmander (#4), Squirtle (#7) are gift starters in Pallet Town."""
    for pid in [1, 4, 7]:
        r = client.get(f"/pokemon/{pid}/locations")
        assert r.status_code == 200
        locs = r.json()
        gifts = [l for l in locs if l["method"] == "gift"]
        assert gifts, f"Pokemon {pid} should have at least one gift location"


def test_weaknesses_include_immunities(client: TestClient) -> None:
    """Immunities (multiplier=0.0) are included in the weaknesses response.
    Gengar (Ghost/Poison) is immune to Normal and Fighting."""
    r = client.get("/pokemon/94/weaknesses")  # Gengar
    assert r.status_code == 200
    by_type = {w["attacking_type_name_en"]: float(w["multiplier"]) for w in r.json()}
    assert by_type.get("Normal") == 0.0
    assert by_type.get("Fighting") == 0.0


def test_weaknesses_resistances(client: TestClient) -> None:
    """Resistances (multiplier=0.5) are returned alongside weaknesses.
    Charizard (Fire/Flying) resists Bug, Steel, Grass, Fighting, Ground."""
    r = client.get("/pokemon/6/weaknesses")  # Charizard
    assert r.status_code == 200
    by_type = {w["attacking_type_name_en"]: float(w["multiplier"]) for w in r.json()}
    # Fire/Flying resists Bug (0.25x), Steel (0.5x), Grass (0.25x)
    assert by_type.get("Bug") == 0.25
    assert by_type.get("Grass") == 0.25
