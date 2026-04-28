"""LLM provider abstraction — DeepSeek (cloud) + Ollama (local).

Allows the agent to switch between a cloud provider (DeepSeek, best quality)
and a local fallback (Ollama with a small quantized model) without touching
the tool-calling loop code.

Runtime selection via env:
  - DEEPSEEK_API_KEY set  → DeepSeekProvider
  - else, OLLAMA_URL set  → OllamaProvider
  - else                  → None (route returns 503 with setup instructions)

Both providers expose the same interface (an OpenAI-compatible client
+ a model name) because DeepSeek and Ollama both speak the OpenAI Chat
Completions protocol.

Anticipates Phase 5 v1.1 (pluggable provider) — adding Anthropic or another
provider simply means creating a new `LLMProvider` subclass.
"""

from __future__ import annotations

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

def select_provider() -> LLMProvider | None:
    """Return the first available provider based on environment.

    Order:
      1. `DEEPSEEK_API_KEY` set → DeepSeek
      2. `OLLAMA_URL` set → Ollama (model from `OLLAMA_MODEL`, default `qwen2.5:3b`)
      3. None — route should return 503 with instructions
    """
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_key:
        return DeepSeekProvider(deepseek_key)

    ollama_url = os.getenv("OLLAMA_URL")
    if ollama_url:
        return OllamaProvider(ollama_url, os.getenv("OLLAMA_MODEL"))

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
