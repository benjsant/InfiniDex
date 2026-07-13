"""
ETL Step 2b — Build name_en → Pokepedia mapping.

Scrapes https://www.pokepedia.fr/Liste_des_Pokémon_dans_l'ordre_du_Pokédex_National
using requests + lxml (already pulled in by Scrapy) to extract for each Pokémon:
  - national_id
  - name_fr  (French name = Pokepedia page slug)
  - name_en  (English name = join key with IF data)
  - gen7_url e.g. https://www.pokepedia.fr/Bulbizarre/Génération_7

Output: data/pokepedia_names.json
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from lxml import html

from etl.utils.io import save_json
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

LIST_URL = (
    "https://www.pokepedia.fr/"
    "Liste_des_Pok%C3%A9mon_dans_l%27ordre_du_Pok%C3%A9dex_National"
)
OUTPUT = Path("data/pokepedia_names.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 "
        "(Educational project - Pokemon Infinite Fusion)"
    )
}


def fetch_page() -> bytes:
    resp = requests.get(LIST_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.content


def parse_list(content: bytes) -> list[dict]:
    """
    Parse the Pokémon list table with lxml.
    Columns: N° | Image | FR name (link) | EN name | DE name | JP name | Types
    """
    tree    = html.fromstring(content)
    results = []
    seen: set[int] = set()

    # Find all table rows that look like Pokémon entries
    rows = tree.xpath("//table//tr[td]")

    for row in rows:
        cells = row.xpath("td")
        if len(cells) < 4:
            continue

        # Cell 0: national ID — strip leading zeros and # symbols
        id_text = re.sub(r"[^0-9]", "", cells[0].text_content().strip())
        if not id_text:
            continue
        national_id = int(id_text)

        if national_id in seen:
            continue
        seen.add(national_id)

        # Cell 2: French name + internal link → slug
        fr_links = cells[2].xpath(".//a[@href]")
        if fr_links:
            name_fr      = fr_links[0].text_content().strip()
            raw_href     = fr_links[0].get("href", "")
            # Pokepédia switched from relative hrefs (/Bulbizarre) to
            # protocol-relative ones (//www.pokepedia.fr/Bulbizarre). A bare
            # lstrip("/") kept the domain in the slug and every gen7_url
            # 404'd (https://www.pokepedia.fr/www.pokepedia.fr/...). Parse the
            # href and keep only the path component — handles relative,
            # protocol-relative and absolute forms alike.
            pokepedia_slug = unquote(urlparse(raw_href).path.lstrip("/"))
        else:
            name_fr        = cells[2].text_content().strip()
            pokepedia_slug = name_fr.replace(" ", "_")

        # Cell 3: English name. Species with forms append the form label in a
        # <small> sibling ("Oricorio<br><small>Baile Style</small>"), so a raw
        # text_content() gives "OricorioBaile Style" and the name never matches
        # IF data (7 species used to fall out of the mapping this way). The
        # clean name is the Bulbapedia link's own text.
        en_links = cells[3].xpath(".//a")
        if en_links:
            name_en = en_links[0].text_content().strip()
        else:
            name_en = cells[3].text_content().strip()

        if not name_en or not name_fr:
            continue

        results.append({
            "national_id":    national_id,
            "name_en":        name_en,
            "name_fr":        name_fr,
            "pokepedia_slug": pokepedia_slug,
            "gen7_url":       f"https://www.pokepedia.fr/{pokepedia_slug}/Génération_7",
        })

    return sorted(results, key=lambda x: x["national_id"])


def main() -> None:
    LOGGER.info("Fetching Pokepedia Pokémon list...")
    content = fetch_page()
    entries = parse_list(content)

    # Fail loudly instead of silently saving a broken mapping: a bad slug here
    # makes every downstream scrapy request 404 (the movesets crawl).
    if not entries:
        raise RuntimeError(
            f"Parsed 0 Pokémon from {LIST_URL} — the page layout has likely "
            f"changed upstream."
        )
    bad = [e for e in entries if "/" in e["pokepedia_slug"] or not e["pokepedia_slug"]]
    if bad:
        raise RuntimeError(
            f"{len(bad)} malformed pokepedia_slug values (e.g. "
            f"{bad[0]['pokepedia_slug']!r}) — href parsing is broken again."
        )

    save_json(OUTPUT, entries)
    LOGGER.info("Saved %d entries → %s", len(entries), OUTPUT)


if __name__ == "__main__":
    main()
