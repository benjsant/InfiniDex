"""Tests for /ai route — tool-calling loop with mocked LLM provider."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.services import ai_service, llm_providers


# ─── Helpers pour mocker les réponses DeepSeek ───────────────────────────────

def _fake_message_content(text: str):
    """Fake OpenAI ChatCompletionMessage with text only, no tool_calls."""
    return SimpleNamespace(content=text, tool_calls=None)


def _fake_message_tool_calls(calls: list[tuple[str, dict]]):
    """Fake message where the assistant requests tool calls.

    Args:
        calls: list of (tool_name, args_dict) tuples.
    """
    tool_calls = [
        SimpleNamespace(
            id=f"call_{i}",
            type="function",
            function=SimpleNamespace(
                name=name,
                arguments=json.dumps(args),
            ),
        )
        for i, (name, args) in enumerate(calls)
    ]
    return SimpleNamespace(content=None, tool_calls=tool_calls)


def _fake_response(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeCompletions:
    """Fake `client.chat.completions` with a scripted sequence of responses."""

    def __init__(self, responses: list):
        self._responses = list(responses)
        self.received_calls: list[dict] = []

    async def create(self, **kwargs):
        self.received_calls.append(kwargs)
        if not self._responses:
            raise AssertionError("FakeCompletions ran out of scripted responses")
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses: list):
        self.chat = SimpleNamespace(completions=FakeCompletions(responses))


class FakeProvider:
    """Minimal LLMProvider impl for tests."""

    def __init__(self, responses: list):
        self._client = FakeClient(responses)

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-model"

    @property
    def client(self):
        return self._client


@pytest.fixture
def fake_client_factory(monkeypatch):
    """Install a fake LLM provider + canned tool dispatch.

    `dispatch_tool` is mocked to return tool-name-specific stubs so these
    tests don't need a populated DB (CI runs without Postgres). Real
    tool↔DB integration is covered separately in `test_ai_tools.py`.

    `select_provider` is monkey-patched at the route level so the 503
    branch is bypassed and our FakeProvider is used in the loop.
    """
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-fake")

    def fake_dispatch_tool(_db, name: str, args: dict) -> dict:
        if name == "get_pokemon":
            return {
                "id": args.get("name_or_id"),
                "name_en": "Pikachu" if args.get("name_or_id") == 25 else "Charizard",
                "types": ["Electric"],
            }
        return {"ok": True, "tool": name, "args": args}

    monkeypatch.setattr(ai_service, "dispatch_tool", fake_dispatch_tool)

    def install(responses: list) -> FakeClient:
        provider = FakeProvider(responses)
        # Patch both module references — route checks select_provider first
        # (its own import), then service uses provider passed in.
        monkeypatch.setattr(
            "backend.routes.ai_route.select_provider",
            lambda: provider,
        )
        monkeypatch.setattr(llm_providers, "select_provider", lambda: provider)
        return provider.client

    yield install


# ─── Tests ───────────────────────────────────────────────────────────────────

def test_ai_no_provider_configured(client: TestClient, monkeypatch) -> None:
    """Without DEEPSEEK_API_KEY nor OLLAMA_URL → 503 with setup instructions."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    r = client.post("/ai/ask", json={"message": "salut"})
    assert r.status_code == 503
    detail = r.json()["detail"]
    assert detail["error"] == "No LLM provider configured"
    providers = {opt["provider"] for opt in detail["options"]}
    assert providers == {"deepseek", "ollama"}


def test_ai_direct_answer_no_tool_call(client: TestClient, fake_client_factory) -> None:
    """LLM answers directly without invoking any tool."""
    fake = fake_client_factory([
        _fake_response(_fake_message_content("Bonjour !")),
    ])

    r = client.post("/ai/ask", json={"message": "Bonjour"})
    assert r.status_code == 200
    assert r.text == "Bonjour !"
    # One call made, no follow-up needed
    assert len(fake.chat.completions.received_calls) == 1
    # Tools were advertised even though the model didn't use them
    assert "tools" in fake.chat.completions.received_calls[0]


def test_ai_single_tool_call_then_answer(client: TestClient, fake_client_factory) -> None:
    """LLM calls one tool, then gives a final answer using the result."""
    fake = fake_client_factory([
        _fake_response(_fake_message_tool_calls([
            ("get_pokemon", {"name_or_id": 25}),
        ])),
        _fake_response(_fake_message_content("Pikachu est de type Electric.")),
    ])

    r = client.post("/ai/ask", json={"message": "Parle-moi de Pikachu"})
    assert r.status_code == 200
    assert "Pikachu" in r.text

    calls = fake.chat.completions.received_calls
    assert len(calls) == 2
    # Second call's messages include the tool result
    second_messages = calls[1]["messages"]
    tool_msgs = [m for m in second_messages if m["role"] == "tool"]
    assert len(tool_msgs) == 1
    tool_payload = json.loads(tool_msgs[0]["content"])
    assert tool_payload["name_en"] == "Pikachu"


def test_ai_multi_tool_single_turn(client: TestClient, fake_client_factory) -> None:
    """LLM calls 2 tools in one turn, then answers."""
    fake = fake_client_factory([
        _fake_response(_fake_message_tool_calls([
            ("get_pokemon", {"name_or_id": 25}),
            ("get_pokemon", {"name_or_id": 6}),
        ])),
        _fake_response(_fake_message_content("Pikachu est Electric, Charizard est Fire/Flying.")),
    ])

    r = client.post("/ai/ask", json={"message": "Compare Pikachu et Charizard"})
    assert r.status_code == 200
    calls = fake.chat.completions.received_calls
    # Both tool results made it back in the second call
    tool_results = [
        json.loads(m["content"])
        for m in calls[1]["messages"]
        if m["role"] == "tool"
    ]
    assert {r["name_en"] for r in tool_results} == {"Pikachu", "Charizard"}


def test_ai_circuit_breaker_fails_closed(client: TestClient, fake_client_factory) -> None:
    """If LLM keeps requesting tools past MAX_ITERATIONS, we fail-close."""
    # Script: always request a tool — MAX_ITERATIONS times
    repeating = _fake_response(_fake_message_tool_calls([
        ("get_pokemon", {"name_or_id": 1}),
    ]))
    fake_client_factory([repeating] * (ai_service.MAX_ITERATIONS + 2))

    r = client.post("/ai/ask", json={"message": "Tu boucles à l'infini"})
    assert r.status_code == 200
    assert r.text == ai_service.FAILURE_MESSAGE


def test_ai_empty_content_is_failure(client: TestClient, fake_client_factory) -> None:
    """A final turn with no content and no tool_calls → fail-closed message."""
    fake_client_factory([
        _fake_response(SimpleNamespace(content="", tool_calls=None)),
    ])

    r = client.post("/ai/ask", json={"message": "rien"})
    assert r.status_code == 200
    assert r.text == ai_service.FAILURE_MESSAGE


def test_ai_invalid_tool_json_is_recovered(client: TestClient, fake_client_factory) -> None:
    """Malformed tool arguments → error payload, model can try again."""
    # 1st response: malformed JSON arguments
    bad = SimpleNamespace(
        id="call_0",
        type="function",
        function=SimpleNamespace(name="get_pokemon", arguments="not json"),
    )
    first = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(
            content=None,
            tool_calls=[bad],
        ))],
    )
    # 2nd response: final answer (with error info in context)
    second = _fake_response(_fake_message_content("Désolé, requête invalide."))

    fake = fake_client_factory([first, second])

    r = client.post("/ai/ask", json={"message": "test"})
    assert r.status_code == 200

    # Tool result message should contain an "error" field
    tool_msg = next(
        m for m in fake.chat.completions.received_calls[1]["messages"]
        if m["role"] == "tool"
    )
    payload = json.loads(tool_msg["content"])
    assert "error" in payload


def test_ai_system_prompt_is_injected(client: TestClient, fake_client_factory) -> None:
    """Every call must include the strict system prompt at position 0."""
    fake = fake_client_factory([
        _fake_response(_fake_message_content("ok")),
    ])

    client.post("/ai/ask", json={"message": "test"})

    first_messages = fake.chat.completions.received_calls[0]["messages"]
    assert first_messages[0]["role"] == "system"
    assert "FusionDex AI" in first_messages[0]["content"]
    assert "Je n'ai pas trouvé" in first_messages[0]["content"]


def test_ai_context_is_prepended(client: TestClient, fake_client_factory) -> None:
    """When `context` is provided, it's prepended to the user message."""
    fake = fake_client_factory([
        _fake_response(_fake_message_content("ok")),
    ])

    client.post("/ai/ask", json={
        "message": "Que penses-tu de cette fusion ?",
        "context": "Pokémon affiché : Pikachu id=25",
    })

    first_messages = fake.chat.completions.received_calls[0]["messages"]
    user_msg = first_messages[1]
    assert user_msg["role"] == "user"
    assert "Pikachu id=25" in user_msg["content"]
    assert "Que penses-tu" in user_msg["content"]
