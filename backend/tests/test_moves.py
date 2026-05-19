"""Tests for /moves and /types routes."""

from fastapi.testclient import TestClient


def test_list_moves(client: TestClient) -> None:
    r = client.get("/moves/?limit=5")
    assert r.status_code == 200
    assert len(r.json()) == 5


def test_filter_category(client: TestClient) -> None:
    r = client.get("/moves/?category=Status&limit=100")
    assert r.status_code == 200
    assert all(m["category"] == "Status" for m in r.json())


def test_filter_power_min(client: TestClient) -> None:
    r = client.get("/moves/?power_min=100&limit=20")
    assert r.status_code == 200
    assert all((m["power"] or 0) >= 100 for m in r.json())


def test_filter_power_range(client: TestClient) -> None:
    r = client.get("/moves/?power_min=60&power_max=80")
    assert r.status_code == 200
    for m in r.json():
        assert 60 <= (m["power"] or 0) <= 80


def test_filter_type_id(client: TestClient) -> None:
    # type_id 7 = Fire
    r = client.get("/moves/?type_id=7&limit=10")
    assert r.status_code == 200
    assert all(m["type"]["name_en"] == "Fire" for m in r.json())


def test_search_move(client: TestClient) -> None:
    r = client.get("/moves/search?q=flamm")
    assert r.status_code == 200
    names = {m["name_fr"] for m in r.json()}
    assert any("Flamm" in n for n in names if n)


def test_by_type_fr(client: TestClient) -> None:
    r = client.get("/moves/by-type/Feu")
    assert r.status_code == 200
    assert len(r.json()) > 0


def test_move_detail_404(client: TestClient) -> None:
    r = client.get("/moves/999999")
    assert r.status_code == 404


def test_move_tutors_bug_bite(client: TestClient) -> None:
    """Bug Bite (move #2) is taught on Route 2 for ₽2000."""
    r = client.get("/moves/2/tutors")
    assert r.status_code == 200
    tutors = r.json()
    assert len(tutors) == 1
    assert tutors[0]["location_name_en"] == "Route 2"
    assert tutors[0]["currency"] == "pokedollars"
    assert tutors[0]["price"] == 2000
    assert "bug catcher" in tutors[0]["npc_description"].lower()


def test_move_tutors_empty(client: TestClient) -> None:
    """A move with no tutor returns an empty list (not 404)."""
    r = client.get("/moves/1/tutors")  # move #1 = Pound, no tutor
    assert r.status_code == 200
    assert r.json() == []


def test_move_detail_tm_info(client: TestClient) -> None:
    """TM05 is Roar, taught at Celadon Dept. Store + Route 32."""
    # Resolve TM05 move via search instead of a raw psycopg2 connection.
    r = client.get("/moves/search?q=Roar")
    assert r.status_code == 200
    moves = r.json()
    roar = next((m for m in moves if m["name_en"] == "Roar"), None)
    assert roar is not None, "Roar not found via search"

    r = client.get(f"/moves/{roar['id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["tm"] is not None
    assert data["tm"]["number"] == 5
    assert len(data["tm"]["locations"]) >= 2
    names = {loc["location_name_en"] for loc in data["tm"]["locations"]}
    assert "Celadon City" in names
    assert "Route 32" in names


def test_move_detail_tm_none_for_non_tm(client: TestClient) -> None:
    """A move that is NOT a TM has tm=null."""
    r = client.get("/moves/1")
    assert r.status_code == 200
    assert r.json()["tm"] is None


def test_move_tutors_quest(client: TestClient) -> None:
    """Quest-based tutors have NULL price and currency='quest'."""
    # Find any tutor with currency='quest' — 5 exist total
    # Soft-Boiled is taught free after a quest in Celadon City
    # Use a direct lookup: moves with Soft-Boiled name
    r = client.get("/moves/search?q=Soft-Boiled")
    assert r.status_code == 200
    moves = r.json()
    assert len(moves) >= 1
    r2 = client.get(f"/moves/{moves[0]['id']}/tutors")
    assert r2.status_code == 200
    tutors = r2.json()
    assert any(t["currency"] == "quest" and t["price"] is None for t in tutors)


def test_move_invalid_category(client: TestClient) -> None:
    r = client.get("/moves/?category=Bogus")
    assert r.status_code == 422


def test_tutors_all(client: TestClient) -> None:
    r = client.get("/moves/tutors/all")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    t = data[0]
    assert "move_id" in t and "move_name_en" in t
    assert "location_id" in t and "location_name_en" in t
    assert "price" in t and "currency" in t


def test_experts_all(client: TestClient) -> None:
    r = client.get("/moves/experts/all")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    e = data[0]
    assert "move_id" in e and "move_name_en" in e
    assert "location" in e
    assert isinstance(e["required_pokemon"], list)
    assert isinstance(e["required_types"], list)


def test_tms_list(client: TestClient) -> None:
    r = client.get("/tms/")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 121
    assert data[0]["number"] == 1
    assert data[-1]["number"] == 121
    first = data[0]
    assert "move_id" in first and "name_en" in first
    assert "type" in first and "category" in first
    assert "locations" in first and isinstance(first["locations"], list)


def test_tm_by_number(client: TestClient) -> None:
    r = client.get("/tms/5")
    assert r.status_code == 200
    data = r.json()
    assert data["number"] == 5
    assert data["name_en"] == "Roar"
    assert len(data["locations"]) >= 2
    location_names = {loc["location_name_en"] for loc in data["locations"]}
    assert "Celadon City" in location_names


def test_tm_not_found(client: TestClient) -> None:
    r = client.get("/tms/200")
    assert r.status_code == 404


def test_types_list(client: TestClient) -> None:
    r = client.get("/types/")
    assert r.status_code == 200
    assert len(r.json()) >= 18  # 18 canonical + triple-fusion types


def test_types_by_name_fr(client: TestClient) -> None:
    r = client.get("/types/by-name/Feu")
    assert r.status_code == 200
    assert r.json()["name_en"] == "Fire"


def test_abilities_list(client: TestClient) -> None:
    r = client.get("/abilities/")
    assert r.status_code == 200
    assert len(r.json()) > 100


def test_ability_search(client: TestClient) -> None:
    r = client.get("/abilities/search?q=blaze")
    assert r.status_code == 200
    assert any(a["name_en"] == "Blaze" for a in r.json())


def test_ability_detail(client: TestClient) -> None:
    """Detail endpoint returns EN/FR descriptions."""
    r = client.get("/abilities/1")  # Adaptability
    assert r.status_code == 200
    a = r.json()
    assert a["id"] == 1
    assert a["name_en"] == "Adaptability"
    assert a["name_fr"] is not None
    assert a["description_en"] is not None
    assert a["description_fr"] is not None


def test_ability_detail_not_found(client: TestClient) -> None:
    r = client.get("/abilities/999999")
    assert r.status_code == 404


def test_type_by_id(client: TestClient) -> None:
    """Type by numeric ID returns correct fields."""
    r = client.get("/types/1")  # Bug
    assert r.status_code == 200
    t = r.json()
    assert t["id"] == 1
    assert t["name_en"] == "Bug"
    assert t["name_fr"] is not None
    assert t["is_triple_fusion_type"] is False


def test_type_triple_fusion_flag(client: TestClient) -> None:
    """Triple-fusion-only types are correctly flagged."""
    r = client.get("/types/")
    assert r.status_code == 200
    types = r.json()
    triple = [t for t in types if t["is_triple_fusion_type"]]
    standard = [t for t in types if not t["is_triple_fusion_type"]]
    assert len(standard) >= 18
    assert len(triple) >= 8
    # All triple-fusion types must have composite names (contain "/")
    assert all("/" in t["name_en"] for t in triple)


def test_type_by_id_not_found(client: TestClient) -> None:
    r = client.get("/types/9999")
    assert r.status_code == 404


def test_power_min_greater_than_max_returns_empty(client: TestClient) -> None:
    """power_min > power_max is not an error — returns empty list."""
    r = client.get("/moves/?power_min=100&power_max=50")
    assert r.status_code == 200
    assert r.json() == []
