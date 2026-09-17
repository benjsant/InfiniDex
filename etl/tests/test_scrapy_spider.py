"""Lock the Scrapy entry-point contract of the movesets spider.

Scrapy 2.19 removed `Spider.start_requests()`. The spider only defined that
method, so the Dependabot bump made every crawl finish instantly with zero
requests and no error. This test drives the real `start()` entry point and
fails if the spider stops emitting requests after a future Scrapy upgrade.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "etl" / "pokepedia_scraper"))

from pokepedia_scraper.spiders.if_movesets_spider import IFMovesetSpider  # noqa: E402


def _collect(spider) -> list:
    async def run():
        return [r async for r in spider.start()]
    return asyncio.run(run())


def test_spider_implements_async_start():
    assert inspect.isasyncgenfunction(IFMovesetSpider.start)
    # The base class must not be what runs: it would read the empty start_urls.
    assert "start" in IFMovesetSpider.__dict__


def test_start_emits_one_request_per_page_and_groups_forms(tmp_path):
    (tmp_path / "pokedex_if.json").write_text(json.dumps([
        {"if_id": 25,  "name_en": "Pikachu"},
        {"if_id": 577, "name_en": "Tornadus"},
        {"if_id": 578, "name_en": "Tornadus (Therian)"},   # same species page
    ]))
    (tmp_path / "pokepedia_names.json").write_text(json.dumps([
        {"name_en": "Pikachu",  "pokepedia_slug": "Pikachu", "gen7_url": "https://www.pokepedia.fr/Pikachu/Génération_7"},
        {"name_en": "Tornadus", "pokepedia_slug": "Boréas",  "gen7_url": "https://www.pokepedia.fr/Boréas/Génération_7"},
    ]))

    requests = _collect(IFMovesetSpider(data_dir=str(tmp_path)))

    assert len(requests) == 2, "un crawl à 0 requête = rupture silencieuse du point d'entrée"
    by_url = {r.url: r for r in requests}
    boreas = next(r for u, r in by_url.items() if "Bor" in u)
    assert [i for i, _ in boreas.meta["pokemon_entries"]] == [577, 578]
