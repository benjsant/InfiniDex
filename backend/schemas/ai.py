"""Pydantic schemas for the AI assistant endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=2000)


class AiRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    context: str | None = Field(None, max_length=500)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=20)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message cannot be whitespace-only")
        return v


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


class FeedbackRequest(BaseModel):
    question: str = Field(..., max_length=2000)
    answer: str = Field(..., max_length=4000)
    rating: Literal["up", "down"]
