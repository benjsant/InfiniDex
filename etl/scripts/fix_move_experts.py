"""
Script ETL — peuple la table `move_expert_move`.

Les Move Experts d'Infinite Fusion (Knot Island et Boon Island) enseignent des
signature moves de Pokémon absents du jeu, mais UNIQUEMENT aux fusions qui
satisfont des conditions précises. Exemple : une fusion tête-Noctali peut
apprendre « Parting Shot » grâce au Move Expert de Knot Island.

Source : https://infinitefusion.fandom.com/wiki/List_of_Move_Expert_Moves

Format du wiki :
  Chaque move occupe UNE cellule avec éventuellement `rowspan="N"` si plusieurs
  combinaisons de prérequis existent (OR entre les lignes). Dans une ligne, les
  trois colonnes suivantes forment une conjonction (AND) :
    - Required Fusions : liste de Pokémon (OR) — head OU body doit matcher
    - Required Type(s) : 1+ types — la fusion doit TOUS les avoir (AND)
    - Must learn one of these moves : liste de moves (OR)
  Un "- " dans une colonne = pas de contrainte sur cet axe.

Idempotent : purge et réinsère les lignes de `move_expert_move` à chaque run.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

import requests

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

WIKI_API = "https://infinitefusion.fandom.com/api.php"
WIKI_UA  = "InfiniDexETL/1.0 (github.com/benjsant/InfiniDex-IA)"
WIKI_PAGE = "List_of_Move_Expert_Moves"


# ─── Helpers de normalisation ─────────────────────────────────────────────────

_NORM_STRIP = str.maketrans("", "", "-.' ")

# Corrections de coquilles du wiki (clé = nom normalisé côté wiki)
WIKI_POKEMON_ALIASES: dict[str, str] = {
    "flaafy": "flaaffy",  # wiki IF orthographie « Flaafy » (1 f)
}


def norm(s: str) -> str:
    """Normalise un nom pour comparaison (case-insensitive, sans ponctuation).

        "Porygon-Z"  → "porygonz"
        "PorygonZ"   → "porygonz"
        "Farfetch'd" → "farfetchd"
        "Ho-oh"      → "hooh"
    """
    return s.lower().translate(_NORM_STRIP)


def norm_pokemon(s: str) -> str:
    """Normalise + applique les alias de coquille du wiki."""
    n = norm(s)
    return WIKI_POKEMON_ALIASES.get(n, n)


# ─── Parseur du wiki ──────────────────────────────────────────────────────────

@dataclass
class ExpertRow:
    """Une alternative (ligne) pour un move enseigné par un expert."""
    move_name: str
    location: str                   # 'knot_island' | 'boon_island'
    pokemon_names: list[str] = field(default_factory=list)  # OR entre eux
    type_names:    list[str] = field(default_factory=list)  # AND entre eux
    move_names:    list[str] = field(default_factory=list)  # OR entre eux (learn ≥1)


MOVE_LINK_RE = re.compile(r"\[\[bulbapedia:[^|\]]+\|(?P<name>[^\]]+)\]\]")
ROWSPAN_RE   = re.compile(r'rowspan="(\d+)"', re.IGNORECASE)


def fetch_wikitext() -> str:
    resp = requests.get(
        WIKI_API,
        params={
            "action": "parse",
            "page":   WIKI_PAGE,
            "prop":   "wikitext",
            "format": "json",
        },
        headers={"User-Agent": WIKI_UA},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["parse"]["wikitext"]["*"]


def parse_cell(raw: str) -> str:
    """Extrait la valeur d'une cellule de tableau (sans le leading `|`)."""
    s = raw.strip()
    # Retire un éventuel prefix `rowspan="N" |` / `colspan="N" |` / `attr | `
    # Format : `rowspan="2" | [[...]]` ou `[[...]]`
    if "|" in s:
        # On ne split qu'une fois : le premier `|` sépare attrs et contenu.
        # Mais attention aux `|` internes de wikilinks `[[x|y]]` → on split
        # uniquement si la portion avant `|` ressemble à un attribut HTML.
        head, _, tail = s.partition("|")
        if re.fullmatch(r'\s*(?:rowspan|colspan|style|class)="[^"]*"\s*', head):
            s = tail.strip()
    # Cellule "vide" : un simple "-"
    if s == "-":
        return ""
    return s


def parse_pokemon_list(cell: str) -> list[str]:
    if not cell:
        return []
    return [p.strip() for p in cell.split(",") if p.strip()]


def parse_type_list(cell: str) -> list[str]:
    """Split sur ', ' ou ' and ' — la page utilise « Grass and Ghost »."""
    if not cell:
        return []
    # normalise les séparateurs
    parts = re.split(r"\s*,\s*|\s+and\s+", cell)
    return [p.strip() for p in parts if p.strip()]


def parse_move_list(cell: str) -> list[str]:
    """Cellule « Must learn one of these moves » — séparée par virgules."""
    if not cell:
        return []
    return [m.strip() for m in cell.split(",") if m.strip()]


def split_sections(wikitext: str) -> list[tuple[str, str]]:
    """Retourne [(location, table_body), ...] — une entrée par table."""
    sections: list[tuple[str, str]] = []
    for header, loc in (
        ("Move Expert (Knot Island)",            "knot_island"),
        ("Legendary Move Expert (Boon Island)",  "boon_island"),
    ):
        pat = re.compile(
            rf"==\s*{re.escape(header)}\s*==\s*\n(?P<body>.*?)(?=\n==|\Z)",
            re.DOTALL,
        )
        m = pat.search(wikitext)
        if not m:
            LOGGER.warning("Section introuvable : %s", header)
            continue
        sections.append((loc, m.group("body")))
    return sections


def parse_table(body: str, location: str) -> list[ExpertRow]:
    """Parse un tableau et retourne la liste des alternatives (une par ligne)."""
    # Tout le tableau est entre `{| ... |}`
    start = body.find("{|")
    end   = body.find("|}", start)
    if start == -1 or end == -1:
        LOGGER.warning("Tableau introuvable pour %s", location)
        return []
    table = body[start + 2 : end]

    # Découpe en lignes via les séparateurs `|-`
    raw_rows = re.split(r"^\s*\|-\s*$", table, flags=re.MULTILINE)
    # Première « ligne » = headers (`!...`) → on l'écarte
    data_rows = [r for r in raw_rows if r.strip() and not r.strip().startswith("!")]

    out: list[ExpertRow] = []
    # Pour gérer rowspan : quand une cellule « move » couvre N lignes, on la
    # réutilise pour les (N-1) lignes suivantes qui n'ont que 3 colonnes.
    current_move: str | None = None
    move_rows_remaining = 0

    for rr in data_rows:
        # Chaque cellule commence par `|` en début de ligne.
        cells = [c for c in re.split(r"^\s*\|", rr, flags=re.MULTILINE) if c.strip()]
        # `cells` contient soit 4 cellules (nouvelle move) soit 3 (continuation).

        if len(cells) == 4:
            move_cell_raw = cells[0]
            rowspan_m = ROWSPAN_RE.search(move_cell_raw)
            rowspan_n = int(rowspan_m.group(1)) if rowspan_m else 1
            move_cell = parse_cell(move_cell_raw)
            m = MOVE_LINK_RE.search(move_cell)
            if not m:
                LOGGER.debug("Cellule move sans lien bulbapedia, ignorée : %r", move_cell_raw)
                continue
            current_move = m.group("name").strip()
            move_rows_remaining = rowspan_n - 1
            pk_cell, ty_cell, mv_cell = cells[1], cells[2], cells[3]
        elif len(cells) == 3 and move_rows_remaining > 0 and current_move:
            move_rows_remaining -= 1
            pk_cell, ty_cell, mv_cell = cells[0], cells[1], cells[2]
        else:
            LOGGER.debug("Ligne ignorée (%d cellules) : %r", len(cells), rr[:80])
            continue

        row = ExpertRow(
            move_name     = current_move,
            location      = location,
            pokemon_names = parse_pokemon_list(parse_cell(pk_cell)),
            type_names    = parse_type_list(parse_cell(ty_cell)),
            move_names    = parse_move_list(parse_cell(mv_cell)),
        )
        out.append(row)

    return out


# ─── Résolution DB ────────────────────────────────────────────────────────────

def load_pokemon_index(cur) -> dict[str, int]:
    cur.execute("SELECT id, name_en FROM pokemon")
    return {norm(name_en): pid for pid, name_en in cur.fetchall()}


def load_move_index(cur) -> dict[str, int]:
    cur.execute("SELECT id, name_en FROM move")
    return {norm(name_en): mid for mid, name_en in cur.fetchall()}


def load_type_index(cur) -> dict[str, int]:
    cur.execute("SELECT id, name_en FROM type WHERE is_triple_fusion_type = FALSE")
    return {norm(name_en): tid for tid, name_en in cur.fetchall()}


# ─── Main ─────────────────────────────────────────────────────────────────────

def run(conn) -> None:
    cur = conn.cursor()

    pokemon_idx = load_pokemon_index(cur)
    move_idx    = load_move_index(cur)
    type_idx    = load_type_index(cur)

    LOGGER.info("DB : %d Pokémon, %d moves, %d types chargés",
                len(pokemon_idx), len(move_idx), len(type_idx))

    wikitext = fetch_wikitext()
    LOGGER.info("Wiki : %d caractères récupérés", len(wikitext))

    all_rows: list[ExpertRow] = []
    for location, body in split_sections(wikitext):
        rows = parse_table(body, location)
        LOGGER.info("  %s : %d alternatives parsées", location, len(rows))
        all_rows.extend(rows)

    # Résolution → IDs
    inserts: list[tuple[int, str, list[int], list[int], list[int]]] = []
    unresolved_moves:    set[str] = set()
    unresolved_pokemon:  set[str] = set()
    unresolved_types:    set[str] = set()
    unresolved_premoves: set[str] = set()

    for row in all_rows:
        mid = move_idx.get(norm(row.move_name))
        if mid is None:
            unresolved_moves.add(row.move_name)
            continue

        pk_ids: list[int] = []
        for name in row.pokemon_names:
            pid = pokemon_idx.get(norm_pokemon(name))
            if pid is None:
                unresolved_pokemon.add(name)
            else:
                pk_ids.append(pid)

        ty_ids: list[int] = []
        for name in row.type_names:
            tid = type_idx.get(norm(name))
            if tid is None:
                unresolved_types.add(name)
            else:
                ty_ids.append(tid)

        mv_ids: list[int] = []
        for name in row.move_names:
            pre_mid = move_idx.get(norm(name))
            if pre_mid is None:
                unresolved_premoves.add(name)
            else:
                mv_ids.append(pre_mid)

        inserts.append((mid, row.location, pk_ids, ty_ids, mv_ids))

    if unresolved_moves:
        LOGGER.warning("Moves inconnus (ignorés) : %s", sorted(unresolved_moves))
    if unresolved_pokemon:
        LOGGER.warning("Pokémon inconnus : %s", sorted(unresolved_pokemon))
    if unresolved_types:
        LOGGER.warning("Types inconnus : %s", sorted(unresolved_types))
    if unresolved_premoves:
        LOGGER.warning("Prerequis moves inconnus : %s", sorted(unresolved_premoves))

    # Purge et réinsertion (idempotent)
    cur.execute("TRUNCATE move_expert_move RESTART IDENTITY")
    for mid, loc, pk_ids, ty_ids, mv_ids in inserts:
        cur.execute(
            """
            INSERT INTO move_expert_move
                (move_id, expert_location, required_pokemon_ids,
                 required_type_ids, required_move_ids)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (mid, loc, pk_ids, ty_ids, mv_ids),
        )

    conn.commit()
    cur.close()
    LOGGER.info("Terminé — %d lignes insérées dans move_expert_move",
                len(inserts))


def main() -> None:
    with pg_connection() as conn:
        run(conn)


if __name__ == "__main__":
    sys.exit(main() or 0)
