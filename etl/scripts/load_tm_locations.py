"""Script ETL — peuple `tm_location` depuis le wiki IF.

Source : https://infinitefusion.fandom.com/wiki/List_of_TMs (section TMs).

Ce script :
  1. Parse la table wiki (122 lignes, TM00 à TM121)
  2. Résout chaque location vers `location.id` (avec alias + création si absent)
  3. Repopule `tm_location` (TRUNCATE + INSERT)

Le résumé texte `location_summary` n'est plus stocké en base — il est calculé
à la volée par le backend depuis les lignes `tm_location`.

Idempotent.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging
from etl.utils.wikitext import fetch_wikitext

LOGGER = setup_logging(__name__)

WIKI_PAGE = "List_of_TMs"


# ─── Mapping des locations du wiki vers location.name_en ─────────────────────
#
# Les sous-lieux sont mappés au parent city, le sous-lieu devient une "note".
# Exemple : "[[Celadon City|Celadon Dept. Store]]" → location=Celadon City,
# notes="Celadon Dept. Store".
LOCATION_ALIASES: dict[str, str] = {
    # Sous-lieux de Celadon City
    "Celadon Dept. Store": "Celadon City",
    "Game Corner":         "Celadon City",
    "Celadon Sewers":      "Celadon City",
    # Sous-lieux de Saffron City
    "Silph Co.":           "Saffron City",
    # Sous-lieux de Lavender Town
    "Pokémon Tower":       "Lavender Town",
}

# Locations à créer si absentes en DB (noms tirés du wiki).
LOCATIONS_TO_ENSURE: list[tuple[str, str | None]] = [
    # Villes/routes principales manquantes
    ("Viridian City",              "Kanto"),
    ("Ecruteak City",              "Johto"),
    ("Route 25",                   "Kanto"),
    # Sous-zones / bâtiments standalone
    ("S.S. Anne",                  "Kanto"),
    ("Underground Paths",          "Kanto"),
    ("Cycling Road",               "Kanto"),
    ("Ember Spa",                  "Other"),
    ("Outside Mt. Moon",           "Kanto"),
    ("Mahogany Gym",               "Johto"),
    ("Name Rater",                 "Johto"),
    ("Safari Zone Area 1",         "Kanto"),
    ("Safari Zone Area 3",         "Kanto"),
    ("Safari Zone Area 5",         "Kanto"),
    ("Safari Zone Area 5 Temple",  "Kanto"),
    ("Azalea Town",                "Johto"),
    ("Battle Factory and Battle Tower", "Other"),
]


# ─── Parseurs ────────────────────────────────────────────────────────────────

@dataclass
class TMEntry:
    number: int
    move_name: str
    locations: list[tuple[str, str | None]] = field(default_factory=list)
    # summary: raw location cell cleaned of wiki markup, for tm.location TEXT
    summary: str = ""


_TM_RE       = re.compile(r"^TM(\d+)$")
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_PARENS_RE   = re.compile(r"^\s*\(([^)]+)\)")
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _extract_move_name(cell: str) -> str:
    """Return the display text of the first wikilink, stripping ' (move)' suffix."""
    m = _WIKILINK_RE.search(cell)
    if not m:
        return cell.strip()
    link = m.group(1)
    display = link.split("|", 1)[-1] if "|" in link else link
    return re.sub(r"\s*\(move\)\s*$", "", display, flags=re.IGNORECASE).strip()


def _parse_location_cell(cell: str) -> tuple[list[tuple[str, str | None]], str]:
    """Parse a location cell into (locations_list, summary_text).

    Returns:
        locations_list: list of (wiki_display_name, trailing_paren_context)
        summary_text:   human-readable cleaned string (replaces tm.location)

    Example input :
        "[[Celadon City|Celadon Dept. Store]], [[Route 32]]"
    Returns :
        ([("Celadon Dept. Store", None), ("Route 32", None)],
         "Celadon Dept. Store, Route 32")

    Example input :
        "[[Celadon City|Game Corner]], [[Quests|Celadon City]] (Team Rocket mission)"
    Returns :
        ([("Game Corner", None), ("Celadon City", "Team Rocket mission")],
         "Game Corner, Celadon City (Team Rocket mission)")
    """
    # We walk the cell from left to right, collecting segments. Splitting on
    # comma naively breaks on commas INSIDE wikilinks — but luckily IF wiki
    # doesn't do that, so a simple split works.
    segments = [s.strip() for s in cell.split(",") if s.strip()]

    parsed: list[tuple[str, str | None]] = []
    summary_parts: list[str] = []
    for seg in segments:
        m = _WIKILINK_RE.search(seg)
        if not m:
            LOGGER.debug("Segment sans wikilink, ignoré : %r", seg)
            continue
        link = m.group(1)
        display = link.split("|", 1)[-1] if "|" in link else link
        display = display.strip()

        # Trailing "(...)" after the wikilink, if any
        trailing = seg[m.end():].strip()
        paren_m = _PARENS_RE.match(trailing)
        context = paren_m.group(1).strip() if paren_m else None

        parsed.append((display, context))
        if context:
            summary_parts.append(f"{display} ({context})")
        else:
            summary_parts.append(display)

    return parsed, ", ".join(summary_parts)


def _is_data_row(block: str) -> bool:
    """Return True if the block begins with `|TM<number>` (data row)."""
    first = next((l.strip() for l in block.splitlines() if l.strip()), "")
    if not first.startswith("|"):
        return False
    head = first.lstrip("|").strip()
    return bool(_TM_RE.match(head))


def parse_tm_table(wikitext: str) -> list[TMEntry]:
    """Extract TM entries from the 'TMs' section of the wikitext."""
    sec = re.search(r"==\s*TMs\s*==(.*?)(?===|\Z)", wikitext, re.DOTALL)
    if not sec:
        raise RuntimeError("Section '== TMs ==' introuvable dans le wikitext")
    body = sec.group(1)

    blocks = re.split(r"^\s*\|-\s*$", body, flags=re.MULTILINE)
    entries: list[TMEntry] = []
    for block in blocks:
        if not _is_data_row(block):
            continue
        lines = [l for l in block.splitlines() if l.strip().startswith("|")]
        cells = [l.lstrip("|").strip() for l in lines]
        if len(cells) < 3:
            continue
        tm_cell, move_cell, loc_cell = cells[:3]
        tm_m = _TM_RE.match(tm_cell)
        if not tm_m:
            continue
        number = int(tm_m.group(1))
        move_name = _extract_move_name(move_cell)
        locations, summary = _parse_location_cell(loc_cell)
        entries.append(TMEntry(
            number=number,
            move_name=move_name,
            locations=locations,
            summary=summary,
        ))
    return entries


# ─── Résolution DB ───────────────────────────────────────────────────────────

def ensure_location(cur, name_en: str, region: str | None) -> int:
    cur.execute("SELECT id FROM location WHERE name_en = %s", (name_en,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO location (name_en, region) VALUES (%s, %s) RETURNING id",
        (name_en, region),
    )
    new_id = cur.fetchone()[0]
    LOGGER.info("  + Location créée : %s (id=%d)", name_en, new_id)
    return new_id


def load_tm_number_index(cur) -> dict[int, int]:
    """Return {tm_number: tm.id}."""
    cur.execute("SELECT id, number FROM tm")
    return {num: tm_id for tm_id, num in cur.fetchall()}


def load_location_index(cur) -> dict[str, int]:
    cur.execute("SELECT id, name_en FROM location")
    return {name: lid for lid, name in cur.fetchall()}


# ─── Main ────────────────────────────────────────────────────────────────────

def run(conn) -> None:
    cur = conn.cursor()

    # Créer les locations manquantes avant de charger l'index
    for name, region in LOCATIONS_TO_ENSURE:
        ensure_location(cur, name, region)

    tm_idx  = load_tm_number_index(cur)
    loc_idx = load_location_index(cur)
    LOGGER.info("DB : %d TMs, %d locations chargés", len(tm_idx), len(loc_idx))

    wikitext = fetch_wikitext(WIKI_PAGE)
    LOGGER.info("Wiki : %d caractères récupérés", len(wikitext))

    entries = parse_tm_table(wikitext)
    LOGGER.info("Wiki : %d TMs parsés", len(entries))

    # Purge complète de tm_location avant ré-insertion
    cur.execute("TRUNCATE tm_location RESTART IDENTITY")

    inserted_rows  = 0
    unresolved_tm: list[int] = []
    unresolved_loc: set[str] = set()

    for entry in entries:
        tm_id = tm_idx.get(entry.number)
        if tm_id is None:
            unresolved_tm.append(entry.number)
            continue

        for display_name, context in entry.locations:
            canonical = LOCATION_ALIASES.get(display_name, display_name)
            location_id = loc_idx.get(canonical)
            if location_id is None:
                unresolved_loc.add(display_name)
                continue

            # Notes = sous-lieu (si aliasé) éventuellement enrichi du contexte
            notes_parts: list[str] = []
            if canonical != display_name:
                notes_parts.append(display_name)
            if context:
                notes_parts.append(context)
            notes = " – ".join(notes_parts) if notes_parts else None

            cur.execute(
                """
                INSERT INTO tm_location (tm_id, location_id, notes)
                VALUES (%s, %s, %s)
                ON CONFLICT (tm_id, location_id, notes) DO NOTHING
                """,
                (tm_id, location_id, notes),
            )
            inserted_rows += 1

    conn.commit()
    cur.close()

    if unresolved_tm:
        LOGGER.warning("TMs wiki absents en DB : %s", sorted(unresolved_tm))
    if unresolved_loc:
        LOGGER.warning("Locations non résolues : %s", sorted(unresolved_loc))

    LOGGER.info("Terminé — %d lignes insérées dans tm_location",
                inserted_rows)


def main() -> None:
    with pg_connection() as conn:
        run(conn)


if __name__ == "__main__":
    sys.exit(main() or 0)
