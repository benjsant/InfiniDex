"""ETL script — populates the `item` table (restricted scope: 3 categories).

Source: https://infinitefusion.fandom.com/wiki/List_of_Items

Scope:
    - Fusion Items    (DNA Splicers, Super Splicers, etc.)
    - Evolution Items (Fire Stone, Moon Stone, Everstone, …)
    - Valuables       (Heart Scale, Nugget, Pearl, …)

Out of scope for this PR:
    Poké Balls, Medicine, Berries, Battle Items, Held Items, TMs & HMs, etc.

Idempotent: TRUNCATE + INSERT.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging
from etl.utils.wikitext import fetch_wikitext

LOGGER = setup_logging(__name__)

WIKI_PAGE = "List_of_Items"

SECTIONS = [
    # (wiki section title, db category, column layout)
    # "layout" describes the columns of the wikitable so the parser knows
    # which cell is effect vs price vs sell price.
    ("Fusion Items",    "fusion",    "icon_name_effect_price_location"),
    ("Evolution Items", "evolution", "icon_name_effect_price_location"),
    ("Valuables",       "valuable",  "icon_name_price_sell_collector_location"),
]


@dataclass
class ItemRow:
    name_en:    str
    category:   str
    effect:     str | None
    price_buy:  int | None
    price_sell: int | None


# ─── Wiki helpers ────────────────────────────────────────────────────────────

_WIKILINK_RE  = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
_ANCHOR_RE    = re.compile(r"\[\[[^#]*#[^|\]]*\|([^\]]*)\]\]")
_TEMPLATE_RE  = re.compile(r"\{\{[^}]+\}\}")
_HTML_TAG_RE  = re.compile(r"<[^>]+>")
_PRICE_RE     = re.compile(r"₽\s*([\d,]+)")
_STYLE_ATTR_RE = re.compile(r'^\s*(?:style|colspan|rowspan|class)="[^"]*"\s*\|\s*', re.IGNORECASE)


def strip_markup(text: str) -> str:
    """Plain-text version of a wiki cell."""
    text = _ANCHOR_RE.sub(r"\1", text)     # [[Page#Anchor|display]] → display
    text = _WIKILINK_RE.sub(r"\1", text)   # [[display]] or [[target|display]]
    text = _TEMPLATE_RE.sub("", text)      # drop {{Icon|...}} etc.
    text = _HTML_TAG_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def strip_cell_attrs(cell: str) -> str:
    """Remove leading `style="..." |` or similar attribute prefix."""
    return _STYLE_ATTR_RE.sub("", cell, count=1)


def parse_price(cell: str) -> int | None:
    """Extract first ₽N,NNN value from cell, or None."""
    clean = strip_markup(cell)
    m = _PRICE_RE.search(clean)
    return int(m.group(1).replace(",", "")) if m else None


def extract_section_body(text: str, title: str) -> str | None:
    """Return the content between `== title ==` and next `==`."""
    pat = re.compile(
        rf"==\s*{re.escape(title)}\s*==(.*?)(?=^==|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    m = pat.search(text)
    return m.group(1) if m else None


def extract_first_table(body: str) -> str | None:
    """Return the wikitext between the first `{|` and its matching `|}`."""
    start = body.find("{|")
    if start == -1:
        return None
    end = body.find("|}", start)
    if end == -1:
        return None
    return body[start + 2 : end]


def split_rows(table: str) -> list[list[str]]:
    """Split a wikitable into data rows (each a list of cells).

    Skips the header row (lines starting with `!`) and any empty rows.
    """
    blocks = re.split(r"^\s*\|-\s*$", table, flags=re.MULTILINE)
    rows: list[list[str]] = []
    for block in blocks:
        lines = [l for l in block.splitlines() if l.strip()]
        # Skip header / blank
        if not lines or lines[0].lstrip().startswith("!"):
            continue
        # A cell starts with `|`. A single line can contain multiple `||`-
        # separated cells. Split only on standalone `|` at beginning of line.
        cells: list[str] = []
        current: list[str] = []
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("|"):
                if current:
                    cells.append("\n".join(current))
                current = [stripped[1:]]
            else:
                current.append(line)
        if current:
            cells.append("\n".join(current))
        rows.append([c.strip() for c in cells])
    return rows


# ─── Layout-specific parsers ─────────────────────────────────────────────────

def parse_fusion_or_evolution(rows: list[list[str]], category: str) -> list[ItemRow]:
    """Layout: icon | name | effect | price | location."""
    out: list[ItemRow] = []
    for cells in rows:
        if len(cells) < 5:
            LOGGER.debug("Row skipped (%d cells): %r", len(cells), cells)
            continue
        _icon, name_cell, effect_cell, price_cell, _loc_cell = cells[:5]
        name = strip_markup(strip_cell_attrs(name_cell))
        if not name:
            continue
        effect = strip_markup(strip_cell_attrs(effect_cell))
        out.append(ItemRow(
            name_en    = name,
            category   = category,
            effect     = effect or None,
            price_buy  = parse_price(price_cell),
            price_sell = None,
        ))
    return out


def parse_valuables(rows: list[list[str]]) -> list[ItemRow]:
    """Layout: icon | name | price | sale_price | collector | location."""
    out: list[ItemRow] = []
    for cells in rows:
        if len(cells) < 6:
            LOGGER.debug("Row skipped (%d cells): %r", len(cells), cells)
            continue
        _icon, name_cell, price_cell, sell_cell, _collector, _loc = cells[:6]
        name = strip_markup(strip_cell_attrs(name_cell))
        if not name:
            continue
        out.append(ItemRow(
            name_en    = name,
            category   = "valuable",
            effect     = None,
            price_buy  = parse_price(price_cell),
            price_sell = parse_price(sell_cell),
        ))
    return out


# ─── Main ────────────────────────────────────────────────────────────────────

def run(conn) -> None:
    cur = conn.cursor()
    text = fetch_wikitext(WIKI_PAGE)
    LOGGER.info("Wiki: %d characters fetched", len(text))

    all_items: list[ItemRow] = []
    for section_title, category, layout in SECTIONS:
        body = extract_section_body(text, section_title)
        if body is None:
            LOGGER.warning("Section not found: %s", section_title)
            continue
        table = extract_first_table(body)
        if table is None:
            LOGGER.warning("Table not found for: %s", section_title)
            continue
        rows = split_rows(table)
        if layout == "icon_name_effect_price_location":
            items = parse_fusion_or_evolution(rows, category)
        elif layout == "icon_name_price_sell_collector_location":
            items = parse_valuables(rows)
        else:
            LOGGER.error("Unknown layout: %s", layout)
            continue
        LOGGER.info("  %s: %d items parsed", section_title, len(items))
        all_items.extend(items)

    # Deduplication: by name + category (the wiki may list variants twice
    # with different prices — keep the first).
    seen: set[str] = set()
    unique: list[ItemRow] = []
    for it in all_items:
        key = it.name_en.lower()
        if key in seen:
            LOGGER.debug("Duplicate skipped: %s", it.name_en)
            continue
        seen.add(key)
        unique.append(it)

    cur.execute("TRUNCATE item RESTART IDENTITY CASCADE")
    for it in unique:
        cur.execute(
            """
            INSERT INTO item (name_en, category, effect, price_buy, price_sell)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (it.name_en, it.category, it.effect, it.price_buy, it.price_sell),
        )

    conn.commit()
    cur.close()
    LOGGER.info("Done — %d items inserted (%d Fusion, %d Evolution, %d Valuables)",
                len(unique),
                sum(1 for i in unique if i.category == "fusion"),
                sum(1 for i in unique if i.category == "evolution"),
                sum(1 for i in unique if i.category == "valuable"))


def main() -> None:
    with pg_connection() as conn:
        run(conn)


if __name__ == "__main__":
    sys.exit(main() or 0)
