"""
Correction script — enrich alternate-form Pokémon via PokeAPI form slugs.

The IF wiki lists alternate forms (Oricorio styles, Castform weathers, ...) as
separate Pokédex rows sharing the species name. They can't carry a national_id
(UNIQUE constraint — the base-form row owns it), so every national_id-based
fix skips them and step 8 leaves them with the stats and FR name of the WRONG
species (pokemon_stats.json is fetched by if_id — #470 Necrozma Ultra used to
ship with Leafeon's stats under the name "Phyllali").

This script owns the national_id-less form rows:
  - stats + base_experience  ← PokeAPI /pokemon/{form-slug} (per-form values:
                               Lycanroc Midday and Midnight differ)
  - name_fr                  ← PokeAPI /pokemon-species (FR species name)
  - abilities                ← PokeAPI /pokemon/{form-slug} (DELETE + INSERT,
                               this script is the sole owner of these rows)

Types are NOT touched here: fix_pokemon_types.py already restores them from
the wiki, which stays the authority on typing.

The (name, form) → PokeAPI slug mapping is explicit (14 known forms). A form
missing from the mapping logs a warning so wiki drift stays visible.

Idempotent. Runs as step 8e-quater, after fix_national_ids and the re-syncs.
"""

from __future__ import annotations

from pathlib import Path

from etl.utils.db import pg_connection
from etl.utils.http import get_json
from etl.utils.io import load_json
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

POKEAPI       = "https://pokeapi.co/api/v2"
POKEDEX_JSON  = Path("data/pokedex_if.json")

# (name_en.lower(), form.lower()) → PokeAPI pokemon endpoint slug
FORM_SLUGS: dict[tuple[str, str], str] = {
    ("oricorio", "baile style"):    "oricorio-baile",
    ("oricorio", "pom-pom style"):  "oricorio-pom-pom",
    ("oricorio", "pa'u style"):     "oricorio-pau",
    ("oricorio", "sensu style"):    "oricorio-sensu",
    ("lycanroc", "midday form"):    "lycanroc-midday",
    ("lycanroc", "midnight form"):  "lycanroc-midnight",
    ("meloetta", "aria form"):      "meloetta-aria",
    ("meloetta", "pirouette form"): "meloetta-pirouette",
    ("necrozma", "ultra"):          "necrozma-ultra",
    ("minior", "meteor form"):      "minior-red-meteor",
    ("minior", "core form"):        "minior-red",
    ("castform", "sunny"):          "castform-sunny",
    ("castform", "rainy"):          "castform-rainy",
    ("castform", "snowy"):          "castform-snowy",
}

# PokeAPI stat slug → pokemon table column
STAT_COLUMNS = {
    "hp":              "hp",
    "attack":          "attack",
    "defense":         "defense",
    "special-attack":  "sp_attack",
    "special-defense": "sp_defense",
    "speed":           "speed",
}


def form_slug(name_en: str, form: str) -> str | None:
    key = (name_en.lower().strip(), form.lower().strip().replace("’", "'"))
    return FORM_SLUGS.get(key)


def _species_name_fr(species_slug: str) -> str | None:
    data = get_json(f"{POKEAPI}/pokemon-species/{species_slug}")
    if data is None:
        return None
    names = {n["language"]["name"]: n["name"] for n in data["names"]}
    return names.get("fr")


def _resolve_ability(cur, ability_cache: dict[str, int], slug: str) -> int | None:
    """Return ability.id for a PokeAPI ability slug, creating the row if needed."""
    title = slug.replace("-", " ").title()
    if title in ability_cache:
        return ability_cache[title]

    data = get_json(f"{POKEAPI}/ability/{slug}")
    if data is None:
        LOGGER.warning("Ability %r not found on PokeAPI", slug)
        return None
    names   = {n["language"]["name"]: n["name"] for n in data["names"]}
    name_en = names.get("en", title)
    name_fr = names.get("fr")

    if name_en in ability_cache:
        return ability_cache[name_en]

    cur.execute(
        """INSERT INTO ability (name_en, name_fr) VALUES (%s, %s)
           ON CONFLICT (name_en) DO UPDATE SET name_fr = EXCLUDED.name_fr
           RETURNING id""",
        (name_en, name_fr),
    )
    ability_id = cur.fetchone()[0]
    ability_cache[name_en] = ability_id
    LOGGER.info("  + ability created: %s (id=%d)", name_en, ability_id)
    return ability_id


def fix_form_pokemon(conn) -> None:
    if not POKEDEX_JSON.exists():
        raise FileNotFoundError(f"{POKEDEX_JSON} not found — run extract_pokedex_if.py first")

    forms = [e for e in load_json(POKEDEX_JSON) if e.get("form")]
    LOGGER.info("%d form rows in the Pokédex JSON", len(forms))

    cur = conn.cursor()
    cur.execute("SELECT id FROM pokemon WHERE national_id IS NULL")
    orphan_ids: set[int] = {r[0] for r in cur.fetchall()}

    cur.execute("SELECT name_en, id FROM ability")
    ability_cache: dict[str, int] = dict(cur.fetchall())

    fixed = skipped = unmapped = errors = 0

    for entry in forms:
        if_id, name_en, form = entry["if_id"], entry["name_en"], entry["form"]

        if if_id not in orphan_ids:
            # Base-form row (e.g. Oricorio Baile owns national 741): the
            # standard national_id pipeline already handles it.
            skipped += 1
            continue

        slug = form_slug(name_en, form)
        if slug is None:
            LOGGER.warning(
                "No PokeAPI slug mapped for #%d %s %r — new wiki form? "
                "Extend FORM_SLUGS.", if_id, name_en, form,
            )
            unmapped += 1
            continue

        data = get_json(f"{POKEAPI}/pokemon/{slug}")
        if data is None:
            LOGGER.warning("PokeAPI fetch failed for %r (#%d)", slug, if_id)
            errors += 1
            continue

        stats = {STAT_COLUMNS[s["stat"]["name"]]: s["base_stat"]
                 for s in data["stats"] if s["stat"]["name"] in STAT_COLUMNS}
        name_fr = _species_name_fr(data["species"]["name"])

        cur.execute(
            """UPDATE pokemon
               SET hp=%s, attack=%s, defense=%s, sp_attack=%s, sp_defense=%s,
                   speed=%s, base_experience=%s,
                   name_fr=COALESCE(%s, name_fr)
               WHERE id=%s""",
            (stats["hp"], stats["attack"], stats["defense"], stats["sp_attack"],
             stats["sp_defense"], stats["speed"], data.get("base_experience"),
             name_fr, if_id),
        )

        # Abilities: this script is the sole owner for these rows
        cur.execute("DELETE FROM pokemon_ability WHERE pokemon_id = %s", (if_id,))
        for ab in data["abilities"]:
            ability_id = _resolve_ability(cur, ability_cache, ab["ability"]["name"])
            if ability_id is None:
                continue
            cur.execute(
                """INSERT INTO pokemon_ability (pokemon_id, ability_id, slot, is_hidden)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (pokemon_id, slot) DO NOTHING""",
                (if_id, ability_id, ab["slot"], ab["is_hidden"]),
            )

        conn.commit()
        LOGGER.info("Fixed #%d %s (%s) via %r — name_fr=%s", if_id, name_en, form, slug, name_fr)
        fixed += 1

    LOGGER.info(
        "Done — %d fixed | %d base-form skipped | %d unmapped | %d errors",
        fixed, skipped, unmapped, errors,
    )
    if unmapped:
        raise RuntimeError(
            f"{unmapped} wiki form(s) missing from FORM_SLUGS — extend the mapping."
        )


def main() -> None:
    with pg_connection() as conn:
        fix_form_pokemon(conn)


if __name__ == "__main__":
    main()
