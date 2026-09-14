"""OpenAI Responses API implementation of the common LLM boundary."""

from __future__ import annotations

import os
from collections.abc import Sequence

from llm.client import LLMRequestError, LLMResponse, LLMResponseError


class OpenAIResponsesClient:
    """Use OpenAI as text-in/text-out only, with hosted tools disabled."""

    def __init__(self, model: str, *, max_output_tokens: int = 800) -> None:
        if not model.strip():
            raise ValueError("An OpenAI model name is required")
        if max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")
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
    def from_env(
        cls,
        model: str | None = None,
        *,
        max_output_tokens: int = 800,
    ) -> OpenAIResponsesClient:
        selected_model = model or os.environ.get("OPENAI_MODEL") or os.environ.get("LLM_MODEL", "")
        if not selected_model:
            raise RuntimeError("Provide --model or set OPENAI_MODEL (or LLM_MODEL)")
        return cls(selected_model, max_output_tokens=max_output_tokens)

    def complete(self, messages: Sequence[dict[str, str]]) -> LLMResponse:
        try:
            response = self._client.responses.create(
                model=self.model,
                input=list(messages),
                max_output_tokens=self.max_output_tokens,
                tools=[],
                tool_choice="none",
                store=False,
            )
        except Exception as exc:
            raise LLMRequestError(f"OpenAI request failed: {exc}") from exc
        text = response.output_text
        if not isinstance(text, str) or not text.strip():
            raise LLMResponseError("OpenAI returned an empty text response")
        usage = response.usage
        return LLMResponse(
            text=text,
            input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
            total_tokens=getattr(usage, "total_tokens", 0) if usage else 0,
        )
