"""API routes for the AI assistant."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.ai import AiRequest
from backend.services.ai_service import stream_ai_response
from backend.services.llm_providers import provider_setup_instructions, select_provider

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/provider")
def get_ai_provider():
    """Return the active LLM provider name and model, or 503 if none configured."""
    p = select_provider()
    if p is None:
        raise HTTPException(status_code=503, detail=provider_setup_instructions())
    return {"name": p.name, "model": p.model}


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
        async for event in stream_ai_response(
            db, request.message, request.context, request.history, provider
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
