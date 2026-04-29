"""Unit tests for the agent tools package (backend.services.tools).

DB tools are tested with a real session (require the populated dev DB).
The wiki tool is tested with a mocked HTTP client.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.services.tools import TOOL_SPECS, TOOLS, dispatch_tool


@pytest.fixture
def db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ─── Spec consistency ────────────────────────────────────────────────────────

def test_every_tool_has_unique_name() -> None:
    names = [t.name for t in TOOLS]
    assert len(names) == len(set(names)), "Duplicate tool names detected"


def test_tool_specs_match_tools() -> None:
    """TOOL_SPECS is generated from TOOLS — they must stay in sync."""
    spec_names = {s["function"]["name"] for s in TOOL_SPECS}
    tool_names = {t.name for t in TOOLS}
    assert spec_names == tool_names


def test_tool_specs_are_valid_openai_schema() -> None:
    for spec in TOOL_SPECS:
        assert spec["type"] == "function"
        fn = spec["function"]
        assert isinstance(fn["name"], str)
        assert isinstance(fn["description"], str)
        params = fn["parameters"]
        assert params["type"] == "object"
        assert isinstance(params["properties"], dict)
        assert isinstance(params.get("required", []), list)


def test_all_tools_have_callable_handler() -> None:
    import asyncio
    for tool in TOOLS:
        assert callable(tool.handler), f"{tool.name} handler is not callable"


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
    assert "Fire" in result["types"]


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


async def test_get_fusion_heart_scale_prices(db) -> None:
    result = await dispatch_tool(db, "get_fusion", {"head": "Umbreon", "body": "Bulbasaur"})
    assert result.get("expert_moves")
    for m in result["expert_moves"]:
        for loc, price in m["prices_heart_scales"].items():
            assert price == (2 if loc == "knot_island" else 10)


async def test_get_fusion_invalid_head(db) -> None:
    result = await dispatch_tool(db, "get_fusion", {"head": 999999, "body": 1})
    assert "error" in result
    assert "head" in result["error"]


async def test_get_fusion_invalid_body(db) -> None:
    result = await dispatch_tool(db, "get_fusion", {"head": 1, "body": 999999})
    assert "error" in result
    assert "body" in result["error"]


# ─── search_move ─────────────────────────────────────────────────────────────

async def test_search_move_with_tm(db) -> None:
    result = await dispatch_tool(db, "search_move", {"name": "Roar"})
    assert result["name_en"] == "Roar"
    assert result["tm"]["number"] == 5
    assert "Celadon City" in {l["name_en"] for l in result["tm"]["locations"]}


async def test_search_move_with_tutors(db) -> None:
    result = await dispatch_tool(db, "search_move", {"name": "Bug Bite"})
    assert any(t["location"] == "Route 2" and t["price"] == 2000 for t in result["tutors"])


async def test_search_move_not_found(db) -> None:
    result = await dispatch_tool(db, "search_move", {"name": "NotARealMoveXYZ"})
    assert "error" in result


# ─── get_item ────────────────────────────────────────────────────────────────

async def test_get_item_heart_scale(db) -> None:
    result = await dispatch_tool(db, "get_item", {"name": "Heart Scale"})
    assert result["name_en"] == "Heart Scale"
    assert result["price_buy"] == 5000


async def test_get_item_not_found(db) -> None:
    result = await dispatch_tool(db, "get_item", {"name": "NotARealItem"})
    assert "error" in result


# ─── get_move_tutors ─────────────────────────────────────────────────────────

async def test_get_move_tutors_bug_bite(db) -> None:
    result = await dispatch_tool(db, "get_move_tutors", {"move_name": "Bug Bite"})
    assert result["move"]["name_en"] == "Bug Bite"
    t = result["tutors"][0]
    assert t["location"] == "Route 2"
    assert t["price"] == 2000


async def test_get_move_tutors_empty(db) -> None:
    result = await dispatch_tool(db, "get_move_tutors", {"move_name": "Pound"})
    assert result["tutors"] == []


# ─── search_wiki ─────────────────────────────────────────────────────────────

async def test_search_wiki_found(db) -> None:
    fake = {
        "found": True, "title": "Safari Zone",
        "url": "https://infinitefusion.fandom.com/wiki/Safari_Zone",
        "extract": "The Safari Zone is a special area...",
        "other_results": [],
    }
    with patch("backend.services.tools.wiki_tool.fetch_wiki", new=AsyncMock(return_value=fake)):
        result = await dispatch_tool(db, "search_wiki", {"query": "Safari Zone"})
    assert result["found"] is True
    assert "extract" in result


async def test_search_wiki_not_found(db) -> None:
    with patch(
        "backend.services.tools.wiki_tool.fetch_wiki",
        new=AsyncMock(return_value={"found": False, "query": "xyzzy"}),
    ):
        result = await dispatch_tool(db, "search_wiki", {"query": "xyzzy"})
    assert result["found"] is False


async def test_search_wiki_missing_arg(db) -> None:
    result = await dispatch_tool(db, "search_wiki", {})
    assert "error" in result


# ─── dispatch safety ─────────────────────────────────────────────────────────

async def test_dispatch_unknown_tool(db) -> None:
    result = await dispatch_tool(db, "nonexistent_tool", {})
    assert "error" in result
    assert "Unknown tool" in result["error"]
