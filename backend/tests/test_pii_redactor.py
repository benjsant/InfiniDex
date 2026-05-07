"""Unit tests for backend.services.pii_redactor."""

from backend.services.pii_redactor import redact


# ─── Key removal ─────────────────────────────────────────────────────────────

def test_removes_creator_key() -> None:
    payload = {"name_en": "Bulbasaur", "creator": "JohnDoe#1234"}
    assert "creator" not in redact(payload)


def test_removes_creators_list() -> None:
    payload = {"id": 1, "creators": ["Alice", "Bob"]}
    result = redact(payload)
    assert "creators" not in result
    assert result["id"] == 1


def test_removes_nested_creator_keys() -> None:
    payload = {
        "fusion": {
            "head": "Bulbasaur",
            "creator_name": "Spritemaker99",
            "stats": {"hp": 45},
        }
    }
    fusion = redact(payload)["fusion"]
    assert "creator_name" not in fusion
    assert fusion["stats"]["hp"] == 45


def test_removes_username_key() -> None:
    payload = {"username": "artist_bob", "move": "Tackle"}
    result = redact(payload)
    assert "username" not in result
    assert result["move"] == "Tackle"


def test_removes_discord_name_key() -> None:
    result = redact({"discord_name": "foo#4321", "id": 7})
    assert "discord_name" not in result


def test_removes_author_key() -> None:
    result = redact({"author": "SomeUser", "title": "page"})
    assert "author" not in result
    assert result["title"] == "page"


# ─── String-value sanitisation ───────────────────────────────────────────────

def test_redacts_discord_tag_in_string() -> None:
    payload = {"snippet": "Sprite by JohnDoe#4242, enjoy!"}
    result = redact(payload)
    assert "#4242" not in result["snippet"]
    assert "[redacted]" in result["snippet"]


def test_redacts_at_mention_in_string() -> None:
    payload = {"notes": "Contact @spritemaster for more info."}
    result = redact(payload)
    assert "@spritemaster" not in result["notes"]
    assert "[redacted]" in result["notes"]


def test_preserves_normal_strings() -> None:
    payload = {"name_en": "Charizard", "location": "Mt. Ember"}
    result = redact(payload)
    assert result["name_en"] == "Charizard"
    assert result["location"] == "Mt. Ember"


def test_redacts_discord_tag_in_nested_list() -> None:
    payload = {"results": [{"snippet": "made by User#0001"}, {"snippet": "no pii here"}]}
    results = redact(payload)["results"]
    assert "[redacted]" in results[0]["snippet"]
    assert results[1]["snippet"] == "no pii here"


# ─── Edge cases ──────────────────────────────────────────────────────────────

def test_passthrough_none() -> None:
    assert redact(None) is None


def test_passthrough_int() -> None:
    assert redact(42) == 42


def test_passthrough_bool() -> None:
    assert redact(True) is True


def test_empty_dict() -> None:
    assert redact({}) == {}


def test_empty_list() -> None:
    assert redact([]) == []


def test_no_mutation_of_input() -> None:
    original = {"creator": "abc", "name_en": "Pikachu"}
    _ = redact(original)
    assert "creator" in original  # input must not be mutated


def test_multiple_at_mentions_in_one_string() -> None:
    s = "Thanks to @alice and @bob for the sprites."
    result = redact({"text": s})["text"]
    assert "@alice" not in result
    assert "@bob" not in result


def test_real_tool_result_safe() -> None:
    """Simulates a typical DB tool result — nothing should be redacted."""
    payload = {
        "id": 6,
        "name_en": "Charizard",
        "name_fr": "Dracaufeu",
        "types": ["Fire", "Flying"],
        "abilities": [{"name_en": "Blaze", "is_hidden": False}],
        "stats": {"hp": 78, "attack": 84},
        "locations": [{"location": "Mt. Ember", "method": "static"}],
    }
    result = redact(payload)
    assert result["name_en"] == "Charizard"
    assert result["types"] == ["Fire", "Flying"]
    assert result["abilities"][0]["name_en"] == "Blaze"
