"""Provider-neutral LLM boundary and OpenAI Responses API implementation."""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class LLMClient(Protocol):
    def complete(self, messages: Sequence[dict[str, str]]) -> LLMResponse: ...


class OpenAIResponsesClient:
    """Use OpenAI only as a text-in/text-out model, with every hosted tool disabled."""

    def __init__(self, model: str, *, max_output_tokens: int = 800) -> None:
        if not model.strip():
            raise ValueError("An OpenAI model name is required")
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError('Install LLM support with: pip install -e ".[llm]"') from exc

        self.model = model
        self.max_output_tokens = max_output_tokens
        self._client = OpenAI()

    @classmethod
    def from_env(cls, model: str | None = None) -> OpenAIResponsesClient:
        selected_model = model or os.environ.get("OPENAI_MODEL", "")
        if not selected_model:
            raise RuntimeError("Provide --model or set OPENAI_MODEL")
        return cls(selected_model)

    def complete(self, messages: Sequence[dict[str, str]]) -> LLMResponse:
        response = self._client.responses.create(
            model=self.model,
            input=list(messages),
            max_output_tokens=self.max_output_tokens,
            tools=[],
            tool_choice="none",
            store=False,
        )
        usage = response.usage
        return LLMResponse(
            text=response.output_text,
            input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
            total_tokens=getattr(usage, "total_tokens", 0) if usage else 0,
        )
