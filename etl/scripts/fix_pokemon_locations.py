"""
ETL — Fix/reload Pokémon location data from authoritative wiki sources.

Replaces all static and gift entries with correct data sourced from:
  - https://infinitefusion.fandom.com/wiki/Legendary_Pokémon
  - https://infinitefusion.fandom.com/wiki/List_of_Gift_Pokémon_and_Trades
  - https://infinitefusion.fandom.com/wiki/Pallet_Town  (inaccessible grass joke)

Also removes known incorrect wild entries (e.g. Rayquaza on Route 23).

Fused legendaries are expanded to their component Pokémon:
  - Raicune  → Raikou + Suicune  (Ruins of Alph)
  - Ho-Gia   → Ho-Oh  + Lugia    (Navel Rock)
  - Reshirom → Reshiram + Zekrom  (Bell Tower)
"""

from __future__ import annotations

from etl.utils.db import pg_connection
from etl.utils.logging import setup_logging

LOGGER = setup_logging(__name__)

# ---------------------------------------------------------------------------
# Legendary encounters (method='static')
# One tuple per Pokémon component:  (name_en, location_name, level, notes)
# Fused legendaries are listed once per component with an explanatory note.
# ---------------------------------------------------------------------------
LEGENDARIES: list[tuple[str, str, int | None, str]] = [
    # Kanto birds
    ("Articuno", "Seafoam Islands", 50,
     "Legendary. Requires Ice Pick from Mt. Ember and Surf."),
    ("Zapdos",   "Power Plant",     50,
     "Legendary. Requires Power Plant Access Key."),
    ("Moltres",  "Mt. Ember",       50,
     "Legendary. Requires Surf and Strength."),

    # Johto beasts — Raicune is a fused form of Raikou + Suicune
    ("Raikou",  "Ruins of Alph", None,
     "Legendary. Encountered fused as Raicune. Roaming Johto after Ruins of Alph (meet Eusine in Violet City). Track via Weather Tracker."),
    ("Suicune", "Ruins of Alph", None,
     "Legendary. Encountered fused as Raicune. Roaming Johto after Ruins of Alph (meet Eusine in Violet City). Track via Weather Tracker."),
    ("Entei",   "Victory Road",  45,
     "Legendary. Found on Victory Road 2nd floor. Roams Johto if defeated."),

    # Johto birds — Ho-Gia is a fused form of Ho-oh + Lugia
    ("Ho-oh", "Navel Rock", 60,
     "Legendary. Encountered fused as Ho-Gia. Requires Navel Ticket from Chuck on Boon Island."),
    ("Lugia", "Navel Rock", 60,
     "Legendary. Encountered fused as Ho-Gia. Requires Navel Ticket from Chuck on Boon Island."),

    # Unova dragons — Reshirom is a fused form of Reshiram + Zekrom
    ("Reshiram", "Bell Tower", 70,
     "Legendary. Encountered fused as Reshirom. Defeat Kimono girls in Ecruteak City first."),
    ("Zekrom",   "Bell Tower", 70,
     "Legendary. Encountered fused as Reshirom. Defeat Kimono girls in Ecruteak City first."),

    # Hoenn weather trio
    ("Rayquaza", "Sky Pillar",    70,
     "Legendary. Requires Kyogre and Groudon encountered first."),
    ("Kyogre",   "Sapphire Cave", 60,
     "Legendary. Sapphire Cave in Deep Sea. Requires Sapphire collection puzzle."),
    ("Groudon",  "Mt. Ember",     60,
     "Legendary. Ruby Chamber at Mt. Ember. Requires Ruby collection and heat-protection cream."),

    # Unova ice dragon
    ("Kyurem", "Lake of Rage", 70,
     "Legendary. Requires Dark and Light stones."),

    # Psychic legendaries
    ("Mewtwo",  "Cerulean Cave", 60,
     "Legendary. Requires HM05 Waterfall and 2+ Johto badges."),
    ("Mew",     "Mt. Moon",      30,
     "Legendary. Mt. Moon Summit. Requires 20+ Karma and all 8 Constellations."),
    ("Celebi",  "Ilex Forest",   30,
     "Legendary. Complete 50 hotel quests to obtain the GS Ball."),
    ("Jirachi", "Unknown",       20,
     "Legendary. Dream encounter after seeing 777 unique Pokémon."),

    # Sinnoh creation trio — encounter 1: Sinjoh Ruins (egg, with Arceus)
    ("Dialga",   "Sinjoh Ruins", 1,
     "Legendary. Obtained as Egg with Arceus in party (Mr. Pokemon on Route 30 → Sinjoh Ruins)."),
    ("Palkia",   "Sinjoh Ruins", 1,
     "Legendary. Obtained as Egg with Arceus in party (Mr. Pokemon on Route 30 → Sinjoh Ruins)."),
    ("Giratina", "Sinjoh Ruins", 1,
     "Legendary. Obtained as Egg with Arceus in party (Mr. Pokemon on Route 30 → Sinjoh Ruins)."),
    # Sinnoh creation trio — encounter 2: Strange Vortex post-Mt. Silver (Gold defeated)
    ("Dialga",   "Boon Island",       75,
     "Legendary. Strange Vortex on the highest mountain. Requires Rock Climb and defeating Gold on Mt. Silver."),
    ("Palkia",   "Blackthorn City",   75,
     "Legendary. Strange Vortex near the cave exit. Requires Rock Climb and defeating Gold on Mt. Silver."),
    ("Giratina", "Route 4",           75,
     "Legendary. Strange Vortex near the Mt. Moon exit. Requires Rock Climb and defeating Gold on Mt. Silver."),

    # Lunar duo
    ("Cresselia", "Lavender Town", 50,
     "Legendary. Complex questline starting from Lavender Orphanage."),
    ("Darkrai",   "Lavender Town", 60,
     "Legendary. Complex questline starting from Lavender Orphanage."),

    # Regi quartet
    ("Regigigas", "Submerged Temple", 60,
     "Legendary. Requires all three Regis. Solve type-specific door puzzles."),
    ("Regirock",  "Submerged Temple", 60,
     "Legendary. Requires Rock/Ice fusion to enter door."),
    ("Registeel", "Submerged Temple", 60,
     "Legendary. Requires Steel/Rock fusion to enter door."),
    ("Regice",    "Submerged Temple", 60,
     "Legendary. Requires Ice/Steel fusion to enter door."),

    # Eon duo
    ("Latias", "Sevii Islands", 50,
     "Legendary. Roaming Sevii Islands after TV event on Boon Island."),
    ("Latios", "Sevii Islands", 50,
     "Legendary. Roaming Sevii Islands after TV event on Boon Island."),

    # Mythics
    ("Genesect", "P2 Laboratory",  60,
     "Legendary. Access via Rocket Warehouse on Chrono Island."),
    ("Arceus",   "Hall of Origin", 60,
     "Legendary. Catch Articuno, Zapdos, Moltres, Entei, Raikou, Suicune first."),
    ("Deoxys",   "Birth Island",   70,
     "Legendary. Collect alien spaceship parts from Route 32 and Route 19."),
    ("Necrozma", "Mt. Moon",       70,
     "Legendary. Collect Strange Prisms from multiple locations and follow plant trail."),
    ("Meloetta", "Saffron City",   50,
     "Legendary. Recruit 5 musicians on specific days and times."),
    ("Diancie",  "Pinkan Island",  30,
     "Legendary. Via Pinkan Island quest from Goldenrod City."),
]

# ---------------------------------------------------------------------------
# Gift Pokémon (method='gift')
# ---------------------------------------------------------------------------
GIFTS: list[tuple[str, str, int | None, str]] = [
    # Gen 1 starters — also obtainable as a sibling egg (lv.1) after 4 Gyms.
    # Merged into one entry per species because the DB enforces
    # UNIQUE(pokemon_id, location_id, method); two rows would collide.
    ("Bulbasaur",  "Pallet Town", 5,
     "Starter Pokémon. Also a lv.1 Egg from sibling after 4 Gyms (starter strong against yours)."),
    ("Charmander", "Pallet Town", 5,
     "Starter Pokémon. Also a lv.1 Egg from sibling after 4 Gyms (starter strong against yours)."),
    ("Squirtle",   "Pallet Town", 5,
     "Starter Pokémon. Also a lv.1 Egg from sibling after 4 Gyms (starter strong against yours)."),

    # Step-based PC gift
    ("Porygon", "Any PC", 1,
     "Random chance when total steps divisible by 200 and accessing a PC."),

    # Early game quests
    ("Luvdisc",  "Viridian City", 5,  "Second Playthroughs only."),
    ("Pineco",   "Pewter City",   5,  "Quest Reward."),
    ("Oricorio", "Pewter City",   15, "Quest Reward."),
    ("Magikarp", "Route 3",       5,  "Sold for 500 Pokédollars."),

    # Mt. Moon fossils
    ("Omanyte", "Mt. Moon", None, "Helix Fossil."),
    ("Kabuto",  "Mt. Moon", None, "Dome Fossil."),

    # Route 5 breeder egg (random fusion)
    # Skipped — randomised, no fixed Pokémon name

    # Kanto Daycare eggs
    ("Togepi",   "Kanto Daycare", 1, "Daycare Egg."),
    ("Azurill",  "Kanto Daycare", 1, "Daycare Egg, Pretty Wings quest."),
    ("Pichu",    "Kanto Daycare", 1, "Daycare Egg, Pretty Wings quest."),
    ("Cleffa",   "Kanto Daycare", 1, "Daycare Egg, Pretty Wings quest."),
    ("Igglybuff","Kanto Daycare", 1, "Daycare Egg, Pretty Wings quest."),
    ("Bonsly",   "Kanto Daycare", 1, "Daycare Egg, Heart Scales quest."),
    ("Mantyke",  "Kanto Daycare", 1, "Daycare Egg, Heart Scales quest."),
    ("Happiny",  "Kanto Daycare", 1, "Daycare Egg, Heart Scales quest."),
    ("Elekid",   "Kanto Daycare", 1, "Daycare Egg, Honey quest."),
    ("Magby",    "Kanto Daycare", 1, "Daycare Egg, Honey quest."),
    ("Smoochum", "Kanto Daycare", 1, "Daycare Egg, Honey quest."),

    # Vermillion
    ("Wooper", "Vermillion City", 15, "Quest Reward."),

    # S.S. Anne fossils + sailor gift
    ("Lileep",  "S.S. Anne", None, "Root Fossil. Fossil Maniac 2nd Encounter."),
    ("Anorith", "S.S. Anne", None, "Claw Fossil. Fossil Maniac 2nd Encounter."),
    ("Torkoal", "S.S. Anne", 20,   "From a sailor, after the third Gym."),

    # Pewter City quests
    ("Aerodactyl", "Pewter City", None, "Old Amber. Quest Reward."),

    # Rock Tunnel
    ("Honedge", "Rock Tunnel", 10, ""),
    ("Machop",  "Rock Tunnel",  1, "As Egg. Hiker's Gift."),
    ("Geodude", "Rock Tunnel",  1, "As Egg. Hiker's Gift."),

    # Lavender
    ("Wynaut", "Lavender Town", 1, "As Egg."),

    # Celadon
    ("Eevee", "Celadon City", 20, "Top floor of Celadon Condominiums."),

    # Celadon Game Corner prizes
    ("Abra",    "Celadon Game Corner", 9,  "200 Coins."),
    ("Clefairy","Celadon Game Corner", 14, "750 Coins."),
    ("Pinsir",  "Celadon Game Corner", 18, "4000 Coins."),
    ("Scyther", "Celadon Game Corner", 18, "4000 Coins."),
    ("Dratini", "Celadon Game Corner", 21, "6000 Coins."),
    ("Porygon", "Celadon Game Corner", 24, "9999 Coins."),

    # Celadon Cafe fossils (Fossil Maniac 3rd Encounter)
    ("Cranidos", "Celadon Cafe", None, "Skull Fossil. Fossil Maniac 3rd Encounter."),
    ("Shieldon", "Celadon Cafe", None, "Armor Fossil. Fossil Maniac 3rd Encounter."),

    # Silph Co.
    ("Lapras",    "Silph Co.", 25, ""),
    ("Chikorita", "Silph Co.", 15, "From the President after Silph Co."),
    ("Cyndaquil", "Silph Co.", 15, "From the President after Silph Co."),
    ("Totodile",  "Silph Co.", 15, "From the President after Silph Co."),

    # Saffron Restaurant fossils (Fossil Maniac 4th Encounter)
    ("Tyrunt", "Saffron Restaurant", None, "Jaw Fossil. Fossil Maniac 4th Encounter."),
    ("Amaura", "Saffron Restaurant", None, "Sail Fossil. Fossil Maniac 4th Encounter."),

    # Fighting Dojo
    ("Hitmonchan", "Fighting Dojo", 40, ""),
    ("Hitmonlee",  "Fighting Dojo", 40, ""),
    ("Hitmontop",  "Fighting Dojo", 40, ""),

    # Saffron quest
    ("Smeargle", "Saffron City", 40, "Quest Reward."),

    # Elm's assistant in Goldenrod
    ("Chikorita", "Goldenrod City", 15, "Elm's assistant."),
    ("Cyndaquil", "Goldenrod City", 15, "Elm's assistant."),
    ("Totodile",  "Goldenrod City", 15, "Elm's assistant."),

    # Gen 3 starters from Oak (after 12 Badges, before 16th Badge)
    ("Treecko", "Pallet Town", 5,
     "Professor Oak. After 12 Badges and before 16th Badge."),
    ("Torchic", "Pallet Town", 5,
     "Professor Oak. After 12 Badges and before 16th Badge."),
    ("Mudkip",  "Pallet Town", 5,
     "Professor Oak. After 12 Badges and before 16th Badge."),

    # National Park
    ("Ralts", "National Park", 1, "As Egg."),

    # Johto
    ("Beldum",  "Violet City",    5,  ""),
    ("Lucario", "Blackthorn City", 45, "Quest Reward."),
    ("Gible",   "Dragon's Den",   25, ""),

    # New Bark Town starters
    ("Chikorita", "New Bark Town", 15, ""),
    ("Cyndaquil", "New Bark Town", 15, ""),
    ("Totodile",  "New Bark Town", 15, ""),

    # Sevii Islands
    ("Pawniard", "Knot Island", 1, "As Eggs brought with Heart Scales."),
    ("Bagon",    "Knot Island", 1, "As Eggs brought with Heart Scales."),
    ("Turtwig",  "Kin Island",  20, "Obtain the other two starters you didn't choose."),
    ("Chimchar", "Kin Island",  20, "Obtain the other two starters you didn't choose."),
    ("Piplup",   "Kin Island",  20, "Obtain the other two starters you didn't choose."),
    ("Mareanie", "Bond Bridge", 30, ""),
]

# ---------------------------------------------------------------------------
# NPC Trades (method='trade')
# ---------------------------------------------------------------------------
TRADES: list[tuple[str, str, str]] = [
    # (pokemon_received, location, notes)
    ("Bellsprout", "Viridian City",     "Trade for Spearow."),
    ("Tyrogue",    "Pewter City",        "Trade for Mankey."),
    ("Squirtle",   "Cerulean City",      "Trade for Grass Type. Requires previous trade."),
    ("Bulbasaur",  "Cerulean City",      "Trade for Fire Type. Requires previous trade."),
    ("Charmander", "Cerulean City",      "Trade for Water Type. Requires previous trade."),
    ("Yanma",      "Cerulean City",      "Trade for Paras."),
    ("Poliwag",    "Route 5",            "Trade for Rattata."),
    ("Slowpoke",   "Vermillion City",    "Trade for Meowth. Normal mode only."),
    ("Psyduck",    "Vermillion City",    "Trade for Meowth. Reversed mode only."),
    ("Farfetch'd", "Vermillion City",    "Trade for Spearow."),
    ("Voltorb",    "Vermillion City",    "Trade for Ekans. Fan Club."),
    ("Exeggcute",  "Vermillion City",    "Trade for Voltorb. Fan Club."),
    ("Doduo",      "Vermillion City",    "Trade for Voltorb. Fan Club."),
    ("Seel",       "S.S. Anne",         "Trade for Drowzee."),
    ("Growlithe",  "S.S. Anne",         "Trade for Shellder."),
    ("Mr. Mime",   "Route 2",           "Trade for Abra."),
    ("Mareep",     "Route 11",          "Trade for Venonat."),
    ("Ponyta",     "Celadon City",      "Trade for Raichu."),
    ("Elekid",     "Celadon City",      "Trade for Eevee. Normal mode only."),
    ("Magby",      "Celadon City",      "Trade for Eevee. Reversed mode only."),
    ("Heracross",  "Safari Zone",       "Trade for Pinsir. Area 3."),
    ("Skarmory",   "Cinnabar Island",   "Trade for Dodrio."),
    ("Seel",       "Cinnabar Island",   "Trade for Ponyta. Cinnabar Laboratory."),
    ("Chansey",    "Cinnabar Island",   "Trade for Clefable. Cinnabar Laboratory."),
    ("Electrode",  "Cinnabar Island",   "Trade for Raichu. Cinnabar Laboratory."),
    ("Larvitar",   "Crimson City",      "Trade for Dratini."),
    ("Mudkip",     "Pallet Town",       "Trade for Squirtle. Hoenn Starter."),
    ("Treecko",    "Pallet Town",       "Trade for Bulbasaur. Hoenn Starter."),
    ("Torchic",    "Pallet Town",       "Trade for Charmander. Hoenn Starter."),
    ("Sneasel",    "Goldenrod City",    "Trade for Lickitung."),
    ("Torchic",    "New Bark Town",     "Trade for Cyndaquil. Hoenn Starter strong to Oak's pick."),
    ("Mudkip",     "New Bark Town",     "Trade for Totodile. Hoenn Starter strong to Oak's pick."),
    ("Treecko",    "New Bark Town",     "Trade for Chikorita. Hoenn Starter strong to Oak's pick."),
]

# ---------------------------------------------------------------------------
# Pallet Town inaccessible grass (Easter egg / joke)
# All Gen 1 starters and evolutions + 1% Mew in tall grass that is
# completely inaccessible in normal gameplay.
# ---------------------------------------------------------------------------
PALLET_INACCESSIBLE: list[tuple[str, str]] = [
    # (pokemon_name, encounter_rate)
    ("Bulbasaur",  "5%"),
    ("Ivysaur",    "5%"),
    ("Venusaur",   "5%"),
    ("Charmander", "5%"),
    ("Charmeleon", "5%"),
    ("Charizard",  "5%"),
    ("Squirtle",   "5%"),
    ("Wartortle",  "5%"),
    ("Blastoise",  "5%"),
    ("Mew",        "1%"),
]

# ---------------------------------------------------------------------------
# Wild entries to DELETE (wrong data introduced by earlier ETL runs)
# Tuple: (pokemon_name, location_name, method)
# ---------------------------------------------------------------------------
WILD_CORRECTIONS_DELETE: list[tuple[str, str, str]] = [
    ("Rayquaza", "Route 23", "wild"),
]


def fix_locations(conn) -> None:
    with conn.cursor() as cur:

        # ── Build name → DB id map ────────────────────────────────────────
        cur.execute("SELECT id, name_en FROM pokemon WHERE is_hoenn_only = false")
        by_name: dict[str, int] = {
            name.lower(): db_id for db_id, name in cur.fetchall()
        }
        LOGGER.info("Loaded %d Pokémon names", len(by_name))

        # ── Ensure location rows exist, collect location_id map ───────────
        all_locations: set[str] = set()
        for _, loc, _, _ in LEGENDARIES:
            all_locations.add(loc)
        for _, loc, _, _ in GIFTS:
            all_locations.add(loc)
        for _, loc, _ in TRADES:
            all_locations.add(loc)
        all_locations.add("Pallet Town")

        for loc_name in sorted(all_locations):
            cur.execute(
                "INSERT INTO location (name_en) VALUES (%s) ON CONFLICT (name_en) DO NOTHING",
                (loc_name,),
            )
        conn.commit()

        cur.execute("SELECT id, name_en FROM location")
        loc_map: dict[str, int] = {name: lid for lid, name in cur.fetchall()}

        # ── Remove known incorrect wild entries ───────────────────────────
        for poke_name, loc_name, method in WILD_CORRECTIONS_DELETE:
            pid = by_name.get(poke_name.lower())
            lid = loc_map.get(loc_name)
            if pid and lid:
                cur.execute(
                    "DELETE FROM pokemon_location WHERE pokemon_id=%s AND location_id=%s AND method=%s",
                    (pid, lid, method),
                )
                LOGGER.info("Deleted wrong entry: %s @ %s (%s)", poke_name, loc_name, method)

        # ── Clear old static / gift / trade entries ───────────────────────
        cur.execute("DELETE FROM pokemon_location WHERE method IN ('static', 'gift', 'trade')")
        deleted = cur.rowcount
        LOGGER.info("Cleared %d old static/gift/trade entries", deleted)
        # No commit here: keep the delete + re-inserts in one transaction so a
        # later insert failure rolls back the deletion instead of wiping data.

        # ── Insert legendaries ────────────────────────────────────────────
        leg_ok = leg_skip = 0
        for name, loc_name, level, notes in LEGENDARIES:
            pid = by_name.get(name.lower())
            lid = loc_map.get(loc_name)
            if not pid:
                LOGGER.warning("Pokémon not found: %s", name)
                leg_skip += 1
                continue
            if not lid:
                LOGGER.warning("Location not found: %s", loc_name)
                leg_skip += 1
                continue
            note_parts = []
            if level is not None:
                note_parts.append(f"lv:{level}")
            if notes:
                note_parts.append(notes)
            note_str = " | ".join(note_parts) or None
            cur.execute(
                "INSERT INTO pokemon_location (pokemon_id, location_id, method, notes) "
                "VALUES (%s, %s, 'static', %s) "
                "ON CONFLICT (pokemon_id, location_id, method) DO UPDATE SET notes = EXCLUDED.notes",
                (pid, lid, note_str),
            )
            leg_ok += 1
        LOGGER.info("Legendaries: %d inserted/updated, %d skipped", leg_ok, leg_skip)

        # ── Insert gifts ──────────────────────────────────────────────────
        gift_ok = gift_skip = 0
        for name, loc_name, level, notes in GIFTS:
            pid = by_name.get(name.lower())
            lid = loc_map.get(loc_name)
            if not pid:
                LOGGER.warning("Gift Pokémon not found: %s", name)
                gift_skip += 1
                continue
            if not lid:
                LOGGER.warning("Gift location not found: %s", loc_name)
                gift_skip += 1
                continue
            note_parts = []
            if level is not None:
                note_parts.append(f"lv:{level}")
            if notes:
                note_parts.append(notes)
            note_str = " | ".join(note_parts) or None
            cur.execute(
                "INSERT INTO pokemon_location (pokemon_id, location_id, method, notes) "
                "VALUES (%s, %s, 'gift', %s) "
                "ON CONFLICT (pokemon_id, location_id, method) DO UPDATE SET notes = EXCLUDED.notes",
                (pid, lid, note_str),
            )
            gift_ok += 1
        LOGGER.info("Gifts: %d inserted/updated, %d skipped", gift_ok, gift_skip)

        # ── Insert trades ─────────────────────────────────────────────────
        trade_ok = trade_skip = 0
        for name, loc_name, notes in TRADES:
            pid = by_name.get(name.lower())
            lid = loc_map.get(loc_name)
            if not pid:
                LOGGER.warning("Trade Pokémon not found: %s", name)
                trade_skip += 1
                continue
            if not lid:
                LOGGER.warning("Trade location not found: %s", loc_name)
                trade_skip += 1
                continue
            cur.execute(
                "INSERT INTO pokemon_location (pokemon_id, location_id, method, notes) "
                "VALUES (%s, %s, 'trade', %s) "
                "ON CONFLICT (pokemon_id, location_id, method) DO UPDATE SET notes = EXCLUDED.notes",
                (pid, lid, notes or None),
            )
            trade_ok += 1
        LOGGER.info("Trades: %d inserted/updated, %d skipped", trade_ok, trade_skip)

        # ── Pallet Town inaccessible grass ────────────────────────────────
        pallet_lid = loc_map.get("Pallet Town")
        if pallet_lid:
            pallet_ok = 0
            for name, rate in PALLET_INACCESSIBLE:
                pid = by_name.get(name.lower())
                if not pid:
                    LOGGER.warning("Pallet inaccessible: Pokémon not found: %s", name)
                    continue
                note_str = f"rate:{rate} | Inaccessible tall grass (Easter egg)."
                cur.execute(
                    "INSERT INTO pokemon_location (pokemon_id, location_id, method, notes) "
                    "VALUES (%s, %s, 'wild', %s) "
                    "ON CONFLICT (pokemon_id, location_id, method) DO UPDATE SET notes = EXCLUDED.notes",
                    (pid, pallet_lid, note_str),
                )
                pallet_ok += 1
            LOGGER.info("Pallet Town inaccessible grass: %d entries", pallet_ok)

        conn.commit()
        LOGGER.info("Done — all location fixes committed.")


def main() -> None:
    LOGGER.info("Connecting to PostgreSQL...")
    with pg_connection() as conn:
        fix_locations(conn)


if __name__ == "__main__":
    main()
