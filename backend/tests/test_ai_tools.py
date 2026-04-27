"""Unit tests for the AI tool handlers (backend.services.ai_tools).

Each DB tool is tested in isolation with a real DB session (via the `db`
fixture from conftest.py). The wiki tool is tested with a mocked HTTP client.
No DeepSeek involvement here — the LLM loop is tested separately in test_ai.py.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.services.ai_tools import (
    ASYNC_TOOL_HANDLERS,
    TOOL_HANDLERS,
    TOOL_SPECS,
    dispatch_tool,
)


@pytest.fixture
def db() -> Iterator[Session]:
    """Yield a real DB session (these tests require the populated dev DB)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ─── Spec consistency ────────────────────────────────────────────────────────

def test_tool_specs_match_handlers() -> None:
    """Every declared tool has a handler (sync or async) and vice-versa."""
    spec_names = {s["function"]["name"] for s in TOOL_SPECS}
    handler_names = set(TOOL_HANDLERS.keys()) | set(ASYNC_TOOL_HANDLERS.keys())
    assert spec_names == handler_names, (
        f"Spec/handler mismatch. In specs but not handlers: "
        f"{spec_names - handler_names}. In handlers but not specs: "
        f"{handler_names - spec_names}."
    )


def test_tool_specs_are_valid_openai_schema() -> None:
    """Each spec follows the OpenAI function-calling structure."""
    for spec in TOOL_SPECS:
        assert spec["type"] == "function"
        fn = spec["function"]
        assert "name" in fn and isinstance(fn["name"], str)
        assert "description" in fn and isinstance(fn["description"], str)
        assert "parameters" in fn
        params = fn["parameters"]
        assert params["type"] == "object"
        assert "properties" in params and isinstance(params["properties"], dict)
        assert isinstance(params.get("required", []), list)


# ─── get_pokemon ─────────────────────────────────────────────────────────────

async def test_get_pokemon_by_id(db) -> None:
    result = await dispatch_tool(db, "get_pokemon", {"name_or_id": 25})
    assert result["id"] == 25
    assert result["name_en"] == "Pikachu"
    assert "Electric" in result["types"]
    assert result["stats"]["speed"] == 90


async def test_get_pokemon_by_name(db) -> None:
    result = await dispatch_tool(db, "get_pokemon", {"name_or_id": "Charizard"})
    assert result["name_en"] == "Charizard"
    assert set(result["types"]) >= {"Fire"}


async def test_get_pokemon_not_found(db) -> None:
    result = await dispatch_tool(db, "get_pokemon", {"name_or_id": 999999})
    assert "error" in result


async def test_get_pokemon_missing_arg(db) -> None:
    result = await dispatch_tool(db, "get_pokemon", {})
    assert "error" in result


# ─── get_fusion ──────────────────────────────────────────────────────────────

async def test_get_fusion_pikachu_charizard(db) -> None:
    result = await dispatch_tool(db, "get_fusion", {"head": 25, "body": 6})
    assert result["head"]["name_en"] == "Pikachu"
    assert result["body"]["name_en"] == "Charizard"
    assert "Electric" in result["types"]
    assert result["stats"]["hp"] > 0
    assert isinstance(result["expert_moves"], list)


async def test_get_fusion_heart_scale_prices_exposed(db) -> None:
    """Expert moves carry per-location Heart Scale prices."""
    result = await dispatch_tool(db, "get_fusion", {"head": "Umbreon", "body": "Bulbasaur"})
    assert result.get("expert_moves")
    for m in result["expert_moves"]:
        assert m["prices_heart_scales"]
        for loc, price in m["prices_heart_scales"].items():
            assert price == (2 if loc == "knot_island" else 10)


async def test_get_fusion_invalid_head(db) -> None:
    result = await dispatch_tool(db, "get_fusion", {"head": 999999, "body": 1})
    assert "error" in result
    assert "head" in result["error"]


# ─── search_move ─────────────────────────────────────────────────────────────

async def test_search_move_with_tm_info(db) -> None:
    """TM05 = Roar, taught at Celadon + Route 32."""
    result = await dispatch_tool(db, "search_move", {"name": "Roar"})
    assert result["name_en"] == "Roar"
    assert result["tm"] is not None
    assert result["tm"]["number"] == 5
    loc_names = {l["name_en"] for l in result["tm"]["locations"]}
    assert "Celadon City" in loc_names


async def test_search_move_with_tutors(db) -> None:
    """Bug Bite is taught by a tutor on Route 2 (₽2000)."""
    result = await dispatch_tool(db, "search_move", {"name": "Bug Bite"})
    assert result["tutors"]
    assert any(
        t["location"] == "Route 2" and t["price"] == 2000
        for t in result["tutors"]
    )


async def test_search_move_not_found(db) -> None:
    result = await dispatch_tool(db, "search_move", {"name": "NotARealMoveXYZ"})
    assert "error" in result


# ─── get_item ────────────────────────────────────────────────────────────────

async def test_get_item_heart_scale(db) -> None:
    result = await dispatch_tool(db, "get_item", {"name": "Heart Scale"})
    assert result["name_en"] == "Heart Scale"
    assert result["category"] == "valuable"
    assert result["price_buy"] == 5000
    assert result["price_sell"] == 50


async def test_get_item_fire_stone(db) -> None:
    result = await dispatch_tool(db, "get_item", {"name": "Fire Stone"})
    assert result["category"] == "evolution"
    assert result["price_buy"] == 5000


async def test_get_item_not_found(db) -> None:
    result = await dispatch_tool(db, "get_item", {"name": "NotARealItem"})
    assert "error" in result


# ─── get_move_tutors ─────────────────────────────────────────────────────────

async def test_get_move_tutors_bug_bite(db) -> None:
    result = await dispatch_tool(db, "get_move_tutors", {"move_name": "Bug Bite"})
    assert result["move"]["name_en"] == "Bug Bite"
    assert len(result["tutors"]) == 1
    t = result["tutors"][0]
    assert t["location"] == "Route 2"
    assert t["currency"] == "pokedollars"
    assert t["price"] == 2000


async def test_get_move_tutors_empty(db) -> None:
    """Most moves have no classical tutor — empty list, not 404."""
    result = await dispatch_tool(db, "get_move_tutors", {"move_name": "Pound"})
    assert "move" in result
    assert result["tutors"] == []


# ─── search_wiki ─────────────────────────────────────────────────────────────

async def test_search_wiki_found(db) -> None:
    """When wiki returns a result, payload has found=True + title + extract."""
    fake_response = {
        "found": True,
        "title": "Safari Zone",
        "url": "https://infinitefusion.fandom.com/wiki/Safari_Zone",
        "extract": "The Safari Zone is a special area...",
        "other_results": [],
    }
    with patch(
        "backend.services.ai_tools.fetch_wiki",
        new=AsyncMock(return_value=fake_response),
    ):
        result = await dispatch_tool(db, "search_wiki", {"query": "Safari Zone"})

    assert result["found"] is True
    assert result["title"] == "Safari Zone"
    assert "extract" in result


async def test_search_wiki_not_found(db) -> None:
    """When wiki finds nothing, payload has found=False."""
    with patch(
        "backend.services.ai_tools.fetch_wiki",
        new=AsyncMock(return_value={"found": False, "query": "xyzzy"}),
    ):
        result = await dispatch_tool(db, "search_wiki", {"query": "xyzzy"})

    assert result["found"] is False


async def test_search_wiki_missing_arg(db) -> None:
    result = await dispatch_tool(db, "search_wiki", {})
    assert "error" in result


async def test_search_wiki_timeout(db) -> None:
    """Network timeout is surfaced as found=False with error key."""
    with patch(
        "backend.services.ai_tools.fetch_wiki",
        new=AsyncMock(return_value={"found": False, "error": "Wiki request timed out"}),
    ):
        result = await dispatch_tool(db, "search_wiki", {"query": "anything"})

    assert result["found"] is False
    assert "error" in result


# ─── dispatch_tool safety ────────────────────────────────────────────────────

async def test_dispatch_unknown_tool(db) -> None:
    result = await dispatch_tool(db, "nonexistent_tool", {})
    assert "error" in result
    assert "Unknown tool" in result["error"]
