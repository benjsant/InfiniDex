"""Tests for /stats/coverage and /fusions/involving."""

from fastapi.testclient import TestClient


def test_stats_coverage(client: TestClient) -> None:
    r = client.get("/stats/coverage")
    assert r.status_code == 200
    d = r.json()
    assert d["pokemon_total"] >= 500
    assert d["moves_total"] >= 600
    assert d["abilities_total"] >= 150
    assert d["fusion_sprites_total"] >= 4
    assert d["triple_fusions_total"] == 23
    assert d["creators_total"] > 1000


def test_fusions_involving(client: TestClient) -> None:
    r = client.get("/fusions/involving/1?limit=20")
    assert r.status_code == 200
    data = r.json()
    assert len(data) <= 20
    for row in data:
        assert row["role"] in {"head", "body"}
        assert 1 in (row["head_id"], row["body_id"])
        assert row["partner_id"] != 1 or row["head_id"] == row["body_id"] == 1


def test_fusions_involving_not_found(client: TestClient) -> None:
    assert client.get("/fusions/involving/99999").status_code == 404
