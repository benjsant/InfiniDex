"""LLM provider abstraction — DeepSeek (cloud) + Ollama (local).

Permet à l'agent de basculer entre un provider cloud (DeepSeek, qualité
maximale) et un fallback local (Ollama avec un petit modèle quantifié)
sans toucher au code de la boucle tool-calling.

Sélection à runtime via env :
  - DEEPSEEK_API_KEY défini  → DeepSeekProvider
  - sinon, OLLAMA_URL défini → OllamaProvider
  - sinon                    → None (le route répond 503 avec instructions)

Les deux providers exposent la même interface (un client OpenAI-compatible
+ un nom de modèle) car DeepSeek et Ollama parlent tous deux le protocole
OpenAI Chat Completions.

Anticipe la Phase 5 v1.1 (provider pluggable) — ajouter Anthropic ou un
autre provider revient à créer une nouvelle classe `LLMProvider`.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

from openai import AsyncOpenAI


class LLMProvider(ABC):
    """Contrat pour un provider de LLM compatible OpenAI Chat Completions."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifiant court du provider, utilisé dans les logs et la doc."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Nom du modèle à passer dans `chat.completions.create(model=...)`."""

    @property
    @abstractmethod
    def client(self) -> AsyncOpenAI:
        """Instance `AsyncOpenAI` configurée (base_url + api_key)."""


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
    """Local — serveur Ollama avec endpoint OpenAI-compatible (`/v1`).

    Le modèle par défaut est `qwen2.5:3b` : ~2 GB, supporte le tool calling
    de façon correcte en français, tourne sur n'importe quel laptop avec
    8 GB de RAM. Override via `OLLAMA_MODEL`.
    """

    DEFAULT_MODEL = "qwen2.5:3b"

    def __init__(self, base_url: str, model: str | None = None) -> None:
        # Ollama ignore l'API key mais OpenAI SDK en exige une non-vide.
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


# ─── Sélection runtime ───────────────────────────────────────────────────────

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
                "label":    "DeepSeek (cloud, qualité maximale)",
                "steps":    [
                    "Créer une clé sur https://platform.deepseek.com/",
                    "Ajouter `DEEPSEEK_API_KEY=sk-...` dans .env",
                    "docker compose restart backend",
                ],
            },
            {
                "provider": "ollama",
                "label":    "Ollama (local, autonome, sans clé)",
                "steps":    [
                    "docker compose --profile ollama up -d ollama",
                    "Décommenter `OLLAMA_URL=http://ollama:11434` dans .env",
                    "docker compose restart backend",
                ],
                "note":     "Premier démarrage : ~2 GB téléchargés (modèle qwen2.5:3b).",
            },
        ],
    }
