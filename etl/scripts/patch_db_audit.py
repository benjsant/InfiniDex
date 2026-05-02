"""
Patch DB — audit fixes 2026-05.

Corrections appliquées :
  1. TMs RandomizedOnly  — location mise à 'Mode aléatoire uniquement'
  2. Abilities manquantes — Deoxys (Pressure), Vigoroth (Vital Spirit),
                           Yamask (Mummy), Meloetta (Serene Grace),
                           Castform (Forecast → inséré),
                           Oricorio (Dancer), Lycanroc (Keen Eye / Sand Rush /
                           Steadfast / Vital Spirit / No Guard),
                           Minior (Shields Down)
  3. Moves manquants     — Oricorio, Lycanroc Midday/Midnight, Minior,
                           Aegislash, Pumpkaboo, Gourgeist
  4. Formes alternatives — Castform/Meloetta : copie abilities+moves depuis
                           la forme de base
  5. Encounters manquants — Meloetta (Saffron City), Minior (Mt. Moon Summit),
                            Necrozma (Mt. Moon) : national_id=None dans raw
                            empêchait le chargement
"""

from __future__ import annotations

import os

import psycopg2

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", "55432")),
    dbname=os.getenv("POSTGRES_DB", "fusiondex_db"),
    user=os.getenv("POSTGRES_USER", "fusiondex_user"),
    password=os.getenv("POSTGRES_PASSWORD", "changeme"),
)
conn.autocommit = False
cur = conn.cursor()


def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


# ── 1. TMs RandomizedOnly ─────────────────────────────────────────────────────
print("\n[1] TMs RandomizedOnly")
randomized_tms = [42, 48, 56, 59, 66, 69, 72, 77, 102, 103, 111, 115, 116, 118]
cur.execute(
    "UPDATE tm SET location = 'Mode aléatoire uniquement' WHERE number = ANY(%s)",
    (randomized_tms,),
)
log(f"{cur.rowcount} TMs mis à jour")


# ── 2. Abilities manquantes ───────────────────────────────────────────────────
print("\n[2] Abilities manquantes")

# Forecast n'est pas dans la table ability — on l'insère
cur.execute(
    """
    INSERT INTO ability (name_en, name_fr, description_en, description_fr)
    VALUES ('Forecast', 'Météo', 'Changes the Pokémon''s type to match the weather.',
            'Change le type du Pokémon en fonction du temps.')
    ON CONFLICT (name_en) DO NOTHING
    RETURNING id
    """,
)
row = cur.fetchone()
if row:
    forecast_id = row[0]
    log(f"Forecast inséré (id={forecast_id})")
else:
    cur.execute("SELECT id FROM ability WHERE name_en = 'Forecast'")
    forecast_id = cur.fetchone()[0]
    log(f"Forecast déjà présent (id={forecast_id})")

# ability_id constants (vérifiés en DB)
PRESSURE     = 104
VITAL_SPIRIT = 169
MUMMY        = 88
SERENE_GRACE = 123
DANCER       = 22
KEEN_EYE     = 66
SAND_RUSH    = 118
STEADFAST    = 143
NO_GUARD     = 91
SHIELDS_DOWN = 129
FRISK        = 40
INSOMNIA     = 61
PICKUP       = 97

simple_abilities = [
    # (pokemon_id, ability_id, slot, is_hidden, if_swapped, if_override)
    # Deoxys — Pressure slot 1
    (380, PRESSURE, 1, False, False, False),
    # Vigoroth — Vital Spirit slot 1
    (386, VITAL_SPIRIT, 1, False, False, False),
    # Yamask — Mummy slot 1
    (411, MUMMY, 1, False, False, False),
    # Meloetta Aria — Serene Grace slot 1
    (466, SERENE_GRACE, 1, False, False, False),
    # Castform base — Forecast slot 1
    (552, forecast_id, 1, False, False, False),
    # Oricorio (toutes formes) — Dancer slot 1
    (430, DANCER, 1, False, False, False),
    (431, DANCER, 1, False, False, False),
    (432, DANCER, 1, False, False, False),
    (433, DANCER, 1, False, False, False),
    # Lycanroc Midday — Keen Eye / Sand Rush / Steadfast (hidden)
    (464, KEEN_EYE,     1, False, False, False),
    (464, SAND_RUSH,    2, False, False, False),
    (464, STEADFAST,    3, True,  False, False),
    # Lycanroc Midnight — Keen Eye / Vital Spirit / No Guard (hidden)
    (465, KEEN_EYE,     1, False, False, False),
    (465, VITAL_SPIRIT, 2, False, False, False),
    (465, NO_GUARD,     3, True,  False, False),
    # Minior (Meteor + Core) — Shields Down slot 1
    (498, SHIELDS_DOWN, 1, False, False, False),
    (499, SHIELDS_DOWN, 1, False, False, False),
]

inserted_ab = 0
for row in simple_abilities:
    cur.execute(
        """
        INSERT INTO pokemon_ability (pokemon_id, ability_id, slot, is_hidden, if_swapped, if_override)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (pokemon_id, slot) DO NOTHING
        """,
        row,
    )
    inserted_ab += cur.rowcount
log(f"{inserted_ab} abilities insérées")

# Copie formes alternatives : Meloetta Pirouette (467) ← Aria (466)
#                             Castform formes (553-555) ← base (552)
for base_id, alt_ids in [(466, [467]), (552, [553, 554, 555])]:
    cur.execute("SELECT ability_id, slot, is_hidden, if_swapped, if_override FROM pokemon_ability WHERE pokemon_id = %s", (base_id,))
    rows = cur.fetchall()
    for alt_id in alt_ids:
        for r in rows:
            cur.execute(
                """
                INSERT INTO pokemon_ability (pokemon_id, ability_id, slot, is_hidden, if_swapped, if_override)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (pokemon_id, slot) DO NOTHING
                """,
                (alt_id, *r),
            )
            inserted_ab += cur.rowcount
log(f"Formes alternatives abilities copiées (total cumulé : {inserted_ab})")


# ── 3. Moves manquants ────────────────────────────────────────────────────────
print("\n[3] Moves manquants")

# Move IDs (vérifiés en DB)
M = {
    "Pound": 442, "Growl": 398, "Echoed Voice": 376, "Helping Hand": 406,
    "Aerial Ace": 207, "Double Slap": 373, "Teeter Dance": 504, "Air Cutter": 209,
    "Roost": 226, "Captivate": 356, "Feather Dance": 218, "Revelation Dance": 457,
    "Air Slash": 210, "Calm Mind": 549, "Hurricane": 221,
    # Lycanroc
    "Tackle": 498, "Leer": 419, "Sand Attack": 312, "Bite": 31, "Headbutt": 404,
    "Rock Throw": 613, "Odor Sleuth": 437, "Rock Tomb": 614, "Roar": 458,
    "Stealth Rock": 619, "Rock Climb": 459, "Scary Face": 462, "Crunch": 33,
    "Rock Slide": 612, "Stone Edge": 620, "Counter": 136,
    # Minior
    "Harden": 402, "Rollout": 616, "Magnitude": 305, "Rapid Spin": 448,
    "Smack Down": 618, "Self-Destruct": 466, "Power Gem": 609,
    "Light Screen": 568, "Swift": 496, "Cosmic Power": 551,
    "Explosion": 382, "Shell Smash": 468,
    # Aegislash
    "Swords Dance": 497, "Fury Cutter": 7, "Pursuit": 54, "Autotomize": 623,
    "Wide Guard": 621, "Iron Defense": 632, "Head Smash": 608, "Retaliate": 455,
    "King's Shield": 635, "Shadow Sneak": 248, "Shadow Claw": 245,
    "Iron Head": 633, "Sacred Sword": 161, "Night Slash": 49,
    # Pumpkaboo / Gourgeist
    "Trick": 601, "Astonish": 231, "Confuse Ray": 232, "Trick-or-Treat": 252,
    "Worry Seed": 293, "Razor Leaf": 279, "Leech Seed": 272, "Bullet Seed": 255,
    "Shadow Ball": 243, "Pain Split": 438, "Seed Bomb": 280, "Phantom Force": 242,
}

# (pokemon_id, move_id, method, level, source)
moves_to_insert = []

def lv(pokemon_ids: list[int], move_name: str, level: int) -> None:
    for pid in pokemon_ids:
        moves_to_insert.append((pid, M[move_name], "level_up", level, "base"))

# Oricorio (430-433) — même moveset pour toutes les formes
oricorio = [430, 431, 432, 433]
lv(oricorio, "Pound",            1)
lv(oricorio, "Growl",            1)
lv(oricorio, "Echoed Voice",     4)
lv(oricorio, "Helping Hand",     8)
lv(oricorio, "Aerial Ace",      12)
lv(oricorio, "Double Slap",     16)
lv(oricorio, "Teeter Dance",    20)
lv(oricorio, "Air Cutter",      24)
lv(oricorio, "Roost",           28)
lv(oricorio, "Captivate",       32)
lv(oricorio, "Feather Dance",   36)
lv(oricorio, "Revelation Dance",40)
lv(oricorio, "Air Slash",       44)
lv(oricorio, "Calm Mind",       48)
lv(oricorio, "Hurricane",       52)

# Lycanroc Midday (464)
lv([464], "Tackle",       1)
lv([464], "Leer",         1)
lv([464], "Sand Attack",  4)
lv([464], "Bite",         8)
lv([464], "Headbutt",    12)
lv([464], "Rock Throw",  16)
lv([464], "Odor Sleuth", 20)
lv([464], "Rock Tomb",   24)
lv([464], "Roar",        28)
lv([464], "Stealth Rock",32)
lv([464], "Rock Climb",  36)
lv([464], "Scary Face",  40)
lv([464], "Crunch",      44)
lv([464], "Rock Slide",  48)
lv([464], "Stone Edge",  52)

# Lycanroc Midnight (465) — même base + Counter à 36
lv([465], "Tackle",       1)
lv([465], "Leer",         1)
lv([465], "Sand Attack",  4)
lv([465], "Bite",         8)
lv([465], "Headbutt",    12)
lv([465], "Rock Throw",  16)
lv([465], "Odor Sleuth", 20)
lv([465], "Rock Tomb",   24)
lv([465], "Roar",        28)
lv([465], "Stealth Rock",32)
lv([465], "Counter",     36)
lv([465], "Scary Face",  40)
lv([465], "Crunch",      44)
lv([465], "Rock Slide",  48)
lv([465], "Stone Edge",  52)

# Minior (498-499) — même moveset
minior = [498, 499]
lv(minior, "Tackle",       1)
lv(minior, "Harden",       1)
lv(minior, "Rollout",      4)
lv(minior, "Magnitude",    8)
lv(minior, "Rapid Spin",  12)
lv(minior, "Smack Down",  16)
lv(minior, "Self-Destruct",20)
lv(minior, "Power Gem",   24)
lv(minior, "Stealth Rock",28)
lv(minior, "Light Screen",32)
lv(minior, "Swift",       36)
lv(minior, "Cosmic Power",40)
lv(minior, "Explosion",   44)
lv(minior, "Shell Smash", 48)

# Aegislash (329) — tous à niveau 1 (hérité via Dusk Stone)
for move_name in [
    "Tackle","Swords Dance","Fury Cutter","Pursuit","Autotomize","Wide Guard",
    "Iron Defense","Head Smash","Retaliate","King's Shield","Shadow Sneak",
    "Aerial Ace","Shadow Claw","Iron Head","Sacred Sword","Night Slash",
]:
    moves_to_insert.append((329, M[move_name], "level_up", 1, "base"))

# Pumpkaboo (489)
lv([489], "Trick",          1)
lv([489], "Astonish",       1)
lv([489], "Confuse Ray",    1)
lv([489], "Scary Face",     4)
lv([489], "Trick-or-Treat", 8)
lv([489], "Worry Seed",    12)
lv([489], "Razor Leaf",    16)
lv([489], "Leech Seed",    20)
lv([489], "Bullet Seed",   24)
lv([489], "Shadow Sneak",  28)
lv([489], "Shadow Ball",   32)
lv([489], "Pain Split",    36)
lv([489], "Seed Bomb",     40)

# Gourgeist (490) — Pumpkaboo + Phantom Force
lv([490], "Trick",          1)
lv([490], "Astonish",       1)
lv([490], "Confuse Ray",    1)
lv([490], "Scary Face",     4)
lv([490], "Trick-or-Treat", 8)
lv([490], "Worry Seed",    12)
lv([490], "Razor Leaf",    16)
lv([490], "Leech Seed",    20)
lv([490], "Bullet Seed",   24)
lv([490], "Shadow Sneak",  28)
lv([490], "Shadow Ball",   32)
lv([490], "Pain Split",    36)
lv([490], "Seed Bomb",     40)
lv([490], "Phantom Force", 44)

# Copie des moves : Meloetta Pirouette (467) ← Aria (466)
# et Castform formes ← base
for base_id, alt_ids in [(466, [467]), (552, [553, 554, 555])]:
    cur.execute(
        "SELECT move_id, method, level, source FROM pokemon_move WHERE pokemon_id = %s",
        (base_id,),
    )
    for move_id, method, level, source in cur.fetchall():
        for alt_id in alt_ids:
            moves_to_insert.append((alt_id, move_id, method, level, source))

inserted_mv = 0
for row in moves_to_insert:
    cur.execute(
        """
        INSERT INTO pokemon_move (pokemon_id, move_id, method, level, source)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (pokemon_id, move_id, method) DO NOTHING
        """,
        row,
    )
    inserted_mv += cur.rowcount
log(f"{inserted_mv} moves insérés")


# ── 4. Encounters manquants ───────────────────────────────────────────────────
print("\n[4] Encounters manquants (Meloetta, Minior, Necrozma)")

# location IDs vérifiés en DB
LOC = {"Mt. Moon": 46, "Mt. Moon Summit": 49, "Saffron City": 115}

# IF IDs des formes principales
encounters = [
    # (pokemon_id, location_id, method, notes)
    (466, LOC["Saffron City"],    "static", "Legendary"),   # Meloetta Aria
    (498, LOC["Mt. Moon Summit"], "static", "Lv 17"),        # Minior Meteor
    (450, LOC["Mt. Moon"],        "static", "Legendary"),   # Necrozma
]

inserted_enc = 0
for pid, loc_id, method, notes in encounters:
    cur.execute(
        """
        INSERT INTO pokemon_location (pokemon_id, location_id, method, notes)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (pokemon_id, location_id, method) DO NOTHING
        """,
        (pid, loc_id, method, notes),
    )
    inserted_enc += cur.rowcount
log(f"{inserted_enc} encounters insérés")


# ── Commit ────────────────────────────────────────────────────────────────────
conn.commit()
cur.close()
conn.close()
print("\n✓ Patch appliqué avec succès.")
