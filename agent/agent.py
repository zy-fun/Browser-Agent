"""Minimal LLM-driven ReAct browser agent."""

from __future__ import annotations

from dataclasses import dataclass

from agent.parser import ActionParseError, AgentDecision, parse_decision
from agent.prompt import REACT_SYSTEM_PROMPT, render_react_state
from browser.actions import ActionType
from browser.observation import Observation
from llm.client import LLMClient


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
    ) -> None:
        if decision_retries < 0:
            raise ValueError("decision_retries cannot be negative")
        self.llm = llm
        self.history_limit = history_limit
        self.decision_retries = decision_retries
        self.usage = TokenUsage()

    def step(
        self,
        task: str,
        observation: Observation,
        history: tuple[str, ...],
    ) -> AgentDecision:
        messages = [
            {"role": "developer", "content": REACT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": render_react_state(
                    task,
                    observation,
                    history,
                    history_limit=self.history_limit,
                ),
            },
        ]
        last_error = ""
        for attempt in range(self.decision_retries + 1):
            response = self.llm.complete(messages)
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

    @staticmethod
    def _validate_target(decision: AgentDecision, observation: Observation) -> None:
        if decision.action.type not in {ActionType.CLICK, ActionType.TYPE, ActionType.SELECT}:
            return
        valid_ids = {element.element_id for element in observation.elements}
        if decision.action.element_id not in valid_ids:
            raise ActionParseError(
                f"Element id {decision.action.element_id!r} is not in the current observation"
            )
