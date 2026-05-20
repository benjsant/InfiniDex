"""ETL — Extract item locations from the Infinite Fusion wiki.

Source : https://infinitefusion.fandom.com/wiki/List_of_Items
API    : MediaWiki action=parse&prop=wikitext

Each item row in the wiki table has a Location cell structured as:
    '''Shops'''
    * [[Location 1]]
    * [[Location 2]]
    '''Found/Given'''
    * [[Location 3]]

We parse each bold-header section into a method ('shop'|'found'|'wild'|'other'),
then each bullet point as an individual item_location row.

Idempotent: ON CONFLICT (item_id, location_name, method) DO NOTHING.
"""

from __future__ import annotations

import re
import time

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging
from etl.utils.wikitext import fetch_wikitext

LOGGER = setup_logging(__name__)

REQUEST_DELAY = 0.5

# Map bold-header text (lowercased) → method value
METHOD_MAP: dict[str, str] = {
    "shops":       "shop",
    "shop":        "shop",
    "found":       "found",
    "found/given": "found",
    "given":       "found",
    "gift":        "found",
    "wild":        "wild",
    "wild pokémon": "wild",
    "wild pokemon": "wild",
    "other":       "other",
}


def _method_for_header(header: str) -> str:
    key = header.strip().lower()
    return METHOD_MAP.get(key, "other")


def _clean_wiki_link(text: str) -> str:
    """[[Page Name|Display]] → Display, [[Page Name]] → Page Name."""
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    return text.strip()


def _clean_template(text: str) -> str:
    """Strip or simplify {{template|arg}} → arg (best-effort)."""
    # {{gym|4}} → "gym 4", {{route|22}} → "Route 22", etc.
    text = re.sub(r"\{\{(\w+)\|([^}]+)\}\}", lambda m: f"{m.group(1)} {m.group(2)}", text)
    text = re.sub(r"\{\{[^}]+\}\}", "", text)
    return text.strip()


def _strip_wiki_markup(text: str) -> str:
    """Remove all remaining wiki markup from a text fragment."""
    text = _clean_wiki_link(text)
    text = _clean_template(text)
    # Remove inline HTML/CSS attributes (style="...")
    text = re.sub(r'style="[^"]*"', "", text)
    # Remove bold/italic markers
    text = re.sub(r"'{2,3}", "", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_location_cell(cell: str) -> list[tuple[str, str, str | None]]:
    """Parse a location cell into [(location_name, method, notes)].

    The cell may contain multiple bold-header sections, each followed
    by bullet-point locations. A location may include extra notes in
    parentheses which are extracted separately.
    """
    results: list[tuple[str, str, str | None]] = []

    # Split on bold headers: '''Header Text'''
    # We keep the delimiter to know which method applies
    parts = re.split(r"'''([^']+)'''", cell)

    # parts[0] is text before the first header (usually empty or CSS)
    # parts[1], parts[2], parts[3], parts[4], ... alternate header/content
    current_method = "other"

    for i, part in enumerate(parts):
        if i % 2 == 1:
            # This is a header
            current_method = _method_for_header(part)
        else:
            # This is content under the current method
            for line in part.split("\n"):
                line = line.strip()
                if not line.startswith("*"):
                    continue
                raw = line.lstrip("* ").strip()
                raw = _strip_wiki_markup(raw)
                if not raw:
                    continue

                # Extract notes in parentheses at end
                notes: str | None = None
                m = re.search(r"\(([^)]+)\)\s*$", raw)
                if m:
                    notes = m.group(1).strip()
                    raw = raw[: m.start()].strip()

                if raw:
                    results.append((raw, current_method, notes))

    return results


def parse_item_rows(wikitext: str) -> list[dict]:
    """Extract list of {name, location_entries} from the wiki table wikitext."""
    items: list[dict] = []

    # Split into table rows (separated by |-) and look for item rows
    # Each item row has 5 cells: icon | name | effect | price | location
    # We identify item rows by the presence of {{ItemIcon|...}}
    rows = re.split(r"\n\|-", wikitext)

    for row in rows:
        cells = re.split(r"\n\|(?!\|)", row)
        # Filter out header cells (starting with !)
        cells = [c for c in cells if not c.strip().startswith("!")]

        # Layout after split:
        #   cells[0] = "" (empty — text before first \n|)
        #   cells[1] = icon  {{ItemIcon|...}}
        #   cells[2] = name
        #   cells[3] = effect
        #   cells[4] = price
        #   cells[5] = location cell
        if len(cells) < 6:
            continue

        # Skip non-item rows (no icon template)
        if "{{ItemIcon" not in cells[1]:
            continue

        name_raw    = cells[2].strip()
        location_raw = cells[5].strip()

        if not name_raw:
            continue

        name = _strip_wiki_markup(name_raw)
        if not name:
            continue

        location_entries = parse_location_cell(location_raw)
        items.append({"name": name, "locations": location_entries})

    return items


def load_item_locations(conn, items: list[dict]) -> None:
    cur = conn.cursor()

    # Build name → id map from DB
    cur.execute("SELECT id, name_en FROM item")
    name_to_id: dict[str, int] = {row[1].lower(): row[0] for row in cur.fetchall()}

    inserted = skipped = unmatched = 0

    for item in items:
        item_id = name_to_id.get(item["name"].lower())
        if item_id is None:
            LOGGER.warning("Item not found in DB: '%s'", item["name"])
            unmatched += 1
            continue

        for location_name, method, notes in item["locations"]:
            cur.execute(
                """
                INSERT INTO item_location (item_id, location_name, method, notes)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (item_id, location_name, method) DO NOTHING
                """,
                (item_id, location_name, method, notes),
            )
            if cur.rowcount:
                inserted += 1
            else:
                skipped += 1

    conn.commit()
    cur.close()
    LOGGER.info(
        "Done — %d locations inserted | %d already present | %d items unmatched",
        inserted, skipped, unmatched,
    )


def main() -> None:
    LOGGER.info("Fetching wikitext from IF wiki…")
    wikitext = fetch_wikitext("List_of_Items")
    time.sleep(REQUEST_DELAY)

    LOGGER.info("Parsing item rows…")
    items = parse_item_rows(wikitext)
    LOGGER.info("%d items parsed from the wiki", len(items))

    with pg_connection() as conn:
        load_item_locations(conn, items)


if __name__ == "__main__":
    main()
