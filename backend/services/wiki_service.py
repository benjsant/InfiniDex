"""MediaWiki client pour le wiki Infinite Fusion (infinitefusion.fandom.com).

Utilisé comme fallback par le tool `search_wiki` lorsque la BDD locale
ne couvre pas la question (mécaniques de jeu, lore, patches, etc.).

L'API MediaWiki est publique, sans clé. On limite l'extract à 2 000
caractères pour éviter l'explosion de tokens dans la fenêtre de contexte
du LLM.
"""

from __future__ import annotations

import logging

import httpx

LOGGER = logging.getLogger(__name__)

WIKI_API_URL = "https://infinitefusion.fandom.com/api.php"
MAX_EXTRACT_CHARS = 2_000
HTTP_TIMEOUT = 8.0


async def fetch_wiki(query: str) -> dict:
    """Search the Infinite Fusion wiki and return the best page's intro extract.

    Returns:
        dict with keys:
          - ``found`` (bool)
          - ``title``, ``url``, ``extract`` (if found)
          - ``other_results`` — list of alternative page titles (if found)
          On HTTP/network error: ``{"found": False, "error": "<message>"}``
    """
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            # 1. Search for matching pages.
            search_resp = await client.get(
                WIKI_API_URL,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": 3,
                    "format": "json",
                },
            )
            search_resp.raise_for_status()
            results = search_resp.json().get("query", {}).get("search", [])

            if not results:
                return {"found": False, "query": query}

            # 2. Fetch the plain-text intro extract of the best result.
            title = results[0]["title"]
            extract_resp = await client.get(
                WIKI_API_URL,
                params={
                    "action": "query",
                    "prop": "extracts",
                    "titles": title,
                    "exintro": 1,
                    "explaintext": 1,
                    "format": "json",
                },
            )
            extract_resp.raise_for_status()
            pages = extract_resp.json().get("query", {}).get("pages", {})
            page = next(iter(pages.values()))
            extract = (page.get("extract") or "").strip()

            if len(extract) > MAX_EXTRACT_CHARS:
                extract = extract[:MAX_EXTRACT_CHARS] + "…"

            return {
                "found": True,
                "title": title,
                "url": f"https://infinitefusion.fandom.com/wiki/{title.replace(' ', '_')}",
                "extract": extract,
                "other_results": [r["title"] for r in results[1:]],
            }

    except httpx.TimeoutException:
        LOGGER.warning("Wiki fetch timeout for query=%r", query)
        return {"found": False, "error": "Wiki request timed out"}
    except httpx.HTTPError as exc:
        LOGGER.warning("Wiki HTTP error for query=%r: %s", query, exc)
        return {"found": False, "error": f"Wiki HTTP error: {exc}"}
