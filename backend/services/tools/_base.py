"""Base class for agent tools.

Each tool encapsulates its name, JSON Schema spec, and async handler in one
object. Adding a new tool means creating one Tool instance — nothing else to
update in separate dicts or lists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from sqlalchemy.orm import Session

Handler = Callable[[Session, dict[str, Any]], Awaitable[dict]]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Handler

    def to_spec(self) -> dict:
        """Return the OpenAI function-calling spec for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
