"""DeepSeek Chat Completions implementation of the common LLM boundary."""

from __future__ import annotations

import os
from collections.abc import Sequence

from llm.client import LLMRequestError, LLMResponse, LLMResponseError

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekClient:
    """Call DeepSeek through its OpenAI-compatible Chat Completions API."""

    def __init__(
        self,
        model: str,
        *,
        max_output_tokens: int = 800,
        base_url: str | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("A DeepSeek model name is required")
        if max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not set")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError('Install LLM support with: pip install -e ".[llm]"') from exc

        self.model = model
        self.max_output_tokens = max_output_tokens
        self.base_url = base_url or os.environ.get(
            "DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL
        )
        self._client = OpenAI(api_key=api_key, base_url=self.base_url)

    @classmethod
    def from_env(
        cls,
        model: str | None = None,
        *,
        max_output_tokens: int = 800,
    ) -> DeepSeekClient:
        selected_model = model or os.environ.get("DEEPSEEK_MODEL") or os.environ.get(
            "LLM_MODEL", ""
        )
        if not selected_model:
            raise RuntimeError("Provide --model or set DEEPSEEK_MODEL (or LLM_MODEL)")
        return cls(selected_model, max_output_tokens=max_output_tokens)

    @staticmethod
    def _normalize_messages(
        messages: Sequence[dict[str, str]],
    ) -> list[dict[str, str]]:
        # DeepSeek Chat Completions uses the portable `system` role rather than
        # the OpenAI Responses-specific `developer` role.
        return [
            {"role": "system" if message["role"] == "developer" else message["role"],
             "content": message["content"]}
            for message in messages
        ]

    def complete(self, messages: Sequence[dict[str, str]]) -> LLMResponse:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=self._normalize_messages(messages),
                max_tokens=self.max_output_tokens,
                tools=[],
                tool_choice="none",
            )
        except Exception as exc:
            raise LLMRequestError(f"DeepSeek request failed: {exc}") from exc
        choice = response.choices[0]
        text = choice.message.content
        if not isinstance(text, str) or not text.strip():
            raise LLMResponseError("DeepSeek returned an empty text response")
        if getattr(choice, "finish_reason", None) == "length":
            raise LLMResponseError(
                "DeepSeek response was truncated; increase max_output_tokens"
            )
        usage = response.usage
        return LLMResponse(
            text=text,
            input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            total_tokens=getattr(usage, "total_tokens", 0) if usage else 0,
        )
