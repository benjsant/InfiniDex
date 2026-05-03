"""Web search tool — DuckDuckGo fallback (last resort in the cascade)."""

from __future__ import annotations

import asyncio
import logging

from ddgs import DDGS

from backend.services.tools._base import Tool

LOGGER = logging.getLogger(__name__)

_MAX_RESULTS = 3
_SNIPPET_LEN = 400


def _sync_search(query: str) -> list[dict]:
    return list(DDGS().text(query, max_results=_MAX_RESULTS))


async def _search_web(_db, args: dict) -> dict:
    query = args.get("query")
    if not query:
        return {"error": "Missing required arg 'query'"}

    scoped = f"{query} Pokémon Infinite Fusion"
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _sync_search, scoped)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("web search failed query=%r: %s", query, exc)
        return {"found": False, "query": query, "reason": str(exc)}

    if not results:
        return {"found": False, "query": query}

    return {
        "found": True,
        "query": query,
        "results": [
            {
                "title":   r.get("title", ""),
                "snippet": r.get("body", "")[:_SNIPPET_LEN],
                "url":     r.get("href", ""),
            }
            for r in results
        ],
    }


search_web_tool = Tool(
    name="search_web",
    description=(
        "Last-resort web search via DuckDuckGo. "
        "Call ONLY if BOTH the database tools AND search_wiki returned no useful information. "
        "Searches the web scoped to Pokémon Infinite Fusion. Returns up to 3 result snippets. "
        "Do NOT use for data already in the database (Pokémon stats, moves, fusions, items)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Search query in English, e.g. 'Wonder Trade mechanics', "
                    "'debug mode cheats', 'Safari Zone unlock'"
                ),
            }
        },
        "required": ["query"],
    },
    handler=_search_web,
)
