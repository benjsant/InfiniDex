"""
ETL Step 3 — Extract moves, TMs and tutors from the Infinite Fusion wiki.

Sources (MediaWiki API):
  - List_of_Moves  → moves EN: name, type, category, power, accuracy, PP, description
  - List_of_TMs    → CTs: number, move name, location in IF
  - List_of_Tutors → tutor moves: name, location, price

FR names: filled in later via Pokepedia (movesets_base.json holds name_fr).
          load_db.py joins move.name_en ↔ moveset.move_name_fr through an
          inverted mapping built from the movesets.

Output: data/moves_if.json, data/tms_if.json, data/tutors_if.json
"""

from __future__ import annotations

import re
from pathlib import Path

from etl.utils.io import save_json
from etl.utils.logging import setup_logging
from etl.utils.wikitext import clean_wikitext, fetch_wikitext

LOGGER = setup_logging(__name__)

OUT_MOVES         = Path("data/moves_if.json")
OUT_TMS           = Path("data/tms_if.json")
OUT_TUTORS        = Path("data/tutors_if.json")
OUT_EXPERT_TUTORS = Path("data/expert_tutors_if.json")

# Section headers: ==Bug-type== or ==Bug-type moves==
TYPE_HEADER_RE = re.compile(r"^==\s*([A-Za-z]+(?:/[A-Za-z]+)?)-type(?:\s+moves)?\s*==$", re.MULTILINE)

# Row separator
ROW_SEP_RE = re.compile(r"^\|-", re.MULTILINE)

SORTVAL_RE    = re.compile(r'data-sort-value="([^"]*)"')


def clean(text: str) -> str:
    return clean_wikitext(text, strip_templates=True)


def parse_cell(raw: str) -> str:
    """Extract display value from a wiki table cell (handles data-sort-value)."""
    raw = raw.strip().lstrip("|").strip()
    # data-sort-value="90" | 90  → take the bare value after |
    if "|" in raw:
        raw = raw.split("|", 1)[-1].strip()
    return clean(raw)


def parse_int_or_none(value: str) -> int | None:
    v = parse_cell(value).strip("-— %")
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


# ─── Moves ────────────────────────────────────────────────────────────────────

def extract_moves(wikitext: str) -> list[dict]:
    """
    Parse ==Type-type== sections, each containing a wikitable of moves.
    Columns: Move | Category | Power | Accuracy | PP | Description
    """
    moves: list[dict] = []
    seen: set[str]    = set()

    # Split on type headers
    parts = TYPE_HEADER_RE.split(wikitext)
    # parts[0] = preamble, then alternating: type_name, content_block, ...

    for i in range(1, len(parts), 2):
        type_en      = parts[i].capitalize()
        block        = parts[i + 1] if i + 1 < len(parts) else ""

        # Split block into rows on "|-"
        rows = ROW_SEP_RE.split(block)

        for row in rows[1:]:   # skip table header
            lines = [l.strip() for l in row.strip().splitlines() if l.strip()]
            # Filter out header lines (starting with !) and row attributes
            cells = [l for l in lines if l.startswith("|") and not l.startswith("|-")]

            if len(cells) < 6:
                continue

            # Cell 0 : move name
            # May be:  | data-sort-value="Bug Bite" | [[bulbapedia:...|Bug Bite]]
            # Or:      | [[...|Bug Bite]]
            name_cell = cells[0].lstrip("|").strip()
            # Try data-sort-value first (most reliable)
            m = SORTVAL_RE.search(name_cell)
            if m:
                name = m.group(1).strip()
            else:
                name = clean(name_cell)

            if not name or name.startswith("{") or not name[0].isalpha():
                continue

            if name in seen:
                continue
            seen.add(name)

            category    = parse_cell(cells[1]).capitalize()
            power       = parse_int_or_none(cells[2])
            accuracy    = parse_int_or_none(cells[3])
            pp          = parse_int_or_none(cells[4]) or 1
            description = parse_cell(cells[5]) if len(cells) > 5 else ""

            moves.append({
                "name_en":        name,
                "name_fr":        None,
                "type_en":        type_en,
                "category":       category if category in ("Physical", "Special", "Status") else "Status",
                "power":          power,
                "accuracy":       accuracy,
                "pp":             pp,
                "description_en": description,
                "description_fr": None,
                "source":         "base",
            })

    LOGGER.info("Parsed %d moves", len(moves))
    return moves


# ─── TMs ──────────────────────────────────────────────────────────────────────

# | TM01 | [[bulbapedia:...|Work Up]] | Location
TM_ROW_RE = re.compile(
    r"\|\s*TM(?P<number>\d+)\s*\|[^\|]*?\|\s*"
    r"(?:data-sort-value=\"[^\"]*\"\s*\|)?\s*"
    r"(?:\[\[(?:[^\]|]*\|)?)?(?P<move>[A-Za-z][^\|\]\n]{1,40})(?:\]\])?\s*\|"
    r"\s*(?P<location>[^\|\n]+)",
    re.IGNORECASE,
)

def extract_tms(wikitext: str) -> list[dict]:
    tms: list[dict] = []
    seen: set[int]  = set()

    for m in TM_ROW_RE.finditer(wikitext):
        number = int(m.group("number"))
        if number in seen:
            continue
        seen.add(number)
        tms.append({
            "number":    number,
            "move_name": clean(m.group("move")),
            "location":  clean(m.group("location")),
        })

    tms.sort(key=lambda x: x["number"])
    LOGGER.info("Parsed %d TMs", len(tms))
    return tms


# ─── Tutors ───────────────────────────────────────────────────────────────────

# Non-move entries to skip from the tutor table
TUTOR_SKIP = {"Move Teacher", "Move Deleter", "Egg Moves"}


def extract_tutors(wikitext: str) -> list[dict]:
    """
    Parse the List_of_Tutors table.
    Format per row:
      |-
      |[[bulbapedia:Move Name (move)|Move Name]]  (or bare text)
      |Location
      |Additional info
      |Price
    """
    tutors: list[dict] = []
    seen: set[str]     = set()

    rows = re.split(r"\n\|-", wikitext)
    for row in rows[1:]:   # skip table header row
        lines = [l.strip() for l in row.strip().splitlines() if l.strip()]
        cells = [l.lstrip("|").strip() for l in lines if l.startswith("|") and not l.startswith("|-") and not l.startswith("!")]
        if len(cells) < 2:
            continue
        name     = clean(cells[0])
        location = clean(cells[1])
        if not name or name in TUTOR_SKIP or name in seen:
            continue
        # Skip generic entries that contain spaces in suspicious patterns
        if name.startswith("{{") or not name[0].isalpha():
            continue
        seen.add(name)
        tutors.append({
            "move_name": name,
            "location":  location,
        })

    LOGGER.info("Parsed %d tutor moves", len(tutors))
    return tutors


# ─── Move Expert Tutors ───────────────────────────────────────────────────────

def extract_expert_tutors(wikitext: str) -> list[dict]:
    """
    Parse List_of_Move_Expert_Moves — two tables:
      == Move Expert (Knot Island) ==   → location: 'Knot Island (Move Expert)'
      == Legendary Move Expert (Boon Island) == → location: 'Boon Island (Legendary Move Expert)'

    Only extract move names (first column).  rowspan continuation rows contain
    Pokémon/type lists — filtered out by checking for commas or single words
    that are not move names.
    """
    expert_tutors: list[dict] = []
    seen: set[str]            = set()

    # Split on == section headers to get location context
    sections = re.split(r"==+\s*", wikitext)
    current_location: str = ""

    for section in sections:
        if section.startswith("Move Expert (Knot Island)"):
            current_location = "Knot Island (Move Expert)"
        elif "Legendary Move Expert" in section or "Boon Island" in section:
            current_location = "Boon Island (Legendary Move Expert)"

        if not current_location:
            continue

        rows = re.split(r"\n\|-", section)
        for row in rows[1:]:
            lines = [l.strip() for l in row.splitlines() if l.strip()]
            cells = [l.lstrip("|").strip() for l in lines
                     if l.startswith("|") and not l.startswith("|-") and not l.startswith("!")]
            if not cells:
                continue

            # Remove rowspan prefix: rowspan="2" | Move Name
            raw = re.sub(r'rowspan="\d+"\s*\|\s*', "", cells[0]).strip()
            name = clean(raw)

            # Skip: empty, dashes, Pokémon lists (contain commas), single bare words that aren't moves
            if not name or name == "-" or "," in name:
                continue
            if not name[0].isupper():
                continue
            if name in seen:
                continue

            seen.add(name)
            expert_tutors.append({
                "move_name": name,
                "location":  current_location,
            })

    LOGGER.info("Parsed %d expert tutor moves", len(expert_tutors))
    return expert_tutors


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    LOGGER.info("Fetching List of Moves from IF wiki...")
    moves = extract_moves(fetch_wikitext("List_of_Moves"))
    save_json(OUT_MOVES, moves)
    LOGGER.info("Saved %d moves → %s", len(moves), OUT_MOVES)

    LOGGER.info("Fetching List of TMs from IF wiki...")
    tms = extract_tms(fetch_wikitext("List_of_TMs"))
    save_json(OUT_TMS, tms)
    LOGGER.info("Saved %d TMs → %s", len(tms), OUT_TMS)

    LOGGER.info("Fetching List of Tutors from IF wiki...")
    try:
        tutors = extract_tutors(fetch_wikitext("List_of_Tutors"))
    except Exception:
        tutors = []
        LOGGER.warning("List of Tutors unavailable — skipped")
    save_json(OUT_TUTORS, tutors)
    LOGGER.info("Saved %d tutors → %s", len(tutors), OUT_TUTORS)

    LOGGER.info("Fetching List of Move Expert Moves from IF wiki...")
    try:
        expert_tutors = extract_expert_tutors(fetch_wikitext("List_of_Move_Expert_Moves"))
    except Exception:
        expert_tutors = []
        LOGGER.warning("List_of_Move_Expert_Moves unavailable — skipped")
    save_json(OUT_EXPERT_TUTORS, expert_tutors)
    LOGGER.info("Saved %d expert tutor moves → %s", len(expert_tutors), OUT_EXPERT_TUTORS)


if __name__ == "__main__":
    main()
