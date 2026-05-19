"""Tests for /sprites and /triple-fusions routes."""

from fastapi.testclient import TestClient


def test_sprites_for_pair(client: TestClient) -> None:
    r = client.get("/sprites/1/4")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        s = data[0]
        assert s["head_id"] == 1
        assert s["body_id"] == 4
        assert "sprite_path" in s
        assert isinstance(s["creators"], list)


def test_sprites_unknown_pair_returns_empty(client: TestClient) -> None:
    r = client.get("/sprites/9999/9999")
    assert r.status_code == 200
    assert r.json() == []


def test_sprite_image_served(client: TestClient) -> None:
    r = client.get("/sprites/1/4/image")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_sprite_image_missing(client: TestClient) -> None:
    r = client.get("/sprites/9999/9999/image")
    assert r.status_code == 404


def test_triple_fusions_list(client: TestClient) -> None:
    r = client.get("/triple-fusions/")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 23
    names = {tf["name_en"] for tf in data}
    assert "Zapmolcuno" in names


def test_triple_fusion_detail(client: TestClient) -> None:
    # Resolve Zapmolcuno's ID from the list (IDs differ between dev and CI DBs).
    listing = client.get("/triple-fusions/").json()
    zapmolcuno = next(tf for tf in listing if tf["name_en"] == "Zapmolcuno")
    r = client.get(f"/triple-fusions/{zapmolcuno['id']}")
    assert r.status_code == 200
    tf = r.json()
    assert tf["name_en"] == "Zapmolcuno"
    components = {c["name_en"] for c in tf["components"]}
    assert components == {"Articuno", "Moltres", "Zapdos"}
    assert len(tf["abilities"]) >= 1


def test_triple_fusion_not_found(client: TestClient) -> None:
    r = client.get("/triple-fusions/999")
    assert r.status_code == 404
