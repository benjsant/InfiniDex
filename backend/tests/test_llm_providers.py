"""Unit tests for backend.services.llm_providers — selection logic."""

from __future__ import annotations

from backend.services.llm_providers import (
    DeepSeekProvider,
    OllamaProvider,
    OpenRouterProvider,
    provider_setup_instructions,
    select_provider,
)


def test_select_deepseek_when_key_present(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    provider = select_provider()
    assert isinstance(provider, DeepSeekProvider)
    assert provider.name == "deepseek"
    assert provider.model == "deepseek-chat"


def test_select_openrouter_when_only_key_present(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    provider = select_provider()
    assert isinstance(provider, OpenRouterProvider)
    assert provider.name == "openrouter"
    assert provider.model == OpenRouterProvider.DEFAULT_MODEL


def test_select_openrouter_with_custom_model(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "google/gemma-3-27b-it:free")
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    provider = select_provider()
    assert provider.model == "google/gemma-3-27b-it:free"


def test_select_ollama_when_only_ollama_url_present(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_URL", "http://ollama:11434")
    provider = select_provider()
    assert isinstance(provider, OllamaProvider)
    assert provider.name == "ollama"
    assert provider.model == "qwen2.5:3b"  # default


def test_select_ollama_with_custom_model(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_URL", "http://ollama:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b")
    provider = select_provider()
    assert provider.model == "qwen2.5:7b"


def test_deepseek_takes_priority_over_all(monkeypatch) -> None:
    """DeepSeek wins when multiple providers are configured."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("OLLAMA_URL", "http://ollama:11434")
    provider = select_provider()
    assert provider.name == "deepseek"


def test_openrouter_takes_priority_over_ollama(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("OLLAMA_URL", "http://ollama:11434")
    provider = select_provider()
    assert provider.name == "openrouter"


def test_no_provider_returns_none(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    assert select_provider() is None


def test_setup_instructions_lists_all_options() -> None:
    payload = provider_setup_instructions()
    providers = {opt["provider"] for opt in payload["options"]}
    assert providers == {"deepseek", "openrouter", "ollama"}
    for opt in payload["options"]:
        assert len(opt["steps"]) >= 2


def test_ollama_base_url_normalization() -> None:
    """Trailing slash on OLLAMA_URL is normalized."""
    p1 = OllamaProvider("http://ollama:11434")
    p2 = OllamaProvider("http://ollama:11434/")
    # Both should resolve to the same /v1 endpoint internally
    assert str(p1.client.base_url).rstrip("/") == str(p2.client.base_url).rstrip("/")
