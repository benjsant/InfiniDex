"""AI service — tool-calling agent loop with fail-closed guarantee.

Flow:
  1. LLM receives the question + TOOL_SPECS
  2. LLM may request tool calls → backend executes, returns results, loops
  3. When LLM produces a text response → yield token events to stream to UI
  4. After MAX_ITERATIONS with no text → fail-closed refusal token event

Yields typed AgentEvent dicts. The route formats them as SSE.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Literal, TypedDict

from sqlalchemy.orm import Session

from backend.schemas.ai import HistoryMessage
from backend.services.llm_providers import LLMProvider, select_provider
from backend.services.prompt import SYSTEM_PROMPT
from backend.services.tools import TOOL_SPECS, dispatch_tool

LOGGER = logging.getLogger(__name__)

MAX_ITERATIONS   = 5
MAX_TOKENS       = 1024
TEMPERATURE      = 0.3
FAILURE_MESSAGE  = "Je n'ai pas trouvé cette information."
MAX_HISTORY_MSGS = 10


# ─── Event types ─────────────────────────────────────────────────────────────

class ToolCallEvent(TypedDict):
    type: Literal["tool_call"]
    name: str


class TokenEvent(TypedDict):
    type: Literal["token"]
    chunk: str


AgentEvent = ToolCallEvent | TokenEvent


# ─── Agent loop ──────────────────────────────────────────────────────────────

async def stream_ai_response(
    db: Session,
    message: str,
    context: str | None = None,
    history: list[HistoryMessage] | None = None,
    provider: LLMProvider | None = None,
) -> AsyncIterator[AgentEvent]:
    """Agent loop: tool calls → results → loop → yield token events.

    Yields:
        ToolCallEvent when a tool is invoked (for UI transparency).
        TokenEvent with the final response chunks (or FAILURE_MESSAGE).
    """
    provider = provider or select_provider()
    if provider is None:
        raise RuntimeError("No LLM provider configured (DEEPSEEK_API_KEY or OLLAMA_URL)")

    LOGGER.debug("agent provider=%s model=%s history_len=%d",
                 provider.name, provider.model, len(history or []))

    trimmed_history = (history or [])[-MAX_HISTORY_MSGS:]
    user_content = f"[Contexte: {context}]\n\n{message}" if context else message

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *[{"role": m.role, "content": m.content} for m in trimmed_history],
        {"role": "user",   "content": user_content},
    ]

    for iteration in range(MAX_ITERATIONS):
        LOGGER.debug("agent iteration=%d/%d", iteration + 1, MAX_ITERATIONS)

        response = await provider.client.chat.completions.create(
            model=provider.model,
            messages=messages,
            tools=TOOL_SPECS,
            tool_choice="auto",
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            content = (msg.content or "").strip()
            yield TokenEvent(type="token", chunk=content if content else FAILURE_MESSAGE)
            return

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            yield ToolCallEvent(type="tool_call", name=tc.function.name)

            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError as exc:
                result = {"error": f"Invalid JSON arguments: {exc}"}
            else:
                result = await dispatch_tool(db, tc.function.name, args)

            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      json.dumps(result, ensure_ascii=False),
            })

    LOGGER.warning("agent reached MAX_ITERATIONS=%d without final response", MAX_ITERATIONS)
    yield TokenEvent(type="token", chunk=FAILURE_MESSAGE)
