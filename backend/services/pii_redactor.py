"""PII redactor — strips personally-identifiable data from tool results.

Applied to every tool result *before* it is JSON-serialised and injected into
the LLM message thread.  The goal is defensive: even if a future tool starts
returning sprite-creator names or user-generated text, they never reach the
model.

Rules applied (in order):
  1. Remove dict keys that are known creator/username fields at any depth.
  2. In remaining string values, replace Discord tag patterns (Name#1234) and
     @-mentions with the sentinel "[redacted]".
"""

from __future__ import annotations

import re

# Keys whose values are stripped entirely (replaced with None or removed).
_PII_KEYS: frozenset[str] = frozenset({
    "creator",
    "creators",
    "creator_name",
    "creator_names",
    "username",
    "discord_name",
    "discord_tag",
    "author",
    "submitted_by",
})

# Patterns in free-form strings that may contain real usernames.
# Order matters: most-specific first.
_DISCORD_TAG_RE = re.compile(r"\b\w[\w .]{0,30}#\d{4}\b")   # Name#1234
_AT_MENTION_RE  = re.compile(r"@[\w][\w.-]{0,60}")           # @username


def _redact_str(value: str) -> str:
    value = _DISCORD_TAG_RE.sub("[redacted]", value)
    value = _AT_MENTION_RE.sub("[redacted]", value)
    return value


def redact(obj: object) -> object:
    """Recursively redact PII from a tool-result payload.

    Accepts any JSON-serialisable structure (dict, list, str, int, …) and
    returns the same structure with PII removed.  The input is never mutated.
    """
    if isinstance(obj, dict):
        result: dict = {}
        for key, val in obj.items():
            if key in _PII_KEYS:
                # Drop the key entirely — the LLM does not need it.
                continue
            result[key] = redact(val)
        return result

    if isinstance(obj, list):
        return [redact(item) for item in obj]

    if isinstance(obj, str):
        return _redact_str(obj)

    # int, float, bool, None — pass through unchanged.
    return obj
