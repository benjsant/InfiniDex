"""ETL Audit — database consistency checks.

Checks performed:
  1. Pokémon with no sprite (neither head nor body in fusion_sprite)
  2. Pokémon with no national_id (cannot use PokeAPI as a fallback)
  3. Pokémon with no declared type
  4. Pokémon with no ability
  5. Pokémon with no learned move
  6. Orphan moves — present in move but learned by no Pokémon
  7. pokemon_move pointing to a non-existent move (broken FK — safety)
  8. fusion_sprite with head_id or body_id absent from pokemon
  9. Pokémon with no known location (excluding Hoenn-only, which is normal)
 10. Global summary with counters

Usage:
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

        # ── 1. Total Pokémon ──────────────────────────────────────────────
        section("Overview")
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

        # ── 2. Pokémon with no sprite (neither head nor body) ─────────────
        section("2. Pokémon with no sprite at all (neither head nor body)")
        cur.execute("""
            SELECT p.id, p.name_en
            FROM pokemon p
            WHERE p.id NOT IN (SELECT DISTINCT head_id FROM fusion_sprite)
              AND p.id NOT IN (SELECT DISTINCT body_id FROM fusion_sprite)
            ORDER BY p.id
        """)
        rows = cur.fetchall()
        if rows:
            fail(f"{len(rows)} Pokémon absent from fusion_sprite:")
            for pid, name in rows:
                print(f"       #{pid} {name}")
            issues += len(rows)
        else:
            ok("All Pokémon have at least one sprite.")

        # ── 3. Pokémon with no national_id ────────────────────────────────
        section("3. Pokémon with no national_id (PokeAPI fallback impossible)")
        cur.execute("""
            SELECT id, name_en FROM pokemon
            WHERE national_id IS NULL
            ORDER BY id
        """)
        rows = cur.fetchall()
        if rows:
            warn(f"{len(rows)} Pokémon with no national_id:")
            for pid, name in rows[:20]:
                print(f"       #{pid} {name}")
            if len(rows) > 20:
                print(f"       … and {len(rows) - 20} more")
        else:
            ok("All Pokémon have a national_id.")

        # ── 4. Pokémon with no type ───────────────────────────────────────
        section("4. Pokémon with no declared type (slot 1 mandatory)")
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
            fail(f"{len(rows)} Pokémon with no primary type:")
            for pid, name in rows:
                print(f"       #{pid} {name}")
            issues += len(rows)
        else:
            ok("All Pokémon have a primary type.")

        # ── 5. Pokémon with no ability ────────────────────────────────────
        section("5. Pokémon with no ability")
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
            warn(f"{len(rows)} Pokémon with no ability:")
            for pid, name in rows[:20]:
                print(f"       #{pid} {name}")
            if len(rows) > 20:
                print(f"       … and {len(rows) - 20} more")
        else:
            ok("All Pokémon have at least one ability.")

        # ── 6. Pokémon with no move ───────────────────────────────────────
        section("6. Pokémon with no learned move")
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
            warn(f"{len(rows)} Pokémon with no move at all:")
            for pid, name in rows[:20]:
                print(f"       #{pid} {name}")
            if len(rows) > 20:
                print(f"       … and {len(rows) - 20} more")
        else:
            ok("All Pokémon have at least one move.")

        # ── 7. Orphan moves (learned by nobody) ───────────────────────────
        section("7. Orphan moves — in move but learned by no Pokémon")
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
            warn(f"{len(rows)} moves learned by no Pokémon and with no TM:")
            for mid, name, source in rows[:30]:
                print(f"       #{mid} {name}  [{source}]")
            if len(rows) > 30:
                print(f"       … and {len(rows) - 30} more")
        else:
            ok("No orphan move.")

        # ── 8. pokemon_move → broken move FK ──────────────────────────────
        section("8. pokemon_move pointing to a non-existent move")
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
            fail(f"{len(rows)} invalid move_id in pokemon_move:")
            for (mid,) in rows:
                print(f"       move_id={mid}")
            issues += len(rows)
        else:
            ok("No broken FK in pokemon_move.")

        # ── 9. fusion_sprite with unknown Pokémon ─────────────────────────
        section("9. fusion_sprite with head_id or body_id absent from pokemon")
        cur.execute("""
            SELECT COUNT(*) FROM fusion_sprite fs
            WHERE NOT EXISTS (SELECT 1 FROM pokemon p WHERE p.id = fs.head_id)
               OR NOT EXISTS (SELECT 1 FROM pokemon p WHERE p.id = fs.body_id)
        """)
        count = cur.fetchone()[0]
        if count:
            fail(f"{count} fusion_sprite entries with a missing Pokémon.")
            issues += count
        else:
            ok("All fusion_sprite entries reference valid Pokémon.")

        # ── 10. Pokémon with no location (excluding Hoenn-only) ───────────
        section("10. Pokémon with no known location (excluding Hoenn-only)")
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
            warn(f"{len(rows)} Kanto/common Pokémon with no location:")
            for pid, name, hoenn in rows[:30]:
                print(f"       #{pid} {name}")
            if len(rows) > 30:
                print(f"       … and {len(rows) - 30} more")
        else:
            ok("All non-Hoenn Pokémon have at least one location.")

        # ── 11. Duplicate default fusion_sprite ───────────────────────────
        section("11. (head_id, body_id) pairs with multiple default sprites")
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
            warn(f"{len(rows)} pairs with multiple is_default=TRUE sprites:")
            for hid, bid, n in rows:
                print(f"       head={hid} body={bid}  → {n} default sprites")
        else:
            ok("No pair with multiple default sprites.")

        # ── 12. DB vs source JSON divergence (abilities & types) ──────────
        # Detects silent data loss at load time (e.g. the slot_tracker bug
        # that collapsed the 2nd normal ability). Compares the expected
        # count (source, capped to the schema) to the actual count in DB.
        section("12. DB vs source JSON consistency (normal abilities & types)")
        cur.execute("SELECT id, lower(name_en), name_en FROM pokemon")
        id_name = {r[0]: r[2] for r in cur.fetchall()}
        cur.execute("SELECT lower(name_en), id FROM pokemon")
        name_to_id = dict(cur.fetchall())

        ab_path = Path("data/abilities_if.json")
        dex_path = Path("data/pokedex_if.json")
        if not ab_path.exists() or not dex_path.exists():
            warn("data/abilities_if.json or pokedex_if.json missing — check skipped.")
        else:
            # Abilities: distinct expected normal abilities (schema cap = 2)
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
                fail(f"{len(ab_bad)} Pokémon with fewer normal abilities than the source:")
                for pid, exp, act in sorted(ab_bad)[:20]:
                    print(f"       #{pid} {id_name.get(pid, '?')} : expected {exp}, actual {act}")
                if len(ab_bad) > 20:
                    print(f"       … and {len(ab_bad) - 20} more")
                issues += len(ab_bad)
            else:
                ok("Normal abilities consistent with abilities_if.json.")

            # Types: number of expected slots (1 or 2 after mono-type dedup)
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
                fail(f"{len(ty_bad)} Pokémon with fewer types than the source:")
                for pid, exp, act in sorted(ty_bad)[:20]:
                    print(f"       #{pid} {id_name.get(pid, '?')} : expected {exp}, actual {act}")
                if len(ty_bad) > 20:
                    print(f"       … and {len(ty_bad) - 20} more")
                issues += len(ty_bad)
            else:
                ok("Types consistent with pokedex_if.json.")

        # ── Summary ───────────────────────────────────────────────────────
        section("Summary")
        if issues == 0:
            ok(f"No blocking error detected. ({total_pokemon} Pokémon, {total_moves} moves, {total_sprites} sprites)")
        else:
            fail(f"{issues} blocking issue(s) to fix.")

        print()


if __name__ == "__main__":
    run_audit()
