"""Provider-neutral LLM types used by the browser agent."""

from __future__ import annotations

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
    """Minimal text-in/text-out boundary implemented by every provider."""

    def complete(self, messages: Sequence[dict[str, str]]) -> LLMResponse: ...


class LLMError(RuntimeError):
    """Base class for recoverable provider and response failures."""


class LLMRequestError(LLMError):
    """Raised when a provider request fails before a usable response arrives."""


class LLMResponseError(LLMError):
    """Raised when a provider returns no usable text response."""
