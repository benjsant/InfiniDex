"""
Scrapy pipeline — persist scraped movesets to data/movesets_base.json.

Unlike the predictiondex which wrote directly to PostgreSQL, we write to JSON
so the merge step (transform_merge_movesets.py) can apply IF-specific overrides
before the final DB load.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

LOGGER      = logging.getLogger(__name__)
# Resolve relative to project root — pipeline runs from scrapy project dir
_ROOT       = Path(__file__).resolve().parents[3]
OUTPUT_FILE = _ROOT / "data/movesets_base.json"


class MovesetPipeline:
    def open_spider(self, spider) -> None:
        self.records: list[dict] = []
        LOGGER.info("[PIPELINE] Moveset pipeline opened — output: %s", OUTPUT_FILE)

    def close_spider(self, spider) -> None:
        # Never clobber a good file with an empty crawl: when every request
        # fails (site down, URL scheme changed upstream), keeping the previous
        # movesets_base.json lets the merge step run on stale-but-valid data.
        if not self.records and OUTPUT_FILE.exists():
            LOGGER.error(
                "[PIPELINE] Crawl produced 0 records — keeping existing %s untouched",
                OUTPUT_FILE,
            )
            return
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(json.dumps(self.records, ensure_ascii=False, indent=2))
        LOGGER.info("[PIPELINE] Saved %d moveset records → %s", len(self.records), OUTPUT_FILE)

    def process_item(self, item, spider):
        try:
            item.validate()
        except ValueError as exc:
            spider.logger.warning("[INVALID ITEM] %s — %s", exc, dict(item))
            return item

        self.records.append({
            "pokemon_if_id":  item["pokemon_if_id"],
            "move_name_fr":   item["move_name_fr"].strip(),
            "method":         item["method"],
            "level":          item.get("level"),
            "source":         "base",
        })
        return item
