"""API routes for AI assistant — streaming SSE with provider auto-selection."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.ai import AiRequest
from backend.services.ai_service import stream_ai_response
from backend.services.llm_providers import provider_setup_instructions, select_provider

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/ask")
async def ask_ai(request: AiRequest, db: Session = Depends(get_db)):
    """Agent tool-calling streaming SSE.

    Le LLM (DeepSeek si `DEEPSEEK_API_KEY` set, sinon Ollama si `OLLAMA_URL`
    set) reçoit la liste de tools (BDD Pokémon/fusions/moves/items/tutors),
    exécute les appels nécessaires, puis stream sa réponse finale. Si aucun
    tool n'a remonté d'info pertinente, répond *« Je n'ai pas trouvé cette
    information. »* (fail-closed).

    Sans provider configuré, retourne 503 avec instructions de setup.
    """
    provider = select_provider()
    if provider is None:
        raise HTTPException(status_code=503, detail=provider_setup_instructions())

    async def token_generator():
        async for token in stream_ai_response(db, request.message, request.context, provider):
            yield token

    return StreamingResponse(
        token_generator(),
        media_type="text/plain; charset=utf-8",
    )
