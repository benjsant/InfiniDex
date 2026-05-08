"""Pydantic schemas for the AI assistant endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AiRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    context: str | None = Field(None, max_length=500)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=20)


class AiProviderInfo(BaseModel):
    name: str
    model: str


class AiToolInfo(BaseModel):
    name: str
    description: str


class AiPromptInfo(BaseModel):
    system_prompt: str
    tools: list[AiToolInfo]
    max_history_messages: int
