"""Agent tools — public interface.

Import from here, not from sub-modules:

    from backend.services.tools import TOOLS, TOOL_SPECS, dispatch_tool
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from backend.services.tools._base import Tool
from backend.services.tools.db_tools import (
    get_fusion_tool,
    get_item_tool,
    get_move_tutors_tool,
    get_pokemon_tool,
    search_move_tool,
)
from backend.services.tools.wiki_tool import search_wiki_tool

LOGGER = logging.getLogger(__name__)

TOOLS: list[Tool] = [
    get_pokemon_tool,
    get_fusion_tool,
    search_move_tool,
    get_item_tool,
    get_move_tutors_tool,
    search_wiki_tool,
]

_TOOL_MAP: dict[str, Tool] = {t.name: t for t in TOOLS}

TOOL_SPECS: list[dict] = [t.to_spec() for t in TOOLS]


async def dispatch_tool(db: Session, name: str, args: dict[str, Any]) -> dict:
    """Resolve a tool by name, invoke its handler, and log the call.

    Returns ``{"error": "..."}`` for unknown tools or bad arguments.
    Structured log line on every call: tool name, latency, success flag.
    """
    tool = _TOOL_MAP.get(name)
    if tool is None:
        LOGGER.warning("tool=%s status=unknown", name)
        return {"error": f"Unknown tool '{name}'"}

    t0 = time.monotonic()
    result = await tool.handler(db, args)
    latency_ms = (time.monotonic() - t0) * 1000
    success = "error" not in result

    LOGGER.info(
        "tool=%s latency_ms=%.1f success=%s",
        name, latency_ms, success,
    )
    return result
