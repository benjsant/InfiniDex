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
        "Cherche une page sur le wiki officiel de Pokémon Infinite "
        "Fusion (infinitefusion.fandom.com). À utiliser quand les "
        "tools BDD ne couvrent pas la question : mécaniques de jeu, "
        "lore, quêtes, patches, fonctionnalités spécifiques au "
        "fan-game. Retourne l'intro de la meilleure page trouvée."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Termes de recherche en anglais (le wiki est en EN). "
                    "Ex: 'Safari Zone', 'Wonder Trade', 'Randomizer mode'"
                ),
            }
        },
        "required": ["query"],
    },
    handler=_search_wiki,
)
