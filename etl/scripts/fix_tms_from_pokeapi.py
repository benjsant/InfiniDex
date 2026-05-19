"""
Script de correction — complète les CT Infinite Fusion via PokeAPI.

Règle métier (Infinite Fusion) : un Pokémon peut apprendre une CT IF dès lors
qu'il apprend ce move par *n'importe quelle* méthode dans les jeux officiels
(niveau, CT, tuteur, œuf) OU par pré-évolution. Le scraper du wiki IF ne capte
que les mouvements listés sur la page propre de chaque Pokémon, ce qui laisse
beaucoup de trous (ex. Moonblast : 13 Pokémon côté IF, 63 côté PokeAPI).

Pipeline :
  1. Liste des CT IF → wiki fandom (api.php, prop=wikitext).
  2. Pour chaque CT, PokeAPI /move/{name}/ → liste des apprenants + flag
     `machines` (CT officielle dans au moins un jeu ?).
  3. Insère `pokemon_move(method='tm', source=base|infinite_fusion)` pour
     chaque apprenant existant dans notre DB.
  4. Héritage pré-évolution forward : tout descendant d'un apprenant reçoit
     aussi la CT (règle IF rappelée par l'utilisateur).
  5. Idempotent via la contrainte UNIQUE (pokemon_id, move_id, method).

Le champ `source` distingue :
  - `base`             : CT officielle Nintendo (existe dans au moins un jeu).
  - `infinite_fusion`  : CT spécifique à IF (le move n'est pas CT ailleurs).
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


# ─── Step 1 — IF TM list ──────────────────────────────────────────────────────

TM_ROW_RE = re.compile(
    r"\|\s*(?:TM|HM)\d+\s*\n\|\s*\[\[[^|\]]+\|(?P<name>[^\]]+)\]\]"
)


def fetch_if_tm_names() -> list[str]:
    """Retourne les noms (en) des moves listés comme CT sur le wiki IF."""
    resp = requests.get(
        WIKI_API,
        params={
            "action": "parse",
            "page":   "List_of_TMs",
            "prop":   "wikitext",
            "format": "json",
        },
        headers={"User-Agent": WIKI_UA},
        timeout=20,
    )
    resp.raise_for_status()
    wikitext = resp.json()["parse"]["wikitext"]["*"]
    names = sorted({m.group("name").strip() for m in TM_ROW_RE.finditer(wikitext)})
    LOGGER.info("Wiki IF : %d moves distincts listés comme CT", len(names))
    return names


# ─── Step 2 — PokeAPI move details ────────────────────────────────────────────

def pokeapi_move_slug(name_en: str) -> str:
    """Convertit un nom de move (EN) vers un slug PokeAPI."""
    return (
        name_en.lower()
        .replace("'", "")
        .replace(".", "")
        .replace(" ", "-")
    )


def fetch_move_detail(name_en: str) -> tuple[bool, list[str]] | None:
    """Retourne (is_official_tm, pokemon_slugs) ou None si introuvable."""
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
    is_official_tm = bool(data.get("machines"))
    learners = [p["name"] for p in data.get("learned_by_pokemon", [])]
    return is_official_tm, learners


# ─── Step 3 — DB helpers ──────────────────────────────────────────────────────

def load_move_ids(cur, names: list[str]) -> dict[str, int]:
    """name_en → move.id (limité aux moves présents en base)."""
    cur.execute("SELECT id, name_en FROM move WHERE name_en = ANY(%s)", (names,))
    return {name: mid for mid, name in cur.fetchall()}


def load_pokemon_ids(cur) -> dict[str, int]:
    """slug PokeAPI-like (lowercased name_en) → pokemon.id"""
    cur.execute("SELECT id, name_en FROM pokemon")
    out: dict[str, int] = {}
    for pid, name_en in cur.fetchall():
        out[pokeapi_move_slug(name_en)] = pid
    return out


def load_evolution_forward(cur) -> dict[int, list[int]]:
    """pokemon_id → liste des descendants directs."""
    cur.execute("SELECT pokemon_id, evolves_into_id FROM pokemon_evolution")
    out: dict[int, list[int]] = defaultdict(list)
    for src, tgt in cur.fetchall():
        out[src].append(tgt)
    return out


def all_descendants(start: int, edges: dict[int, list[int]]) -> set[int]:
    """BFS des descendants d'un Pokémon (hors lui-même)."""
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

    tm_names = fetch_if_tm_names()
    move_ids = load_move_ids(cur, tm_names)
    LOGGER.info("Moves trouvés en base : %d / %d", len(move_ids), len(tm_names))
    missing = set(tm_names) - set(move_ids)
    if missing:
        LOGGER.warning("Moves CT IF absents de la table `move` (ignorés) : %s",
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
        is_official_tm, learners = detail
        source = "base" if is_official_tm else "infinite_fusion"

        # Collecte des pokémon_id (apprenants + descendants)
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

        # INSERT idempotent
        for pid in targets:
            cur.execute(
                """
                INSERT INTO pokemon_move (pokemon_id, move_id, method, source)
                VALUES (%s, %s, 'tm', %s)
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
    LOGGER.info("Terminé — %d nouvelles lignes CT insérées, %d déjà présentes",
                inserted, skipped)


def main() -> None:
    with pg_connection() as conn:
        run(conn)


if __name__ == "__main__":
    main()
