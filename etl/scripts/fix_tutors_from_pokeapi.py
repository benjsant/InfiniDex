"""
Script de correction — complète les moves de Move Tutor Infinite Fusion.

Même règle que pour les CT (cf. fix_tms_from_pokeapi.py) : un Pokémon peut
apprendre un move par tutor IF s'il l'apprend par *n'importe quelle* méthode
officielle (niveau, CT, tuteur, œuf) ou via héritage pré-évolution.

Trois lignes du wiki sont ignorées car ce ne sont pas de vrais moves :
  - "Move Teacher" (Move Reminder) : rappelle des moves déjà dans le learnset
  - "Move Deleter" : efface des moves
  - "Egg Moves" : emplacement pour ré-apprendre les moves œuf (déjà capturés
    en méthode `breeding`)

La page Move Expert est traitée à part (liste_Move_Expert_Moves), car ces
moves ne sont apprenables que sur des fusions sous conditions.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict

import requests

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

WIKI_API = "https://infinitefusion.fandom.com/api.php"
WIKI_UA  = "InfiniDexETL/1.0 (github.com/benjsant/InfiniDex-IA)"
POKEAPI  = "https://pokeapi.co/api/v2"
DELAY    = 0.1

SKIP_NAMES: set[str] = {
    "Move Teacher",
    "Move Reminder",
    "Move Deleter",
    "Egg Moves",
}


# ─── Step 1 — Parse tutor list ────────────────────────────────────────────────

# Lignes de la forme :
#   |[[bulbapedia:NAME_LINK|DISPLAY_NAME]]
# ou :
#   |[https://bulbapedia.../NAME DISPLAY_NAME]
# On capture DISPLAY_NAME, puis on filtre via SKIP_NAMES.
TUTOR_BULBA_WIKI = re.compile(
    r"\|\s*\[\[bulbapedia:[^|\]]+\|(?P<name>[^\]]+)\]\]"
)
TUTOR_BULBA_EXTLINK = re.compile(
    r"\|\s*\[https?://bulbapedia\.bulbagarden\.net/wiki/[^\s]+\s+(?P<name>[^\]]+)\]"
)


def fetch_tutor_names() -> list[str]:
    resp = requests.get(
        WIKI_API,
        params={
            "action": "parse",
            "page":   "List_of_Tutors",
            "prop":   "wikitext",
            "format": "json",
        },
        headers={"User-Agent": WIKI_UA},
        timeout=20,
    )
    resp.raise_for_status()
    wikitext = resp.json()["parse"]["wikitext"]["*"]

    # Only capture the FIRST cell of each table row (which is the move name).
    # The wiki table uses row separators "|-" and columns separated by "|".
    # A naive extract of any bulbapedia link would also catch "Location" cells
    # that happen to link to a move (rare). We therefore restrict to lines
    # starting with "|[[bulbapedia:" or "|[https://bulbapedia".
    names: set[str] = set()
    for line in wikitext.splitlines():
        stripped = line.strip()
        m = TUTOR_BULBA_WIKI.match(stripped) or TUTOR_BULBA_EXTLINK.match(stripped)
        if not m:
            continue
        name = m.group("name").strip()
        if name in SKIP_NAMES:
            continue
        names.add(name)

    names_sorted = sorted(names)
    LOGGER.info("Wiki IF : %d moves distincts listés comme tutors", len(names_sorted))
    return names_sorted


# ─── Step 2 — PokeAPI helpers (copiés de fix_tms_from_pokeapi) ────────────────

def pokeapi_move_slug(name_en: str) -> str:
    return (
        name_en.lower()
        .replace("'", "")
        .replace(".", "")
        .replace(" ", "-")
    )


def fetch_move_detail(name_en: str) -> tuple[bool, list[str]] | None:
    """Retourne (is_official_tutor_or_tm, pokemon_slugs). On considère `base`
    tout move qui apparaît officiellement dans les machines ou dans les
    move_learn_methods ≠ level-up (i.e. non exclusif IF)."""
    slug = pokeapi_move_slug(name_en)
    try:
        r = requests.get(f"{POKEAPI}/move/{slug}", timeout=15)
    except requests.RequestException as e:
        LOGGER.warning("PokeAPI erreur (%s) : %s", slug, e)
        return None
    if r.status_code != 200:
        LOGGER.warning("PokeAPI 404 pour move %s (slug=%s)", name_en, slug)
        return None
    data = r.json()
    # `machines` non vide = TM/HM dans un jeu officiel
    is_official = bool(data.get("machines"))
    learners = [p["name"] for p in data.get("learned_by_pokemon", [])]
    return is_official, learners


# ─── Step 3 — DB helpers ──────────────────────────────────────────────────────

def load_move_ids(cur, names: list[str]) -> dict[str, int]:
    cur.execute("SELECT id, name_en FROM move WHERE name_en = ANY(%s)", (names,))
    return {name: mid for mid, name in cur.fetchall()}


def load_pokemon_ids(cur) -> dict[str, int]:
    cur.execute("SELECT id, name_en FROM pokemon")
    return {pokeapi_move_slug(name_en): pid for pid, name_en in cur.fetchall()}


def load_evolution_forward(cur) -> dict[int, list[int]]:
    cur.execute("SELECT pokemon_id, evolves_into_id FROM pokemon_evolution")
    out: dict[int, list[int]] = defaultdict(list)
    for src, tgt in cur.fetchall():
        out[src].append(tgt)
    return out


def all_descendants(start: int, edges: dict[int, list[int]]) -> set[int]:
    seen: set[int] = set()
    queue = list(edges.get(start, []))
    while queue:
        nxt = queue.pop()
        if nxt in seen:
            continue
        seen.add(nxt)
        queue.extend(edges.get(nxt, []))
    return seen


# ─── Step 4 — Main pipeline ───────────────────────────────────────────────────

def run(conn) -> None:
    cur = conn.cursor()

    names = fetch_tutor_names()
    move_ids = load_move_ids(cur, names)
    LOGGER.info("Moves trouvés en base : %d / %d", len(move_ids), len(names))
    missing = set(names) - set(move_ids)
    if missing:
        LOGGER.warning("Moves tutor IF absents de la table `move` (ignorés) : %s",
                       sorted(missing))

    pokemon_ids = load_pokemon_ids(cur)
    evolutions  = load_evolution_forward(cur)

    inserted = 0
    skipped  = 0

    for name_en, move_id in move_ids.items():
        detail = fetch_move_detail(name_en)
        time.sleep(DELAY)
        if detail is None:
            continue
        is_official, learners = detail
        # Pour les tutors : on marque `base` si le move est soit une CT
        # officielle (machines non vide), soit listé comme learnable dans
        # un jeu officiel (learned_by_pokemon non vide de manière générale).
        # Sinon c'est un tutor ajouté par IF.
        source = "base" if (is_official or learners) else "infinite_fusion"

        targets: set[int] = set()
        for slug in learners:
            pid = pokemon_ids.get(slug)
            if pid is None:
                continue
            targets.add(pid)
            targets |= all_descendants(pid, evolutions)

        if not targets:
            LOGGER.debug("Aucun apprenant pour %s", name_en)
            continue

        for pid in targets:
            cur.execute(
                """
                INSERT INTO pokemon_move (pokemon_id, move_id, method, source)
                VALUES (%s, %s, 'tutor', %s)
                ON CONFLICT (pokemon_id, move_id, method) DO NOTHING
                """,
                (pid, move_id, source),
            )
            if cur.rowcount:
                inserted += 1
            else:
                skipped += 1

        LOGGER.info("  %s (source=%s) → %d apprenants ciblés",
                    name_en, source, len(targets))

    conn.commit()
    cur.close()
    LOGGER.info("Terminé — %d nouvelles lignes tutor insérées, %d déjà présentes",
                inserted, skipped)


def main() -> None:
    with pg_connection() as conn:
        run(conn)


if __name__ == "__main__":
    main()
