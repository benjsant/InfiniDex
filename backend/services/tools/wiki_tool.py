"""Wiki tool — searches the Infinite Fusion wiki via MediaWiki API."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.services.tools._base import Tool
from backend.services.wiki_service import fetch_wiki


async def _search_wiki(db: Session, args: dict) -> dict:
    query = args.get("query")
    if not query:
        return {"error": "Missing required arg 'query'"}
    return await fetch_wiki(str(query))


search_wiki_tool = Tool(
    name="search_wiki",
    description=(
        "Search a page on the official Pokémon Infinite Fusion wiki "
        "(infinitefusion.fandom.com). Use when the DB tools do not "
        "cover the question: game mechanics, lore, quests, patches, "
        "fan-game-specific features. Returns the intro of the best "
        "matching page found."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Search terms in English (the wiki is in EN). "
                    "E.g.: 'Safari Zone', 'Wonder Trade', 'Randomizer mode'"
                ),
            }
        },
        "required": ["query"],
    },
    handler=_search_wiki,
)
