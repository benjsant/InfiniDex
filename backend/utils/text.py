"""Text utilities — accent-insensitive search normalization."""

from __future__ import annotations

import unicodedata


def ilike_escape(text: str) -> str:
    """Escape ILIKE special characters (%, _, \\) in user-supplied search strings.

    Always pair with escape="\\\\" in the SQLAlchemy ilike() call.
    """
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def normalize(text: str) -> str:
    """Lowercase + strip accents (NFD decomposition).

    Used for accent-insensitive search on EN/FR names.
    Example: "Éclair" → "eclair", "Pokémon" → "pokemon"
    """
    return "".join(
        c
        for c in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(c) != "Mn"
    )
