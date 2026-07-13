"""
Scrapy Spider — Pokémon Infinite Fusion moveset scraper (Pokepedia, Gen 7 USUL).

Targets Gen 7 Ultra-Soleil / Ultra-Lune (USUL) data only.

URL pattern: https://www.pokepedia.fr/{pokepedia_slug}/Génération_7

Level-up table: column header "USUL" → we extract only those levels
CT section:     h4 "Soleil et Lune / Ultra-Soleil" → table below it
Breeding:       section id Par_reproduction — ALL Pokémon
Tutor:          section id Par_donneur_de_capacités — ALL Pokémon
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import scrapy

from pokepedia_scraper.items import MovesetItem


# ── Column detection ─────────────────────────────────────────────────────────

# Exact abbreviation used in the level-up table header
USUL_PATTERNS = ["USUL", "US UL", "Ultra-Soleil", "Ultra Soleil", "USUM"]

# Patterns to identify the USUL CT subsection h4
CT_USUL_PATTERNS = [
    "Soleil et Lune",
    "Ultra-Soleil",
    "Ultra Soleil",
]

LEVEL_RE = re.compile(r"N\.(\d+)")


class IFMovesetSpider(scrapy.Spider):
    name          = "if_movesets"
    allowed_domains = ["pokepedia.fr"]

    # ── Startup ──────────────────────────────────────────────────────────────

    def start_requests(self):
        """
        Build request list by joining:
          - data/pokedex_if.json      → IF IDs + EN names
          - data/pokepedia_names.json → EN name → Pokepedia slug + gen7 URL

        Falls back to a best-effort slug (name_fr from PokeAPI) if no match found.
        """
        # Resolve data/ relative to project root (4 levels up from this file)
        _root = Path(__file__).resolve().parents[4]
        pokedex_file   = _root / "data/pokedex_if.json"
        pokepedia_file = _root / "data/pokepedia_names.json"

        if not pokedex_file.exists():
            self.logger.error("data/pokedex_if.json not found — run extract_pokedex_if.py first")
            return

        pokedex = json.loads(pokedex_file.read_text())

        # Build mapping: name_en.lower() → pokepedia entry
        pokepedia_map: dict[str, dict] = {}
        if pokepedia_file.exists():
            for entry in json.loads(pokepedia_file.read_text()):
                pokepedia_map[entry["name_en"].lower()] = entry
        else:
            self.logger.warning(
                "data/pokepedia_names.json not found — "
                "run extract_pokepedia_names.py first for accurate URLs"
            )

        # Group IF entries by target URL: alternate forms (Oricorio styles,
        # Castform weathers, ...) share one Pokepedia page under one name.
        # Scrapy dedupes identical requests, so a request per entry meant only
        # the FIRST if_id of each name got a moveset — the others got nothing.
        # One request per URL + fan-out of the parsed items to every if_id.
        url_groups: dict[str, dict] = {}

        for entry in pokedex:
            if_id   = entry["if_id"]
            name_en = entry["name_en"]

            poke_entry = pokepedia_map.get(name_en.lower())

            if poke_entry:
                gen7_url      = poke_entry["gen7_url"]
                pokepedia_slug = poke_entry["pokepedia_slug"]
            else:
                # Fallback: use EN name directly (will likely 404 for Gen 3+)
                pokepedia_slug = name_en.replace(" ", "_")
                gen7_url       = f"https://www.pokepedia.fr/{pokepedia_slug}/Génération_7"
                self.logger.warning(
                    "[NO POKEPEDIA MATCH] #%d %s — using fallback URL", if_id, name_en
                )

            group = url_groups.setdefault(
                gen7_url, {"pokepedia_slug": pokepedia_slug, "entries": []}
            )
            group["entries"].append((if_id, name_en))

        for gen7_url, group in url_groups.items():
            first_id, first_name = group["entries"][0]
            yield scrapy.Request(
                url=gen7_url,
                callback=self.parse_all,
                errback=self.handle_error,
                meta={
                    "pokemon_if_id":    first_id,
                    "pokemon_name_en":  first_name,
                    "pokepedia_slug":   group["pokepedia_slug"],
                    "pokemon_entries":  group["entries"],
                },
            )

    def handle_error(self, failure):
        meta = failure.request.meta
        self.logger.warning(
            "[REQUEST ERROR] #%d %s — %s",
            meta["pokemon_if_id"],
            meta["pokemon_name_en"],
            failure.value,
        )

    # ── Main dispatcher ───────────────────────────────────────────────────────

    def parse_all(self, response):
        if response.status == 404:
            self.logger.warning(
                "[404] #%d %s — %s",
                response.meta["pokemon_if_id"],
                response.meta["pokemon_name_en"],
                response.url,
            )
            return

        entries = response.meta.get(
            "pokemon_entries",
            [(response.meta["pokemon_if_id"], response.meta["pokemon_name_en"])],
        )
        self.logger.info(
            "[PARSE] %s → %s",
            response.meta["pokemon_name_en"],
            ", ".join(f"#{i}" for i, _ in entries),
        )

        # Parse the page once, then fan the items out to every IF id sharing
        # it (alternate forms). Approximation: forms inherit the same moveset —
        # per-form tables (e.g. Lycanroc Midday vs Midnight) are not split.
        items = [
            *self.parse_level_up(response),
            *self.parse_ct(response),
            *self.parse_breeding(response),
            *self.parse_tutor(response),
        ]
        for if_id, _name in entries:
            for item in items:
                yield MovesetItem({**dict(item), "pokemon_if_id": if_id})

    # ── Level-up moves (USUL column) ─────────────────────────────────────────

    def parse_level_up(self, response):
        """
        Parse level-up moves targeting the USUL column.
        Table headers: Capacité | Niveau | Nom | Type | Cat. | Puis. | Préc. | PP | SL | USUL | LGPE
        We find the USUL column index and extract only those levels.
        """
        pokemon_if_id = response.meta["pokemon_if_id"]

        header = response.xpath('//*[@id="Par_montée_en_niveau"]')
        if not header:
            return

        table = header.xpath("following::table[1]")
        if not table:
            return

        usul_col = self._find_column_index(table, USUL_PATTERNS)
        if usul_col is None:
            # Single-version table — take the last data column
            col_count = len(table.xpath(".//thead/tr[last()]/th | .//tr[1]/th"))
            usul_col  = col_count if col_count > 0 else 1
            self.logger.debug(
                "[LEVEL_UP] No USUL column found for #%d, using col %d",
                pokemon_if_id, usul_col,
            )

        for row in table.xpath(".//tbody/tr"):
            move_name = row.xpath("./td[1]//a/text() | ./td[1]/text()").get()
            cell      = row.xpath(f"./td[{usul_col}]")

            if not move_name or not cell:
                continue

            for level in self._parse_levels(cell):
                yield MovesetItem(
                    pokemon_if_id=pokemon_if_id,
                    move_name_fr=move_name.strip(),
                    method="level_up",
                    level=level,
                    source="base",
                )

    @staticmethod
    def _find_column_index(table, patterns: list[str]) -> int | None:
        """Return 1-based column index whose header text matches any pattern."""
        # Try all header rows (last may be a button row with no th)
        for header_xpath in [
            ".//thead/tr[last()]/th",
            ".//thead/tr[last()-1]/th",
            ".//thead/tr[2]/th",
            ".//thead/tr[1]/th",
            ".//tr[1]/th",
        ]:
            headers = table.xpath(header_xpath)
            if not headers:
                continue
            for idx, header in enumerate(headers, start=1):
                text = " ".join(header.xpath(".//text()").getall()).strip()
                if any(p.lower() in text.lower() for p in patterns):
                    return idx

        return None

    @staticmethod
    def _parse_levels(cell) -> list[int]:
        """
        Parse learning levels from a table cell.
        'Départ'   → level 0  (known from start)
        'Évolution' → level -1
        'N.xx'     → integer level
        '—' or '-' → skip (not learned in this version)
        """
        levels = []
        for raw in cell.xpath(".//text()").getall():
            text = raw.strip()
            if not text or text in ("—", "-", "–"):
                continue
            if text == "Départ":
                levels.append(0)
            elif text == "Évolution":
                levels.append(-1)
            else:
                m = LEVEL_RE.search(text)
                if m:
                    levels.append(int(m.group(1)))
        return levels

    # ── CT/TM moves (USUL subsection) ────────────────────────────────────────

    def parse_ct(self, response):
        """
        Parse CT moves from the USUL subsection only.

        Section structure:
          == Par CT ==               ← id="Par_CT"
          === SL et USUL ===         ← h4 we target
            [table]
          === LGPE ===               ← h4 we skip
            [table]

        CT table columns: Numéro | Capacité | Type | Cat. | Puis. | Préc. | PP
        Move name is in column 2 (index 2).
        """
        pokemon_if_id = response.meta["pokemon_if_id"]

        header = response.xpath('//*[@id="Par_CT"]')
        if not header:
            return

        # Find the first h4 subsection matching USUL patterns
        usul_h4 = None
        for h4 in header.xpath("following::h4"):
            text = " ".join(h4.xpath(".//text()").getall()).strip()
            if any(p.lower() in text.lower() for p in CT_USUL_PATTERNS):
                usul_h4 = h4
                break

        if usul_h4 is not None:
            table = usul_h4.xpath("following::table[1]")
        else:
            # No subsections — single unified CT table (older page format)
            table = header.xpath("following::table[1]")

        if not table:
            return

        for row in table.xpath(".//tbody/tr"):
            # Column 2 = move name (column 1 = CT number)
            move_name = row.xpath("./td[2]//a/text() | ./td[2]/text()").get()
            if not move_name:
                continue

            yield MovesetItem(
                pokemon_if_id=pokemon_if_id,
                move_name_fr=move_name.strip(),
                method="tm",
                level=None,
                source="base",
            )

    # ── Breeding moves — ALL Pokémon ─────────────────────────────────────────

    def parse_breeding(self, response):
        """
        Parse breeding (egg) moves for ALL Pokémon.
        Section id: Par_reproduction
        Columns: Capacité | Type | Cat. | Puis. | Préc. | PP | Parents (level) | Parents (breeding)
        Move name is in column 1.
        """
        pokemon_if_id = response.meta["pokemon_if_id"]

        header = response.xpath('//*[@id="Par_reproduction"]')
        if not header:
            return   # Pokémon with no egg moves (legendaries, etc.)

        table = header.xpath("following::table[1]")
        if not table:
            return

        for row in table.xpath(".//tbody/tr"):
            move_name = row.xpath("./td[1]//a/text() | ./td[1]/text()").get()
            if not move_name:
                continue

            yield MovesetItem(
                pokemon_if_id=pokemon_if_id,
                move_name_fr=move_name.strip(),
                method="breeding",
                level=None,
                source="base",
            )

    # ── Move tutor — ALL Pokémon ─────────────────────────────────────────────

    def parse_tutor(self, response):
        """
        Parse move tutor moves for ALL Pokémon.
        Section id: Par_donneur_de_capacités
        Columns: Capacité | Type | Cat. | Puis. | Préc. | PP | Lieu | Coût
        Move name is in column 1.

        Note: unlike predictiondex which only scraped tutors for starters (LGPE-specific),
        Gen 7 USUL has tutors available to many Pokémon across the game.
        """
        pokemon_if_id = response.meta["pokemon_if_id"]

        header = response.xpath('//*[@id="Par_donneur_de_capacités"]')
        if not header:
            return

        table = header.xpath("following::table[1]")
        if not table:
            return

        for row in table.xpath(".//tbody/tr"):
            move_name = row.xpath("./td[1]//a/text() | ./td[1]/text()").get()
            if not move_name:
                continue

            yield MovesetItem(
                pokemon_if_id=pokemon_if_id,
                move_name_fr=move_name.strip(),
                method="tutor",
                level=None,
                source="base",
            )
