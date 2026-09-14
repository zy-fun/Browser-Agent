"""Lightweight high-level planning for M3 browser tasks."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from agent.prompt import PLANNER_CREATE_PROMPT, PLANNER_UPDATE_PROMPT
from browser.observation import Observation
from llm.client import LLMClient, LLMError

T = TypeVar("T")


class PlanError(RuntimeError):
    """Raised when a plan cannot be created or updated safely."""


@dataclass(frozen=True, slots=True)
class PlanStep:
    step_id: int
    description: str


@dataclass(frozen=True, slots=True)
class Plan:
    goal: str
    steps: tuple[PlanStep, ...]


@dataclass(frozen=True, slots=True)
class PlanState:
    plan: Plan
    completed_step_ids: tuple[int, ...] = ()
    current_step_id: int | None = None

    def to_text(self) -> str:
        completed = set(self.completed_step_ids)
        lines = [f"Goal:\n{self.plan.goal}", "Plan:"]
        for step in self.plan.steps:
            if step.step_id in completed:
                status = "completed"
            elif step.step_id == self.current_step_id:
                status = "current"
            else:
                status = "pending"
            lines.append(f"[{status}] {step.step_id}. {step.description}")
        return "\n".join(lines)


@dataclass(slots=True)
class PlannerUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class TaskPlanner:
    """Create a plan, then update only its execution state after each action."""

    def __init__(self, llm: LLMClient, *, retries: int = 2, max_steps: int = 8) -> None:
        if retries < 0:
            raise ValueError("retries cannot be negative")
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")
        self.llm = llm
        self.retries = retries
        self.max_steps = max_steps
        self.usage = PlannerUsage()

    def create_plan(self, task: str, observation: Observation) -> PlanState:
        messages = [
            {"role": "system", "content": PLANNER_CREATE_PROMPT},
            {
                "role": "user",
                "content": f"Task:\n{task}\n\nCurrent Observation:\n{observation.to_text()}",
            },
        ]
        plan = self._request(messages, self._parse_plan)
        return PlanState(plan=plan, current_step_id=plan.steps[0].step_id)

    def update_plan(
        self,
        state: PlanState,
        observation: Observation,
        history: Sequence[str],
    ) -> PlanState:
        history_text = "\n".join(history[-8:]) or "(none)"
        messages = [
            {"role": "system", "content": PLANNER_UPDATE_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Plan State:\n{state.to_text()}\n\n"
                    f"Recent Action History:\n{history_text}\n\n"
                    f"Current Observation:\n{observation.to_text()}"
                ),
            },
        ]
        completed, current = self._request(
            messages,
            lambda text: self._parse_update(text, state.plan),
        )
        return PlanState(state.plan, completed, current)

    def _request(self, messages: list[dict[str, str]], parser: Callable[[str], T]) -> T:
        last_error = ""
        for attempt in range(self.retries + 1):
            try:
                response = self.llm.complete(messages)
            except LLMError as exc:
                last_error = str(exc)
            else:
                self.usage.input_tokens += response.input_tokens
                self.usage.output_tokens += response.output_tokens
                self.usage.total_tokens += response.total_tokens
                try:
                    return parser(response.text)
                except PlanError as exc:
                    last_error = str(exc)
                    messages.extend(
                        [
                            {"role": "assistant", "content": response.text},
                            {
                                "role": "user",
                                "content": (
                                    f"Invalid plan response: {last_error}. Return JSON only."
                                ),
                            },
                        ]
                    )
            if attempt == self.retries:
                break
        raise PlanError(f"Planner failed after {self.retries + 1} attempts: {last_error}")

    def _parse_plan(self, text: str) -> Plan:
        payload = _json_object(text)
        if set(payload) != {"goal", "steps"}:
            raise PlanError("Plan requires exactly 'goal' and 'steps'")
        goal = payload["goal"]
        raw_steps = payload["steps"]
        if not isinstance(goal, str) or not goal.strip():
            raise PlanError("Plan goal must be a non-empty string")
        if not isinstance(raw_steps, list) or not 1 <= len(raw_steps) <= self.max_steps:
            raise PlanError(f"Plan must contain 1 to {self.max_steps} steps")
        steps = []
        for expected_id, item in enumerate(raw_steps, 1):
            if not isinstance(item, dict) or set(item) != {"id", "description"}:
                raise PlanError("Each plan step requires exactly 'id' and 'description'")
            if item["id"] != expected_id:
                raise PlanError("Plan step ids must be consecutive integers starting at 1")
            description = item["description"]
            if not isinstance(description, str) or not description.strip():
                raise PlanError("Plan step descriptions must be non-empty strings")
            steps.append(PlanStep(expected_id, description.strip()))
        return Plan(goal.strip(), tuple(steps))

    @staticmethod
    def _parse_update(text: str, plan: Plan) -> tuple[tuple[int, ...], int | None]:
        payload = _json_object(text)
        if set(payload) != {"completed", "current"}:
            raise PlanError("Plan update requires exactly 'completed' and 'current'")
        completed = payload["completed"]
        current = payload["current"]
        if not isinstance(completed, list) or any(type(item) is not int for item in completed):
            raise PlanError("'completed' must be a list of integer step ids")
        expected_prefix = list(range(1, len(completed) + 1))
        if completed != expected_prefix or len(completed) > len(plan.steps):
            raise PlanError("Completed steps must be a valid consecutive prefix")
        expected_current = len(completed) + 1 if len(completed) < len(plan.steps) else None
        if current != expected_current:
            raise PlanError(f"Current step must be {expected_current!r}")
        return tuple(completed), current


def _json_object(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PlanError(f"Invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise PlanError("Planner response must be a JSON object")
    return payload
