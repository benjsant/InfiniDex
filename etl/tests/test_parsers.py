"""Unit tests for the fragile *pure* ETL parsers.

These lock the regression classes that bit us in production:
  - extract_pokedex_if: alt-form rows put the form name in the type1
    column and the real type in type2 → must be promoted (PR #69).
  - the unique-IF triple-fusion type splitter.
  - the Pokepedia→PokeAPI move-name alias/normalize layer.

Pure functions only — no DB, no network. Run from the repo root:
    uv run --project etl --with pytest python -m pytest etl/tests -q
"""

from __future__ import annotations

from etl.scripts.extract_pokedex_if import parse_entries
from etl.scripts.load_triple_fusions import split_type_string
from etl.scripts.transform_merge_movesets import apply_alias, normalize


def _entry(idx, if_id, name, t1, t2, loc="Somewhere", notes=""):
    return f"{{{{PokedexTable/Data|{idx}|{if_id}|{name}|{t1}|{t2}|{loc}|{notes}}}}}"


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


def test_pokedex_form_label_in_type1_is_promoted():
    """Regression PR #69: form name in type1, real type in type2."""
    e = _by_id(_entry(431, 431, "Oricorio", "Pom-Pom Style", "Electric"))[431]
    assert e["type1"] == "electric"   # promoted from type2
    assert e["type2"] is None


def test_pokedex_invalid_type1_no_valid_type2_stays_none():
    e = _by_id(_entry(999, 999, "Glitch", "Banana", ""))[999]
    assert e["type1"] is None
    assert e["type2"] is None


def test_pokedex_hoenn_only_flag_from_notes():
    e = _by_id(_entry(600, 600, "Treecko", "Grass", "", notes="Not in game"))[600]
    assert e["is_hoenn_only"] is True


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
