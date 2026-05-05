"""DuckDuckGo web search service — last-resort fallback after DB + wiki.

Used only when both database tools and search_wiki return nothing useful.
Results are cached for _CACHE_TTL seconds to avoid hammering DDG.
"""

from __future__ import annotations

import asyncio
import logging
import time

from duckduckgo_search import DDGS

LOGGER = logging.getLogger(__name__)

MAX_RESULTS          = 5
MAX_CHARS_PER_RESULT = 300   # per snippet, before capping total
MAX_TOTAL_CHARS      = 1_500  # total returned to the LLM
HTTP_TIMEOUT         = 8.0
_CACHE_TTL           = 300   # 5 min (web results change faster than wiki)

_web_cache: dict[str, tuple[float, dict]] = {}


async def search_web(query: str) -> dict:
    """Search DuckDuckGo and return the top text results.

    Results are cached in-process for _CACHE_TTL seconds.

    Returns:
        dict with keys:
        - ``found`` (bool)
        - ``results`` — list of {title, url, snippet} dicts (if found)
        - On error: ``{"found": False, "error": "<message>"}``
    """
    cache_key = query.strip().lower()
    cached = _web_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL:
        LOGGER.debug("web cache hit for query=%r", query)
        return cached[1]

    try:
        def _sync_search() -> list[dict]:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=MAX_RESULTS))

        raw = await asyncio.to_thread(_sync_search)

        if not raw:
            result: dict = {"found": False, "query": query}
            _web_cache[cache_key] = (time.monotonic(), result)
            return result

        results = []
        total_chars = 0
        for r in raw:
            snippet = (r.get("body") or "")[:MAX_CHARS_PER_RESULT]
            total_chars += len(snippet)
            results.append({
                "title":   r.get("title", ""),
                "url":     r.get("href", ""),
                "snippet": snippet,
            })
            if total_chars >= MAX_TOTAL_CHARS:
                break

        result = {"found": True, "results": results}
        _web_cache[cache_key] = (time.monotonic(), result)
        return result

    except Exception as exc:
        LOGGER.warning("Web search error for query=%r: %s", query, exc)
        return {"found": False, "error": f"Web search failed: {exc}"}
