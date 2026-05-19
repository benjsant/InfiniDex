"""AI service — tool-calling agent loop with real token streaming.

Flow:
  1. LLM receives the question + TOOL_SPECS (stream=True throughout)
  2. If the stream contains tool_call deltas → assemble, dispatch, loop
  3. If the stream contains content tokens → yield them as they arrive
  4. After the final text turn → yield a SourceEvent listing sources used
  5. After MAX_ITERATIONS with no text → fail-closed refusal

Yields typed AgentEvent dicts. The route formats them as SSE.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Literal, TypedDict

from sqlalchemy.orm import Session

from backend.schemas.ai import HistoryMessage
from backend.services.llm_providers import LLMProvider, select_provider
from backend.services.pii_redactor import redact as pii_redact
from backend.services.prompt import SYSTEM_PROMPT
from backend.services.tools import TOOL_SPECS, dispatch_tool

LOGGER = logging.getLogger(__name__)

MAX_ITERATIONS   = 5
MAX_TOKENS       = 2048
TEMPERATURE      = 0.1
FAILURE_MESSAGE  = "Je n'ai pas trouvé cette information."
MAX_HISTORY_MSGS = 10

# Source classification for SourceEvent
_DB_TOOLS = frozenset({
    "get_pokemon", "get_fusion", "get_triple_fusion",
    "search_move", "get_item", "get_move_tutors", "search_pokemon_locations",
})


# ─── Event types ─────────────────────────────────────────────────────────────

class ToolCallEvent(TypedDict):
    type: Literal["tool_call"]
    name: str


class TokenEvent(TypedDict):
    type: Literal["token"]
    chunk: str


class SourceEvent(TypedDict):
    type: Literal["source"]
    sources: list[str]           # e.g. ["db", "wiki", "web"]
    web_urls: list[dict]         # [{title, url}] from search_web results, empty if web unused


class UsageEvent(TypedDict):
    type: Literal["usage"]
    total_tokens: int


AgentEvent = ToolCallEvent | TokenEvent | SourceEvent | UsageEvent


def _safe_redact(data: dict) -> dict:
    try:
        return pii_redact(data)
    except Exception:
        LOGGER.warning("pii_redact failed — passing tool result unredacted")
        return data


# ─── Single-turn streamer ─────────────────────────────────────────────────────

async def _stream_turn(provider: LLMProvider, messages: list[dict]):
    """Stream one LLM turn and yield internal events.

    Yields dicts with key 'type':
      {"type": "token",      "chunk": str}          — text token
      {"type": "tool_calls", "calls": list[dict]}   — assembled tool calls
      {"type": "empty"}                              — no output
    """
    tool_calls_by_idx: dict[int, dict] = {}
    has_tokens     = False
    has_tool_calls = False
    usage_data:  dict | None = None

    stream = await provider.client.chat.completions.create(
        model=provider.model,
        messages=messages,
        tools=TOOL_SPECS,
        tool_choice="auto",
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        stream=True,
        stream_options={"include_usage": True},
    )

    async for chunk in stream:
        if not chunk.choices:
            # Final usage-only chunk (from stream_options include_usage)
            if chunk.usage:
                usage_data = {"total_tokens": chunk.usage.total_tokens}
            continue
        delta = chunk.choices[0].delta

        if delta.tool_calls:
            has_tool_calls = True
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in tool_calls_by_idx:
                    tool_calls_by_idx[idx] = {
                        "id":   tc.id or "",
                        "type": "function",
                        "function": {
                            "name":      (tc.function.name      or "") if tc.function else "",
                            "arguments": (tc.function.arguments or "") if tc.function else "",
                        },
                    }
                else:
                    if tc.id:
                        tool_calls_by_idx[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_by_idx[idx]["function"]["name"]      += tc.function.name
                        if tc.function.arguments:
                            tool_calls_by_idx[idx]["function"]["arguments"] += tc.function.arguments

        elif delta.content:
            has_tokens = True
            yield {"type": "token", "chunk": delta.content}

    if has_tool_calls:
        yield {"type": "tool_calls", "calls": [tool_calls_by_idx[i] for i in sorted(tool_calls_by_idx)]}
    elif not has_tokens:
        yield {"type": "empty"}
    if usage_data:
        yield {"type": "usage", **usage_data}


# ─── Agent loop ──────────────────────────────────────────────────────────────

async def stream_ai_response(
    db: Session,
    message: str,
    context: str | None = None,
    history: list[HistoryMessage] | None = None,
    provider: LLMProvider | None = None,
) -> AsyncIterator[AgentEvent]:
    """Agent loop — streams tokens as they arrive, emits source attribution.

    Yields:
        ToolCallEvent  — before each tool dispatch (UI transparency).
        TokenEvent     — text chunks as they arrive from the LLM.
        SourceEvent    — after the final response, listing sources used.
    """
    provider = provider or select_provider()
    if provider is None:
        raise RuntimeError("No LLM provider configured (DEEPSEEK_API_KEY or OLLAMA_URL)")

    LOGGER.debug("agent provider=%s model=%s history_len=%d",
                 provider.name, provider.model, len(history or []))

    trimmed_history = (history or [])[-MAX_HISTORY_MSGS:]
    user_content    = f"[Contexte: {context}]\n\n{message}" if context else message

    messages: list[dict] = [
        {"role": "system",  "content": SYSTEM_PROMPT},
        *[{"role": m.role, "content": m.content} for m in trimmed_history],
        {"role": "user",   "content": user_content},
    ]

    sources_used: set[str] = set()
    web_urls: list[dict] = []
    total_tokens = 0

    for iteration in range(MAX_ITERATIONS):
        LOGGER.debug("agent iteration=%d/%d", iteration + 1, MAX_ITERATIONS)

        tool_calls: list[dict] = []
        got_text = False
        assistant_parts: list[str] = []

        async for ev in _stream_turn(provider, messages):
            if ev["type"] == "token":
                got_text = True
                chunk: str = ev["chunk"]
                assistant_parts.append(chunk)
                yield TokenEvent(type="token", chunk=chunk)

            elif ev["type"] == "tool_calls":
                tool_calls = ev["calls"]

            elif ev["type"] == "usage":
                total_tokens += ev.get("total_tokens", 0)

        if got_text and not tool_calls:
            # Pure-text turn — final answer, no tools were called.
            if not assistant_parts:
                yield TokenEvent(type="token", chunk=FAILURE_MESSAGE)
            if sources_used:
                yield SourceEvent(type="source", sources=sorted(sources_used), web_urls=web_urls)
            if total_tokens:
                yield UsageEvent(type="usage", total_tokens=total_tokens)
            return

        if not tool_calls:
            # No text and no tool calls — fail closed.
            yield TokenEvent(type="token", chunk=FAILURE_MESSAGE)
            return

        # Tool calls are present (model may have emitted a preamble text like
        # "Je vais chercher…" before the call — that text was already streamed;
        # the tool dispatch continues normally on the next iteration).

        # Append the assistant's tool-call turn.
        messages.append({
            "role":    "assistant",
            "content": "".join(assistant_parts),
            "tool_calls": [
                {
                    "id":   tc["id"],
                    "type": "function",
                    "function": {
                        "name":      tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    },
                }
                for tc in tool_calls
            ],
        })

        # Dispatch each tool, tracking sources.
        for tc in tool_calls:
            name = tc["function"]["name"]
            yield ToolCallEvent(type="tool_call", name=name)

            if name in _DB_TOOLS:
                sources_used.add("db")
            elif name == "search_wiki":
                sources_used.add("wiki")
            elif name == "search_web":
                sources_used.add("web")

            try:
                args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
            except json.JSONDecodeError as exc:
                result: dict = {"error": f"Invalid JSON arguments: {exc}"}
            else:
                result = await dispatch_tool(db, name, args)

            # Collect URLs from web search results for source attribution.
            if name == "search_web" and result.get("found") and result.get("results"):
                for r in result["results"]:
                    if r.get("url") and r.get("title"):
                        web_urls.append({"title": r["title"][:80], "url": r["url"]})

            messages.append({
                "role":         "tool",
                "tool_call_id": tc["id"],
                "content":      json.dumps(_safe_redact(result), ensure_ascii=False),
            })

    LOGGER.warning("agent reached MAX_ITERATIONS=%d without final response", MAX_ITERATIONS)
    yield TokenEvent(type="token", chunk=FAILURE_MESSAGE)
