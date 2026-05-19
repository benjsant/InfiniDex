"""ETL Audit — vérification de la cohérence de la base de données.

Checks effectués :
  1. Pokémon sans aucun sprite (ni head ni body dans fusion_sprite)
  2. Pokémon sans national_id (ne peuvent pas utiliser PokeAPI en fallback)
  3. Pokémon sans type déclaré
  4. Pokémon sans talent (ability)
  5. Pokémon sans aucune attaque apprise
  6. Moves orphelins — présents dans move mais appris par aucun Pokémon
  7. pokemon_move pointant vers un move inexistant (brisé côté FK — sécurité)
  8. fusion_sprite avec head_id ou body_id absent de pokemon
  9. Pokémon sans localisation connue (hors Pokémon Hoenn-only qui sont normaux)
 10. Résumé global avec compteurs

Usage :
    docker compose run --rm etl python -m etl.scripts.audit_db
"""

from __future__ import annotations

import json
from pathlib import Path

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging

log = setup_logging("audit_db")

SEP = "─" * 60


def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def ok(msg: str) -> None:
    print(f"  ✅  {msg}")


def warn(msg: str) -> None:
    print(f"  ⚠️   {msg}")


def fail(msg: str) -> None:
    print(f"  ❌  {msg}")


def run_audit() -> None:
    issues = 0

    with pg_connection() as conn:
        cur = conn.cursor()

        # ── 1. Pokémon totaux ─────────────────────────────────────────────
        section("Vue d'ensemble")
        cur.execute("SELECT COUNT(*) FROM pokemon")
        total_pokemon = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM move")
        total_moves = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM pokemon_move")
        total_pm = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM fusion_sprite")
        total_sprites = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT (head_id, body_id)) FROM fusion_sprite WHERE is_custom = TRUE")
        custom_sprites = cur.fetchone()[0]
        print(f"  Pokémon       : {total_pokemon}")
        print(f"  Moves         : {total_moves}")
        print(f"  pokemon_move  : {total_pm}")
        print(f"  fusion_sprite : {total_sprites}  (custom: {custom_sprites})")

        # ── 2. Pokémon sans sprite (ni head ni body) ──────────────────────
        section("2. Pokémon sans aucun sprite (ni head ni body)")
        cur.execute("""
            SELECT p.id, p.name_en
            FROM pokemon p
            WHERE p.id NOT IN (SELECT DISTINCT head_id FROM fusion_sprite)
              AND p.id NOT IN (SELECT DISTINCT body_id FROM fusion_sprite)
            ORDER BY p.id
        """)
        rows = cur.fetchall()
        if rows:
            fail(f"{len(rows)} Pokémon absents de fusion_sprite :")
            for pid, name in rows:
                print(f"       #{pid} {name}")
            issues += len(rows)
        else:
            ok("Tous les Pokémon ont au moins un sprite.")

        # ── 3. Pokémon sans national_id ───────────────────────────────────
        section("3. Pokémon sans national_id (fallback PokeAPI impossible)")
        cur.execute("""
            SELECT id, name_en FROM pokemon
            WHERE national_id IS NULL
            ORDER BY id
        """)
        rows = cur.fetchall()
        if rows:
            warn(f"{len(rows)} Pokémon sans national_id :")
            for pid, name in rows[:20]:
                print(f"       #{pid} {name}")
            if len(rows) > 20:
                print(f"       … et {len(rows) - 20} autres")
        else:
            ok("Tous les Pokémon ont un national_id.")

        # ── 4. Pokémon sans type ──────────────────────────────────────────
        section("4. Pokémon sans type déclaré (slot 1 obligatoire)")
        cur.execute("""
            SELECT p.id, p.name_en
            FROM pokemon p
            WHERE NOT EXISTS (
                SELECT 1 FROM pokemon_type pt
                WHERE pt.pokemon_id = p.id AND pt.slot = 1
            )
            ORDER BY p.id
        """)
        rows = cur.fetchall()
        if rows:
            fail(f"{len(rows)} Pokémon sans type primaire :")
            for pid, name in rows:
                print(f"       #{pid} {name}")
            issues += len(rows)
        else:
            ok("Tous les Pokémon ont un type primaire.")

        # ── 5. Pokémon sans talent (ability) ─────────────────────────────
        section("5. Pokémon sans talent (ability)")
        cur.execute("""
            SELECT p.id, p.name_en
            FROM pokemon p
            WHERE NOT EXISTS (
                SELECT 1 FROM pokemon_ability pa
                WHERE pa.pokemon_id = p.id
            )
            ORDER BY p.id
        """)
        rows = cur.fetchall()
        if rows:
            warn(f"{len(rows)} Pokémon sans talent :")
            for pid, name in rows[:20]:
                print(f"       #{pid} {name}")
            if len(rows) > 20:
                print(f"       … et {len(rows) - 20} autres")
        else:
            ok("Tous les Pokémon ont au moins un talent.")

        # ── 6. Pokémon sans aucune attaque ───────────────────────────────
        section("6. Pokémon sans aucune attaque apprise")
        cur.execute("""
            SELECT p.id, p.name_en
            FROM pokemon p
            WHERE NOT EXISTS (
                SELECT 1 FROM pokemon_move pm
                WHERE pm.pokemon_id = p.id
            )
            ORDER BY p.id
        """)
        rows = cur.fetchall()
        if rows:
            warn(f"{len(rows)} Pokémon sans aucune attaque :")
            for pid, name in rows[:20]:
                print(f"       #{pid} {name}")
            if len(rows) > 20:
                print(f"       … et {len(rows) - 20} autres")
        else:
            ok("Tous les Pokémon ont au moins une attaque.")

        # ── 7. Moves orphelins (appris par personne) ──────────────────────
        section("7. Moves orphelins — dans move mais appris par aucun Pokémon")
        cur.execute("""
            SELECT m.id, m.name_en, m.source
            FROM move m
            WHERE NOT EXISTS (
                SELECT 1 FROM pokemon_move pm WHERE pm.move_id = m.id
            )
              AND NOT EXISTS (
                SELECT 1 FROM tm t WHERE t.move_id = m.id
            )
            ORDER BY m.id
        """)
        rows = cur.fetchall()
        if rows:
            warn(f"{len(rows)} moves non appris par aucun Pokémon et sans CT :")
            for mid, name, source in rows[:30]:
                print(f"       #{mid} {name}  [{source}]")
            if len(rows) > 30:
                print(f"       … et {len(rows) - 30} autres")
        else:
            ok("Aucun move orphelin.")

        # ── 8. pokemon_move → move FK brisée ─────────────────────────────
        section("8. pokemon_move pointant vers un move inexistant")
        cur.execute("""
            SELECT DISTINCT pm.move_id
            FROM pokemon_move pm
            WHERE NOT EXISTS (
                SELECT 1 FROM move m WHERE m.id = pm.move_id
            )
            ORDER BY pm.move_id
        """)
        rows = cur.fetchall()
        if rows:
            fail(f"{len(rows)} move_id invalides dans pokemon_move :")
            for (mid,) in rows:
                print(f"       move_id={mid}")
            issues += len(rows)
        else:
            ok("Aucune FK brisée dans pokemon_move.")

        # ── 9. fusion_sprite avec Pokémon inconnu ────────────────────────
        section("9. fusion_sprite avec head_id ou body_id absent de pokemon")
        cur.execute("""
            SELECT COUNT(*) FROM fusion_sprite fs
            WHERE NOT EXISTS (SELECT 1 FROM pokemon p WHERE p.id = fs.head_id)
               OR NOT EXISTS (SELECT 1 FROM pokemon p WHERE p.id = fs.body_id)
        """)
        count = cur.fetchone()[0]
        if count:
            fail(f"{count} entrées fusion_sprite avec Pokémon introuvable.")
            issues += count
        else:
            ok("Toutes les entrées fusion_sprite référencent des Pokémon valides.")

        # ── 10. Pokémon sans localisation (hors Hoenn-only) ──────────────
        section("10. Pokémon sans localisation connue (hors Hoenn-only)")
        cur.execute("""
            SELECT p.id, p.name_en, p.is_hoenn_only
            FROM pokemon p
            WHERE NOT EXISTS (
                SELECT 1 FROM pokemon_location pl
                WHERE pl.pokemon_id = p.id
            )
              AND p.is_hoenn_only = FALSE
            ORDER BY p.id
        """)
        rows = cur.fetchall()
        if rows:
            warn(f"{len(rows)} Pokémon Kanto/communs sans localisation :")
            for pid, name, hoenn in rows[:30]:
                print(f"       #{pid} {name}")
            if len(rows) > 30:
                print(f"       … et {len(rows) - 30} autres")
        else:
            ok("Tous les Pokémon non-Hoenn ont au moins une localisation.")

        # ── 11. Doublons dans fusion_sprite par défaut ────────────────────
        section("11. Paires (head_id, body_id) avec plusieurs sprites par défaut")
        cur.execute("""
            SELECT head_id, body_id, COUNT(*) AS n
            FROM fusion_sprite
            WHERE is_default = TRUE
            GROUP BY head_id, body_id
            HAVING COUNT(*) > 1
            ORDER BY n DESC, head_id, body_id
            LIMIT 20
        """)
        rows = cur.fetchall()
        if rows:
            warn(f"{len(rows)} paires avec plusieurs sprites is_default=TRUE :")
            for hid, bid, n in rows:
                print(f"       head={hid} body={bid}  → {n} sprites default")
        else:
            ok("Aucune paire avec plusieurs sprites par défaut.")

        # ── 12. Divergence DB vs JSON source (capacités & types) ──────────
        # Détecte la perte silencieuse de données au chargement (ex: le bug
        # du slot_tracker qui collapsait la 2e capacité normale). Compare le
        # nombre attendu (source, plafonné au schéma) au réel en base.
        section("12. Cohérence DB vs JSON source (capacités normales & types)")
        cur.execute("SELECT id, lower(name_en), name_en FROM pokemon")
        id_name = {r[0]: r[2] for r in cur.fetchall()}
        cur.execute("SELECT lower(name_en), id FROM pokemon")
        name_to_id = dict(cur.fetchall())

        ab_path = Path("data/abilities_if.json")
        dex_path = Path("data/pokedex_if.json")
        if not ab_path.exists() or not dex_path.exists():
            warn("data/abilities_if.json ou pokedex_if.json absent — check ignoré.")
        else:
            # Abilities: capacités normales distinctes attendues (cap schéma = 2)
            expected_norm: dict[int, set[str]] = {}
            for ab in json.loads(ab_path.read_text(encoding="utf-8")):
                for poke in ab.get("pokemon", []):
                    if poke.get("is_hidden"):
                        continue
                    pid = name_to_id.get(poke["name"].lower())
                    if pid is not None:
                        expected_norm.setdefault(pid, set()).add(ab["name_en"].lower())
            cur.execute(
                "SELECT pokemon_id, COUNT(*) FROM pokemon_ability "
                "WHERE is_hidden = false GROUP BY pokemon_id"
            )
            actual_norm = dict(cur.fetchall())
            ab_bad = [
                (pid, min(len(n), 2), actual_norm.get(pid, 0))
                for pid, n in expected_norm.items()
                if actual_norm.get(pid, 0) < min(len(n), 2)
            ]
            if ab_bad:
                fail(f"{len(ab_bad)} Pokémon avec moins de capacités normales que la source :")
                for pid, exp, act in sorted(ab_bad)[:20]:
                    print(f"       #{pid} {id_name.get(pid, '?')} : attendu {exp}, réel {act}")
                if len(ab_bad) > 20:
                    print(f"       … et {len(ab_bad) - 20} autres")
                issues += len(ab_bad)
            else:
                ok("Capacités normales cohérentes avec abilities_if.json.")

            # Types: nb de slots attendus (1 ou 2 après dédup mono-type)
            expected_types: dict[int, int] = {}
            for entry in json.loads(dex_path.read_text(encoding="utf-8")):
                t1 = (entry.get("type1") or "").lower() or None
                t2 = (entry.get("type2") or "").lower() or None
                if t2 and t1 and t2 == t1:
                    t2 = None
                expected_types[entry["if_id"]] = (1 if t1 else 0) + (1 if t2 else 0)
            cur.execute("SELECT pokemon_id, COUNT(*) FROM pokemon_type GROUP BY pokemon_id")
            actual_types = dict(cur.fetchall())
            ty_bad = [
                (pid, exp, actual_types.get(pid, 0))
                for pid, exp in expected_types.items()
                if exp > 0 and actual_types.get(pid, 0) < exp
            ]
            if ty_bad:
                fail(f"{len(ty_bad)} Pokémon avec moins de types que la source :")
                for pid, exp, act in sorted(ty_bad)[:20]:
                    print(f"       #{pid} {id_name.get(pid, '?')} : attendu {exp}, réel {act}")
                if len(ty_bad) > 20:
                    print(f"       … et {len(ty_bad) - 20} autres")
                issues += len(ty_bad)
            else:
                ok("Types cohérents avec pokedex_if.json.")

        # ── Résumé ────────────────────────────────────────────────────────
        section("Résumé")
        if issues == 0:
            ok(f"Aucune erreur bloquante détectée. ({total_pokemon} Pokémon, {total_moves} moves, {total_sprites} sprites)")
        else:
            fail(f"{issues} problème(s) bloquant(s) à corriger.")

        print()


if __name__ == "__main__":
    run_audit()
