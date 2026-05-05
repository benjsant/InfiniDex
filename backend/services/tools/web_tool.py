"""Web search tool — DuckDuckGo fallback of last resort."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.services.tools._base import Tool
from backend.services.web_service import search_web as _do_search


async def _search_web(db: Session, args: dict) -> dict:
    query = args.get("query")
    if not query:
        return {"error": "Missing required arg 'query'"}
    return await _do_search(str(query))


search_web_tool = Tool(
    name="search_web",
    description=(
        "Last-resort web search via DuckDuckGo. "
        "Use ONLY if both the database tools AND search_wiki returned nothing "
        "useful for the question. Do not use for Pokémon stats, moves, items, "
        "fusions, or anything the DB covers — use the dedicated tools instead. "
        "Queries must be in English. Returns up to 5 results (title, url, snippet)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Precise English search query. "
                    "E.g.: 'Pokémon Infinite Fusion randomizer how to enable', "
                    "'infinite fusion android download', "
                    "'infinite fusion discord server'"
                ),
            }
        },
        "required": ["query"],
    },
    handler=_search_web,
)
