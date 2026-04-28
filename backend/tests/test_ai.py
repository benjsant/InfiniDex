"""Tests for /ai route — tool-calling loop with mocked LLM provider."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.services import ai_service, llm_providers


# ─── SSE helpers ─────────────────────────────────────────────────────────────

def _sse_events(response) -> list[dict]:
    """Parse all JSON events from an SSE response body."""
    events = []
    for line in response.text.splitlines():
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


def _sse_text(response) -> str:
    """Concatenate all token chunks from an SSE response."""
    return "".join(
        e["chunk"] for e in _sse_events(response) if e.get("type") == "token"
    )


def _sse_tool_calls(response) -> list[str]:
    """Return tool names from tool_call events in an SSE response."""
    return [e["name"] for e in _sse_events(response) if e.get("type") == "tool_call"]


# ─── Fake LLM infrastructure ─────────────────────────────────────────────────

def _fake_message_content(text: str):
    return SimpleNamespace(content=text, tool_calls=None)


def _fake_message_tool_calls(calls: list[tuple[str, dict]]):
    tool_calls = [
        SimpleNamespace(
            id=f"call_{i}",
            type="function",
            function=SimpleNamespace(name=name, arguments=json.dumps(args)),
        )
        for i, (name, args) in enumerate(calls)
    ]
    return SimpleNamespace(content=None, tool_calls=tool_calls)


def _fake_response(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeCompletions:
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
    """Install a fake LLM provider + canned tool dispatch (no DB needed)."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-fake")

    async def fake_dispatch_tool(_db, name: str, args: dict) -> dict:
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
        monkeypatch.setattr("backend.routes.ai_route.select_provider", lambda: provider)
        monkeypatch.setattr(llm_providers, "select_provider", lambda: provider)
        return provider.client

    yield install


# ─── Provider endpoint ───────────────────────────────────────────────────────

def test_ai_provider_returns_name_and_model(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    r = client.get("/ai/provider")
    assert r.status_code == 200
    assert r.json()["name"] == "deepseek"
    assert r.json()["model"] == "deepseek-chat"


def test_ai_provider_503_when_none_configured(client: TestClient, monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    r = client.get("/ai/provider")
    assert r.status_code == 503


# ─── Core agent behavior ─────────────────────────────────────────────────────

def test_ai_no_provider_configured(client: TestClient, monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    r = client.post("/ai/ask", json={"message": "salut"})
    assert r.status_code == 503
    detail = r.json()["detail"]
    assert detail["error"] == "No LLM provider configured"
    assert {opt["provider"] for opt in detail["options"]} == {"deepseek", "ollama"}


def test_ai_direct_answer_no_tool_call(client: TestClient, fake_client_factory) -> None:
    fake = fake_client_factory([_fake_response(_fake_message_content("Bonjour !"))])

    r = client.post("/ai/ask", json={"message": "Bonjour"})
    assert r.status_code == 200
    assert _sse_text(r) == "Bonjour !"
    assert _sse_tool_calls(r) == []
    assert len(fake.chat.completions.received_calls) == 1
    assert "tools" in fake.chat.completions.received_calls[0]


def test_ai_single_tool_call_then_answer(client: TestClient, fake_client_factory) -> None:
    fake = fake_client_factory([
        _fake_response(_fake_message_tool_calls([("get_pokemon", {"name_or_id": 25})])),
        _fake_response(_fake_message_content("Pikachu est de type Electric.")),
    ])

    r = client.post("/ai/ask", json={"message": "Parle-moi de Pikachu"})
    assert r.status_code == 200
    assert "Pikachu" in _sse_text(r)
    assert _sse_tool_calls(r) == ["get_pokemon"]

    tool_msgs = [m for m in fake.chat.completions.received_calls[1]["messages"] if m["role"] == "tool"]
    assert json.loads(tool_msgs[0]["content"])["name_en"] == "Pikachu"


def test_ai_tool_call_events_emitted_before_response(client: TestClient, fake_client_factory) -> None:
    """tool_call events appear in the SSE stream before the token event."""
    fake_client_factory([
        _fake_response(_fake_message_tool_calls([("get_pokemon", {"name_or_id": 25})])),
        _fake_response(_fake_message_content("Pikachu.")),
    ])

    r = client.post("/ai/ask", json={"message": "Pikachu ?"})
    events = _sse_events(r)
    types = [e["type"] for e in events]
    assert types.index("tool_call") < types.index("token")


def test_ai_multi_tool_single_turn(client: TestClient, fake_client_factory) -> None:
    fake = fake_client_factory([
        _fake_response(_fake_message_tool_calls([
            ("get_pokemon", {"name_or_id": 25}),
            ("get_pokemon", {"name_or_id": 6}),
        ])),
        _fake_response(_fake_message_content("Pikachu est Electric, Charizard est Fire/Flying.")),
    ])

    r = client.post("/ai/ask", json={"message": "Compare Pikachu et Charizard"})
    assert r.status_code == 200
    assert set(_sse_tool_calls(r)) == {"get_pokemon"}
    tool_results = [
        json.loads(m["content"])
        for m in fake.chat.completions.received_calls[1]["messages"]
        if m["role"] == "tool"
    ]
    assert {res["name_en"] for res in tool_results} == {"Pikachu", "Charizard"}


def test_ai_circuit_breaker_fails_closed(client: TestClient, fake_client_factory) -> None:
    repeating = _fake_response(_fake_message_tool_calls([("get_pokemon", {"name_or_id": 1})]))
    fake_client_factory([repeating] * (ai_service.MAX_ITERATIONS + 2))

    r = client.post("/ai/ask", json={"message": "Tu boucles à l'infini"})
    assert r.status_code == 200
    assert _sse_text(r) == ai_service.FAILURE_MESSAGE


def test_ai_empty_content_is_failure(client: TestClient, fake_client_factory) -> None:
    fake_client_factory([_fake_response(SimpleNamespace(content="", tool_calls=None))])

    r = client.post("/ai/ask", json={"message": "rien"})
    assert r.status_code == 200
    assert _sse_text(r) == ai_service.FAILURE_MESSAGE


def test_ai_invalid_tool_json_is_recovered(client: TestClient, fake_client_factory) -> None:
    bad = SimpleNamespace(
        id="call_0", type="function",
        function=SimpleNamespace(name="get_pokemon", arguments="not json"),
    )
    first = SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=None, tool_calls=[bad])
    )])
    second = _fake_response(_fake_message_content("Désolé, requête invalide."))

    fake = fake_client_factory([first, second])
    r = client.post("/ai/ask", json={"message": "test"})
    assert r.status_code == 200

    tool_msg = next(
        m for m in fake.chat.completions.received_calls[1]["messages"]
        if m["role"] == "tool"
    )
    assert "error" in json.loads(tool_msg["content"])


def test_ai_system_prompt_is_injected(client: TestClient, fake_client_factory) -> None:
    fake = fake_client_factory([_fake_response(_fake_message_content("ok"))])
    client.post("/ai/ask", json={"message": "test"})

    msgs = fake.chat.completions.received_calls[0]["messages"]
    assert msgs[0]["role"] == "system"
    assert "FusionDex AI" in msgs[0]["content"]
    assert "Je n'ai pas trouvé" in msgs[0]["content"]


def test_ai_context_is_prepended(client: TestClient, fake_client_factory) -> None:
    fake = fake_client_factory([_fake_response(_fake_message_content("ok"))])
    client.post("/ai/ask", json={
        "message": "Que penses-tu de cette fusion ?",
        "context": "Pokémon affiché : Pikachu id=25",
    })

    user_msg = fake.chat.completions.received_calls[0]["messages"][1]
    assert user_msg["role"] == "user"
    assert "Pikachu id=25" in user_msg["content"]
    assert "Que penses-tu" in user_msg["content"]


def test_ai_history_ordering(client: TestClient, fake_client_factory) -> None:
    fake = fake_client_factory([_fake_response(_fake_message_content("ok"))])
    client.post("/ai/ask", json={
        "message": "question 3",
        "history": [
            {"role": "user",      "content": "question 1"},
            {"role": "assistant", "content": "réponse 1"},
            {"role": "user",      "content": "question 2"},
            {"role": "assistant", "content": "réponse 2"},
        ],
    })

    sent = fake.chat.completions.received_calls[0]["messages"]
    assert sent[0]["role"] == "system"
    assert sent[1] == {"role": "user",      "content": "question 1"}
    assert sent[2] == {"role": "assistant", "content": "réponse 1"}
    assert sent[5]["role"] == "user"
    assert "question 3" in sent[5]["content"]


def test_ai_history_trimmed_to_max(client: TestClient, fake_client_factory) -> None:
    from backend.services.ai_service import MAX_HISTORY_MSGS
    fake = fake_client_factory([_fake_response(_fake_message_content("ok"))])

    long_history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
        for i in range(20)
    ]
    client.post("/ai/ask", json={"message": "nouvelle question", "history": long_history})

    sent = fake.chat.completions.received_calls[0]["messages"]
    assert len(sent) == 1 + MAX_HISTORY_MSGS + 1
