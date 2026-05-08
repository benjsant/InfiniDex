"""API routes for the AI assistant."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

LOGGER = logging.getLogger(__name__)

from backend.db.session import get_db
from backend.schemas.ai import AiPromptInfo, AiProviderInfo, AiRequest
from backend.services.ai_service import MAX_HISTORY_MSGS, stream_ai_response
from backend.services.llm_providers import provider_setup_instructions, select_provider
from backend.services.prompt import SYSTEM_PROMPT
from backend.services.tools import TOOL_SPECS

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/provider", response_model=AiProviderInfo)
def get_ai_provider():
    """Return the active LLM provider name and model, or 503 if none configured."""
    p = select_provider()
    if p is None:
        raise HTTPException(status_code=503, detail=provider_setup_instructions())
    return {"name": p.name, "model": p.model}


@router.get("/prompt", response_model=AiPromptInfo)
def get_ai_prompt():
    """Return the system prompt and tool descriptions for UI transparency."""
    return {
        "system_prompt": SYSTEM_PROMPT,
        "tools": [
            {
                "name":        spec["function"]["name"],
                "description": spec["function"]["description"],
            }
            for spec in TOOL_SPECS
        ],
        "max_history_messages": MAX_HISTORY_MSGS,
    }


@router.post("/ask")
async def ask_ai(request: AiRequest, db: Session = Depends(get_db)):
    """Agent tool-calling endpoint — SSE stream of AgentEvents.

    Each event is a JSON line: ``data: {"type": "tool_call"|"token", ...}\\n\\n``

    - ``tool_call`` events carry the tool name (emitted before execution).
    - ``token`` events carry response text chunks.

    Returns 503 with setup instructions if no LLM provider is configured.
    """
    provider = select_provider()
    if provider is None:
        raise HTTPException(status_code=503, detail=provider_setup_instructions())

    async def event_stream():
        try:
            async for event in stream_ai_response(
                db, request.message, request.context, request.history, provider
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            LOGGER.error("SSE stream exception: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Une erreur est survenue, réessaie.'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
