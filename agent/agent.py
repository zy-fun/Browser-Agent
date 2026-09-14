"""Minimal LLM-driven ReAct browser agent."""

from __future__ import annotations

import time
from dataclasses import dataclass

from agent.parser import ActionParseError, AgentDecision, parse_decision
from agent.prompt import REACT_SYSTEM_PROMPT, render_react_state
from browser.actions import ActionType
from browser.observation import Observation
from llm.client import LLMClient, LLMError, LLMResponse


class AgentDecisionError(RuntimeError):
    """Raised after the model repeatedly produces an unusable decision."""


@dataclass(slots=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class ReActAgent:
    """Ask an LLM for one validated browser action at a time."""

    def __init__(
        self,
        llm: LLMClient,
        *,
        history_limit: int = 8,
        decision_retries: int = 2,
        llm_retries: int = 1,
        llm_retry_delay: float = 1.0,
    ) -> None:
        if decision_retries < 0:
            raise ValueError("decision_retries cannot be negative")
        if llm_retries < 0:
            raise ValueError("llm_retries cannot be negative")
        if llm_retry_delay < 0:
            raise ValueError("llm_retry_delay cannot be negative")
        self.llm = llm
        self.history_limit = history_limit
        self.decision_retries = decision_retries
        self.llm_retries = llm_retries
        self.llm_retry_delay = llm_retry_delay
        self.usage = TokenUsage()

    def step(
        self,
        task: str,
        observation: Observation,
        history: tuple[str, ...],
        plan: str = "",
    ) -> AgentDecision:
        messages = [
            {"role": "system", "content": REACT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": render_react_state(
                    task,
                    observation,
                    history,
                    history_limit=self.history_limit,
                    plan=plan,
                ),
            },
        ]
        last_error = ""
        for attempt in range(self.decision_retries + 1):
            response = self._complete(messages)
            self.usage.input_tokens += response.input_tokens
            self.usage.output_tokens += response.output_tokens
            self.usage.total_tokens += response.total_tokens
            try:
                decision = parse_decision(response.text)
                self._validate_target(decision, observation)
                return decision
            except ActionParseError as exc:
                last_error = str(exc)
                if attempt < self.decision_retries:
                    messages.extend(
                        [
                            {"role": "assistant", "content": response.text},
                            {
                                "role": "user",
                                "content": (
                                    f"Invalid decision: {last_error}. Return corrected JSON only."
                                ),
                            },
                        ]
                    )
        raise AgentDecisionError(
            f"Model failed to produce a valid decision after "
            f"{self.decision_retries + 1} attempts: {last_error}"
        )

    def _complete(self, messages: list[dict[str, str]]) -> LLMResponse:
        """Retry provider-level failures separately from malformed decisions."""
        last_error: LLMError | None = None
        for attempt in range(self.llm_retries + 1):
            try:
                return self.llm.complete(messages)
            except LLMError as exc:
                last_error = exc
                if attempt < self.llm_retries and self.llm_retry_delay:
                    time.sleep(self.llm_retry_delay * (2**attempt))
        raise AgentDecisionError(
            f"LLM request failed after {self.llm_retries + 1} attempts: {last_error}"
        ) from last_error

    @staticmethod
    def _validate_target(decision: AgentDecision, observation: Observation) -> None:
        if decision.action.type not in {ActionType.CLICK, ActionType.TYPE, ActionType.SELECT}:
            return
        valid_ids = {element.element_id for element in observation.elements}
        if decision.action.element_id not in valid_ids:
            raise ActionParseError(
                f"Element id {decision.action.element_id!r} is not in the current observation"
            )
