"""Unit tests for the source-watchdog helpers — pure functions, no network."""

from __future__ import annotations

from etl.flows.pokedex_watcher import POKEDEX_PAGE, _ENTRY_RE
from etl.scripts.check_sources import parse_game_version
from etl.scripts.extract_sprites import count_sprite_entries


def test_parse_game_version_reads_settings_rb():
    settings = """
module Settings
  LATEST_GAME_RELEASE = "6.8.0"
  VERSION_FILE_URL = "https://example/VERSION"
end
"""
    assert parse_game_version(settings) == "6.8.0"


def test_parse_game_version_missing_returns_none():
    assert parse_game_version("module Settings\nend\n") is None


def test_watcher_targets_the_subpage_not_the_hub():
    """Regression: the hub page "Pokédex" holds no data since the restructure."""
    assert POKEDEX_PAGE != "Pokédex"
    assert POKEDEX_PAGE.startswith("Pokédex/")


def test_watcher_regex_handles_the_form_field():
    """The `form` field sits after the name, so id/name capture is unaffected."""
    line = "{{PokedexTable/Data|430|430|Oricorio|Baile Style|Fire|Flying|TBA||}}"
    m = _ENTRY_RE.search(line)
    assert m is not None
    assert int(m.group("id")) == 430
    assert m.group("name") == "Oricorio"


def test_watcher_regex_handles_a_plain_row():
    line = "{{PokedexTable/Data|1|001|Bulbasaur||Grass|Poison|TBA||}}"
    m = _ENTRY_RE.search(line)
    assert m is not None
    assert int(m.group("id")) == 1
    assert m.group("name") == "Bulbasaur"


def test_count_sprite_entries_counts_only_png_lines():
    listing = """
1.1.png
25.6.png
25.6a.png

# commentaire ou entête
README.md
"""
    assert count_sprite_entries(listing) == 3


def test_count_sprite_entries_empty_listing():
    assert count_sprite_entries("") == 0
