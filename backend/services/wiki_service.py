"""MediaWiki client pour le wiki Infinite Fusion (infinitefusion.fandom.com).

Utilisé comme fallback par le tool `search_wiki` lorsque la BDD locale
ne couvre pas la question (mécaniques de jeu, lore, patches, etc.).

L'API MediaWiki est publique, sans clé. On utilise `action=parse&prop=wikitext`
(prop=extracts retourne vide sur ce wiki Fandom) puis on strip le markup wiki.
L'extract est limité à MAX_EXTRACT_CHARS pour éviter l'explosion de tokens.
"""

from __future__ import annotations

import logging
import re

import httpx

LOGGER = logging.getLogger(__name__)

WIKI_API_URL = "https://infinitefusion.fandom.com/api.php"
MAX_EXTRACT_CHARS = 2_000
HTTP_TIMEOUT = 8.0


def _strip_wiki_markup(text: str) -> str:
    """Convert wikitext to plain text (best-effort, not a full parser)."""
    text = re.sub(r"\{\{[^}]*\}\}", "", text)                            # templates
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)       # [[link|label]]
    text = re.sub(r"'{2,3}", "", text)                                   # bold/italic
    text = re.sub(r"==+[^=]*==+", "", text)                              # == headers ==
    text = re.sub(r"<[^>]+>", "", text)                                  # HTML tags
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def fetch_wiki(query: str) -> dict:
    """Search the Infinite Fusion wiki and return the best page's intro.

    Uses action=parse with section=0 (intro) then falls back to the full
    page when the intro is empty (some pages have no lead section).

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

            title = results[0]["title"]

            # 2. Fetch intro section (section=0) wikitext, strip markup.
            extract = await _fetch_section(client, title, section=0)

            # 3. If intro is empty, grab the full page and truncate.
            if not extract:
                extract = await _fetch_section(client, title, section=None)

            if not extract:
                return {
                    "found": False,
                    "query": query,
                    "note": f"Page '{title}' trouvée mais contenu illisible",
                }

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


async def _fetch_section(
    client: httpx.AsyncClient,
    title: str,
    section: int | None,
) -> str:
    """Return stripped plain text for a page section (None = full page)."""
    params: dict = {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json",
    }
    if section is not None:
        params["section"] = section

    resp = await client.get(WIKI_API_URL, params=params)
    resp.raise_for_status()
    wikitext = resp.json().get("parse", {}).get("wikitext", {}).get("*", "")
    text = _strip_wiki_markup(wikitext)
    if len(text) > MAX_EXTRACT_CHARS:
        text = text[:MAX_EXTRACT_CHARS] + "…"
    return text
