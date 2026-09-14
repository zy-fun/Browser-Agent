"""Configuration and construction for supported LLM providers."""

from __future__ import annotations

import os
from enum import StrEnum

from llm.client import LLMClient
from llm.deepseek_client import DeepSeekClient
from llm.openai_client import OpenAIResponsesClient


class LLMProvider(StrEnum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"


def create_llm_client(
    provider: str | LLMProvider | None = None,
    *,
    model: str | None = None,
    max_output_tokens: int = 800,
) -> LLMClient:
    """Create a provider client from explicit arguments and environment variables."""
    provider_name = provider or os.environ.get("LLM_PROVIDER", LLMProvider.OPENAI.value)
    try:
        selected_provider = LLMProvider(str(provider_name).strip().lower())
    except ValueError as exc:
        supported = ", ".join(item.value for item in LLMProvider)
        raise ValueError(
            f"Unsupported LLM provider {provider_name!r}; choose: {supported}"
        ) from exc

    if selected_provider is LLMProvider.OPENAI:
        return OpenAIResponsesClient.from_env(
            model,
            max_output_tokens=max_output_tokens,
        )
    return DeepSeekClient.from_env(
        model,
        max_output_tokens=max_output_tokens,
    )
