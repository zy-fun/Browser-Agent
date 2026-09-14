"""Provider-neutral LLM client interface."""

from collections.abc import Sequence
from typing import Protocol


class LLMClient(Protocol):
    def complete(self, messages: Sequence[dict[str, str]]) -> str: ...
