"""LLM provider abstraction — DeepSeek · OpenRouter · Ollama.

Runtime selection via env (first match wins):
  1. DEEPSEEK_API_KEY   → DeepSeekProvider   (cloud, best quality)
  2. OPENROUTER_API_KEY → OpenRouterProvider  (cloud, free tier available)
  3. OLLAMA_URL         → OllamaProvider      (local, no key required)
  4. None               → 503 with setup instructions

All three expose the same OpenAI Chat Completions-compatible interface,
so the tool-calling loop in ai_service.py never needs to know which is active.
"""

from __future__ import annotations

import functools
import os
from abc import ABC, abstractmethod

from openai import AsyncOpenAI


class LLMProvider(ABC):
    """Contract for an OpenAI Chat Completions-compatible LLM provider."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short provider identifier, used in logs and documentation."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Model name to pass to `chat.completions.create(model=...)`."""

    @property
    @abstractmethod
    def client(self) -> AsyncOpenAI:
        """Configured `AsyncOpenAI` instance (base_url + api_key)."""


class DeepSeekProvider(LLMProvider):
    """Cloud — DeepSeek API (https://platform.deepseek.com/)."""

    BASE_URL = "https://api.deepseek.com"
    MODEL    = "deepseek-chat"

    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=self.BASE_URL)

    @property
    def name(self) -> str:
        return "deepseek"

    @property
    def model(self) -> str:
        return self.MODEL

    @property
    def client(self) -> AsyncOpenAI:
        return self._client


class OpenRouterProvider(LLMProvider):
    """Cloud — OpenRouter (https://openrouter.ai/), OpenAI-compatible.

    Free-tier models available with the `:free` suffix (e.g. `deepseek/deepseek-chat-v3-0324:free`).
    Override via OPENROUTER_MODEL. HTTP-Referer header required by OpenRouter ToS.
    """

    BASE_URL      = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "deepseek/deepseek-chat-v3-0324:free"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self._model = model or self.DEFAULT_MODEL
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.BASE_URL,
            default_headers={
                "HTTP-Referer": "https://github.com/benjsant/InfiniDex-IA",
                "X-Title":      "InfiniDex-IA",
            },
        )

    @property
    def name(self) -> str:
        return "openrouter"

    @property
    def model(self) -> str:
        return self._model

    @property
    def client(self) -> AsyncOpenAI:
        return self._client


class OllamaProvider(LLMProvider):
    """Local — Ollama server with OpenAI-compatible endpoint (`/v1`).

    The default model is `qwen2.5:3b`: ~2 GB, supports tool calling
    correctly, runs on any laptop with 8 GB of RAM. Override via `OLLAMA_MODEL`.
    """

    DEFAULT_MODEL = "qwen2.5:3b"

    def __init__(self, base_url: str, model: str | None = None) -> None:
        # Ollama ignores the API key but the OpenAI SDK requires a non-empty one.
        self._client = AsyncOpenAI(api_key="ollama", base_url=f"{base_url.rstrip('/')}/v1")
        self._model = model or self.DEFAULT_MODEL

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    @property
    def client(self) -> AsyncOpenAI:
        return self._client


# ─── Runtime selection ───────────────────────────────────────────────────────

@functools.cache
def select_provider() -> LLMProvider | None:
    """Return the first available provider based on environment (first match wins).

    Cached at process level — the provider and its httpx connection pool are
    reused across requests. Changing env vars requires a restart (expected in
    Docker). Call select_provider.cache_clear() in tests to reset state.

    Order:
      1. DEEPSEEK_API_KEY   → DeepSeek
      2. OPENROUTER_API_KEY → OpenRouter (model from OPENROUTER_MODEL, default free DeepSeek)
      3. OLLAMA_URL         → Ollama    (model from OLLAMA_MODEL, default qwen2.5:3b)
      4. None               → route returns 503 with instructions
    """
    if key := os.getenv("DEEPSEEK_API_KEY"):
        return DeepSeekProvider(key)

    if key := os.getenv("OPENROUTER_API_KEY"):
        return OpenRouterProvider(key, os.getenv("OPENROUTER_MODEL"))

    if url := os.getenv("OLLAMA_URL"):
        return OllamaProvider(url, os.getenv("OLLAMA_MODEL"))

    return None


def provider_setup_instructions() -> dict:
    """Structured 503 payload telling the user how to enable an LLM."""
    return {
        "error":   "No LLM provider configured",
        "options": [
            {
                "provider": "deepseek",
                "label":    "DeepSeek (cloud, best quality)",
                "steps":    [
                    "Create a key at https://platform.deepseek.com/",
                    "Add `DEEPSEEK_API_KEY=sk-...` to .env",
                    "docker compose restart backend",
                ],
            },
            {
                "provider": "openrouter",
                "label":    "OpenRouter (cloud, free tier available)",
                "steps":    [
                    "Create a free key at https://openrouter.ai/",
                    "Add `OPENROUTER_API_KEY=sk-or-...` to .env",
                    "Optionally set OPENROUTER_MODEL (default: deepseek/deepseek-chat-v3-0324:free)",
                    "docker compose restart backend",
                ],
                "note":     "Free models have rate limits; paid models available on the same key.",
            },
            {
                "provider": "ollama",
                "label":    "Ollama (local, self-contained, no key required)",
                "steps":    [
                    "docker compose --profile ollama up -d ollama",
                    "Uncomment `OLLAMA_URL=http://ollama:11434` in .env",
                    "docker compose restart backend",
                ],
                "note":     "First start: ~2 GB downloaded (qwen2.5:3b model).",
            },
        ],
    }
