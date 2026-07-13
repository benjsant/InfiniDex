"""Unit tests for the shared on-disk HTTP cache — no network, requests mocked."""

from __future__ import annotations

from etl.utils import http


class _Resp:
    status_code = 200

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def _install_fake_get(monkeypatch, calls: list) -> None:
    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(url)
        return _Resp({"call": len(calls)})
    monkeypatch.setattr(http.requests, "get", fake_get)


def test_get_json_caches_and_reuses(tmp_path, monkeypatch):
    monkeypatch.setattr(http, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(http, "CACHE_TTL_HOURS", 24.0)
    calls: list = []
    _install_fake_get(monkeypatch, calls)

    assert http.get_json("https://x/pokemon/1") == {"call": 1}
    assert http.get_json("https://x/pokemon/1") == {"call": 1}   # hit — pas de refetch
    assert len(calls) == 1

    assert http.get_json("https://x/pokemon/2") == {"call": 2}   # URL différente
    assert len(calls) == 2


def test_get_json_cache_disabled_by_ttl_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(http, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(http, "CACHE_TTL_HOURS", 0.0)
    calls: list = []
    _install_fake_get(monkeypatch, calls)

    http.get_json("https://x/pokemon/1")
    http.get_json("https://x/pokemon/1")
    assert len(calls) == 2
    assert not any(tmp_path.iterdir())   # rien n'est écrit


def test_get_json_cache_opt_out_param(tmp_path, monkeypatch):
    monkeypatch.setattr(http, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(http, "CACHE_TTL_HOURS", 24.0)
    calls: list = []
    _install_fake_get(monkeypatch, calls)

    http.get_json("https://x/pokemon/1")
    http.get_json("https://x/pokemon/1", cache=False)   # fetch forcé
    assert len(calls) == 2


def test_corrupt_cache_entry_refetches(tmp_path, monkeypatch):
    monkeypatch.setattr(http, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(http, "CACHE_TTL_HOURS", 24.0)
    calls: list = []
    _install_fake_get(monkeypatch, calls)

    path = http._cache_path("https://x/pokemon/1", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{corrompu", encoding="utf-8")

    assert http.get_json("https://x/pokemon/1") == {"call": 1}
    assert len(calls) == 1


def test_params_are_part_of_the_cache_key(tmp_path, monkeypatch):
    monkeypatch.setattr(http, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(http, "CACHE_TTL_HOURS", 24.0)
    calls: list = []
    _install_fake_get(monkeypatch, calls)

    http.get_json("https://x/api.php", params={"page": "Pokédex"})
    http.get_json("https://x/api.php", params={"page": "List_of_Moves"})
    assert len(calls) == 2


def test_prefetch_warms_the_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(http, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(http, "CACHE_TTL_HOURS", 24.0)
    calls: list = []
    _install_fake_get(monkeypatch, calls)

    urls = [f"https://x/pokemon/{i}" for i in (1, 2, 3, 1)]   # doublon volontaire
    http.prefetch_json(urls, workers=2)
    assert len(calls) == 3   # dédupliqué

    http.get_json("https://x/pokemon/2")
    assert len(calls) == 3   # servi par le cache
