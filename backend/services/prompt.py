"""System prompt for the InfiniDex AI agent — loaded from prompts/system.md."""

from pathlib import Path

_PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "system.md"

SYSTEM_PROMPT: str = _PROMPT_FILE.read_text(encoding="utf-8").strip()
