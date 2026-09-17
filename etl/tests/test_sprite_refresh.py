"""Redrawn sprites must be refreshed, not skipped because the file exists.

Artists redraw sprites under the same filename: the old "skip if present"
logic kept stale art forever (seen on 25.6.png) while the credits already
named the new artist. Pure tests: synthetic sheets, requests mocked.
"""

from __future__ import annotations

from PIL import Image

from etl.scripts import extract_sprites as es

SIZE = es.SPRITE_SIZE


def _sheet(colors: dict[int, tuple[int, int, int, int]]) -> Image.Image:
    """Sheet where each body_id cell is filled with a flat colour."""
    sheet = Image.new("RGBA", (SIZE * es.GRID_COLS, SIZE * 2), (0, 0, 0, 0))
    for body_id, color in colors.items():
        x, y = (body_id % es.GRID_COLS) * SIZE, (body_id // es.GRID_COLS) * SIZE
        sheet.paste(Image.new("RGBA", (SIZE, SIZE), color), (x, y))
    return sheet


def _pixel(path, xy=(10, 10)):
    with Image.open(path) as im:
        return im.convert("RGBA").getpixel(xy)


def test_write_creates_refreshes_and_keeps_identical(tmp_path):
    red, blue, green = (255, 0, 0, 255), (0, 0, 255, 255), (0, 255, 0, 255)
    # On disk: body 1 already current, body 6 stale (old red art), body 7 absent.
    _sheet({1: green, 6: red}).crop((SIZE, 0, 2 * SIZE, SIZE)).save(tmp_path / "25.1.png")
    _sheet({6: red}).crop((6 * SIZE, 0, 7 * SIZE, SIZE)).save(tmp_path / "25.6.png")
    mtime_1 = (tmp_path / "25.1.png").stat().st_mtime_ns

    upstream = _sheet({1: green, 6: blue, 7: green})   # body 6 redrawn in blue
    created, refreshed, unchanged, failed = es.write_sheet_sprites(upstream, 25, "", [1, 6, 7], tmp_path)

    assert (created, refreshed, unchanged, failed) == (1, 1, 1, 0)
    assert _pixel(tmp_path / "25.6.png") == blue           # redraw applied
    assert _pixel(tmp_path / "25.7.png") == green          # new sprite written
    assert (tmp_path / "25.1.png").stat().st_mtime_ns == mtime_1   # identical: untouched


class _Resp:
    def __init__(self, status, content=b"", etag=None):
        self.status_code, self.content = status, content
        self.headers = {"ETag": etag} if etag else {}


def test_fetch_sheet_sends_if_none_match_and_handles_304(monkeypatch):
    seen = {}
    def fake_get(url, headers=None, timeout=None):
        seen.update(headers or {})
        return _Resp(304)
    monkeypatch.setattr(es.requests, "get", fake_get)

    status, content, etag = es.fetch_sheet("https://x/25/25.png", '"abc"')
    assert seen["If-None-Match"] == '"abc"'
    assert (status, content, etag) == ("not_modified", None, '"abc"')


def test_fetch_sheet_returns_new_etag_on_change(monkeypatch):
    monkeypatch.setattr(es.requests, "get", lambda url, headers=None, timeout=None: _Resp(200, b"PNG", '"new"'))
    assert es.fetch_sheet("https://x/25/25.png", '"old"') == ("modified", b"PNG", '"new"')


def test_fetch_sheet_without_etag_sends_no_condition(monkeypatch):
    seen = {}
    def fake_get(url, headers=None, timeout=None):
        seen.update(headers or {})
        return _Resp(200, b"PNG", '"e1"')
    monkeypatch.setattr(es.requests, "get", fake_get)
    es.fetch_sheet("https://x/25/25.png", None)
    assert "If-None-Match" not in seen


def test_fetch_sheet_404_is_missing(monkeypatch):
    monkeypatch.setattr(es.requests, "get", lambda url, headers=None, timeout=None: _Resp(404))
    assert es.fetch_sheet("https://x/999/999.png", None) == ("missing", None, None)


def test_etags_roundtrip_and_corrupt_file(tmp_path):
    path = tmp_path / "spritesheet_etags.json"
    es.save_etags(path, {"25": '"a"', "25a": '"b"'})
    assert es.load_etags(path) == {"25": '"a"', "25a": '"b"'}
    path.write_text("{corrompu")
    assert es.load_etags(path) == {}                         # re-verify everything
