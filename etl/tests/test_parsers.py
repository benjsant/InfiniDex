"""Unit tests for the fragile *pure* ETL parsers.

These lock the regression classes that bit us in production:
  - extract_pokedex_if: the wiki restructure added a `form` field after the
    name — an old-format regex shifts every field left (Bulbasaur becomes
    Grass/(none)). Fixtures below use the current 8-field template.
  - extract_pokedex_if: form label leaking into type1 with the real type in
    type2 → must be promoted (PR #69, kept as a safety net).
  - extract_pokedex_if: Hoenn-only flag from the Kanto/Hoenn page diff (the
    restructure dropped the per-row "Not in game" markers).
  - the unique-IF triple-fusion type splitter.
  - the Pokepedia→PokeAPI move-name alias/normalize layer.

Pure functions only — no DB, no network. Run from the repo root:
    uv run --project etl --with pytest python -m pytest etl/tests -q
"""

from __future__ import annotations

from etl.scripts.extract_pokedex_if import mark_hoenn_only, parse_entries
from etl.scripts.load_triple_fusions import split_type_string
from etl.scripts.transform_merge_movesets import apply_alias, normalize


def _entry(idx, if_id, name, t1, t2, form="", loc="Somewhere", notes=""):
    """Current wiki template: {{PokedexTable/Data|index|id|name|form|t1|t2|loc|notes}}."""
    return f"{{{{PokedexTable/Data|{idx}|{if_id}|{name}|{form}|{t1}|{t2}|{loc}|{notes}}}}}"


def _by_id(wikitext):
    return {e["if_id"]: e for e in parse_entries(wikitext)}


def test_pokedex_normal_dual_type():
    e = _by_id(_entry(1, 1, "Bulbasaur", "Grass", "Poison"))[1]
    assert e["name_en"] == "Bulbasaur"
    assert e["type1"] == "grass"
    assert e["type2"] == "poison"


def test_pokedex_mono_type_empty_type2():
    e = _by_id(_entry(4, 4, "Charmander", "Fire", ""))[4]
    assert e["type1"] == "fire"
    assert e["type2"] is None


def test_pokedex_form_field_captured_not_polluting():
    """The form field is captured as-is and must not pollute name or types."""
    e = _by_id(_entry(430, 430, "Oricorio", "Fire", "Flying", form="Baile Style"))[430]
    assert e["name_en"] == "Oricorio"
    assert e["form"] == "Baile Style"
    assert e["type1"] == "fire"
    assert e["type2"] == "flying"


def test_pokedex_no_form_is_none():
    e = _by_id(_entry(1, 1, "Bulbasaur", "Grass", "Poison"))[1]
    assert e["form"] is None


def test_form_slug_mapping():
    """Every known wiki form resolves to a PokeAPI slug (apostrophe variants included)."""
    from etl.scripts.fix_form_pokemon import form_slug
    assert form_slug("Oricorio", "Pom-Pom Style") == "oricorio-pom-pom"
    assert form_slug("Oricorio", "Pa’u Style") == "oricorio-pau"   # curly apostrophe
    assert form_slug("Lycanroc", "Midnight Form") == "lycanroc-midnight"
    assert form_slug("Castform", "Snowy") == "castform-snowy"
    assert form_slug("Oricorio", "Unknown New Style") is None


def test_pokedex_form_label_in_type1_is_promoted():
    """Regression PR #69: form name leaking into type1, real type in type2."""
    e = _by_id(_entry(431, 431, "Oricorio", "Pom-Pom Style", "Electric"))[431]
    assert e["type1"] == "electric"   # promoted from type2
    assert e["type2"] is None


def test_pokedex_invalid_type1_no_valid_type2_stays_none():
    e = _by_id(_entry(999, 999, "Glitch", "Banana", ""))[999]
    assert e["type1"] is None
    assert e["type2"] is None


def test_pokedex_hoenn_only_flag_from_notes():
    """Legacy per-row marker — kept as a safety net."""
    e = _by_id(_entry(600, 600, "Treecko", "Grass", "", notes="Not in game"))[600]
    assert e["is_hoenn_only"] is True


def test_pokedex_hoenn_only_flag_from_kanto_diff():
    """Post-restructure: an id absent from the Kanto page is Hoenn-only."""
    entries = parse_entries(
        _entry(1, 1, "Bulbasaur", "Grass", "Poison")
        + _entry(502, 502, "Treecko", "Grass", "")
    )
    flagged = mark_hoenn_only(entries, kanto_ids={1})
    by_id = {e["if_id"]: e for e in entries}
    assert flagged == 1
    assert by_id[1]["is_hoenn_only"] is False
    assert by_id[502]["is_hoenn_only"] is True


def test_pokedex_empty_page_parses_to_nothing():
    """The hub page holds no data — parse_entries must return [] (main() raises)."""
    assert parse_entries("Some hub page linking to [[Pokédex/Hoenn/Classic]]") == []


def test_split_type_string_unique_if_type_single_slot():
    assert split_type_string("Fire/Water/Electric") == ["Fire/Water/Electric"]


def test_split_type_string_bracketed_unique_plus_standard():
    assert split_type_string("[Ice/Fire/Electric]/Flying") == ["Ice/Fire/Electric", "Flying"]
    assert split_type_string("Dragon/[Ghost/Steel/Water]") == ["Dragon", "Ghost/Steel/Water"]


def test_split_type_string_plain_dual_and_empty():
    assert split_type_string("Grass/Poison") == ["Grass", "Poison"]
    assert split_type_string("") == []


def test_transform_apply_alias():
    assert apply_alias("Poing de Feu") == "Poing Feu"          # known old name
    assert apply_alias("Grâce à sa capacité") is None          # artefact → discard
    assert apply_alias("Charge") == "Charge"                   # unknown → passthrough


def test_transform_normalize():
    assert normalize("Cage-Éclair") == "cage éclair"           # hyphen→space, lower
    assert normalize("D’Eau") == "d'eau"                   # curly → straight apostrophe
