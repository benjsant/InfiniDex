"""Tests for the MediaWiki template parser and the 2026-09 wiki additions."""

from __future__ import annotations

from etl.scripts.extract_pokedex_if import extract_ids, parse_entries
from etl.scripts.fix_form_pokemon import form_slug, is_form_row
from etl.utils.wikitext import parse_template_calls

# Real rows from Pokédex/Hoenn/Classic (2026-09), including the two using a
# named param that made the old regex swallow the following Gastrodon rows.
SEPT_ROWS = """
{{PokedexTable/Data|572|572|Dragalge||Poison|Dragon|Evolve Skrelp (Lv48)||}}
{{PokedexTable/Data|573|573|Shellos|East|Water|7=Route 119 (Egg, Team Aqua)}}
{{PokedexTable/Data|574|574|Gastrodon|East|Water|Ground|Evolve Shellos East (Lv30)}}
{{PokedexTable/Data|575|575|Shellos|West|Water|7=Route 119 (Egg, Team Magma)}}
{{PokedexTable/Data|576|576|Gastrodon|West|Water|Ground|Evolve Shellos West (Lv30)}}
{{PokedexTable/Data|578|578|Tornadus (Therian)||Flying||TBA||}}
"""


def test_named_param_does_not_swallow_next_row():
    by_id = {e["if_id"]: e for e in parse_entries(SEPT_ROWS)}
    assert sorted(by_id) == [572, 573, 574, 575, 576, 578]
    assert by_id[574]["name_en"] == "Gastrodon"
    assert (by_id[574]["type1"], by_id[574]["type2"]) == ("water", "ground")


def test_named_param_lands_in_its_position():
    shellos = {e["if_id"]: e for e in parse_entries(SEPT_ROWS)}[573]
    assert shellos["form"] == "East"
    assert shellos["type1"] == "water"
    assert shellos["type2"] is None
    assert shellos["location_raw"] == "Route 119 (Egg, Team Aqua)"


def test_extract_ids_counts_every_row():
    assert extract_ids(SEPT_ROWS) == {572, 573, 574, 575, 576, 578}


def test_wikilink_pipes_stay_inside_their_argument():
    calls = parse_template_calls(
        "{{PokedexTable/Data|31|031|Nidoqueen||Poison|Ground|"
        "Evolve Nidorina ([[List of Items|Moon Stone]])||}}",
        "PokedexTable/Data",
    )
    assert calls[0][7] == "Evolve Nidorina ([[List of Items|Moon Stone]])"
    assert calls[0][8] == ""


def test_other_templates_with_same_prefix_are_ignored():
    assert parse_template_calls("{{PokedexTable/DataHeader}}", "PokedexTable/Data") == []


def test_new_forms_are_mapped():
    assert form_slug("Shellos", "West") == "shellos"
    assert form_slug("Gastrodon", "East") == "gastrodon"
    assert form_slug("Tornadus (Therian)", None) == "tornadus-therian"
    assert form_slug("Landorus (Therian)", "") == "landorus-therian"


def test_form_row_detection_covers_both_conventions():
    assert is_form_row({"name_en": "Oricorio", "form": "Sensu Style"})
    assert is_form_row({"name_en": "Thundurus (Therian)", "form": None})
    assert not is_form_row({"name_en": "Thundurus", "form": None})
