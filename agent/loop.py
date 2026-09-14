"""Bounded Observation -> Reason -> Action execution loop."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from agent.agent import AgentDecisionError, ReActAgent
from agent.parser import AgentDecision
from browser.actions import ActionType
from browser.environment import BrowserEnvironment
from browser.observation import Observation


@dataclass(frozen=True, slots=True)
class ExecutionStep:
    number: int
    decision: AgentDecision
    url: str
    reward: float = 0.0
    error: str = ""

    def history_line(self) -> str:
        action = self.decision.action
        outcome = f"reward={self.reward:g}"
        if self.error:
            outcome += f" error={self.error!r}"
        return f"{self.number}. reason={self.decision.reason!r} action={action!r} {outcome}"


@dataclass(frozen=True, slots=True)
class EpisodeResult:
    task: str
    observation: Observation
    steps: tuple[ExecutionStep, ...]
    total_reward: float
    success: bool
    stop_reason: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


StepCallback = Callable[[ExecutionStep, Observation], None]


def run_episode(
    env: BrowserEnvironment,
    agent: ReActAgent,
    *,
    task: str | None = None,
    seed: int | None = None,
    max_steps: int = 30,
    max_stalled_repeats: int = 3,
    on_step: StepCallback | None = None,
) -> EpisodeResult:
    """Run one bounded episode and preserve enough state for benchmark reporting."""
    if max_steps <= 0:
        raise ValueError("max_steps must be positive")
    if max_stalled_repeats < 0:
        raise ValueError("max_stalled_repeats cannot be negative")

    initial_input_tokens = agent.usage.input_tokens
    initial_output_tokens = agent.usage.output_tokens
    initial_total_tokens = agent.usage.total_tokens
    observation = env.reset(seed=seed)
    effective_task = (task or observation.goal).strip()
    if not effective_task:
        raise ValueError("No task instruction was provided by the caller or environment")

    steps: list[ExecutionStep] = []
    total_reward = 0.0
    stop_reason = "max_steps"
    stalled_action = None
    stalled_repeats = 0

    for number in range(1, max_steps + 1):
        history = tuple(step.history_line() for step in steps)
        try:
            decision = agent.step(effective_task, observation, history)
        except AgentDecisionError as exc:
            stop_reason = f"agent_error: {exc}"
            break

        if decision.action.type is ActionType.FINISH:
            step = ExecutionStep(number=number, decision=decision, url=observation.url)
            steps.append(step)
            if on_step:
                on_step(step, observation)
            stop_reason = "agent_finish"
            break

        previous_state = _page_fingerprint(observation)
        try:
            result = env.step(decision.action)
        except Exception as exc:  # Browser failures must end the episode with a trace.
            step = ExecutionStep(
                number=number,
                decision=decision,
                url=observation.url,
                error=f"{type(exc).__name__}: {exc}",
            )
            steps.append(step)
            if on_step:
                on_step(step, observation)
            stop_reason = "environment_error"
            break

        observation = result.observation
        total_reward += result.reward
        step = ExecutionStep(
            number=number,
            decision=decision,
            url=observation.url,
            reward=result.reward,
            error=observation.last_action_error,
        )
        steps.append(step)
        if on_step:
            on_step(step, observation)
        if result.done:
            stop_reason = "environment_done"
            break
        no_progress = result.reward <= 0 and _page_fingerprint(observation) == previous_state
        if no_progress and decision.action == stalled_action:
            stalled_repeats += 1
        elif no_progress:
            stalled_action = decision.action
            stalled_repeats = 1
        else:
            stalled_action = None
            stalled_repeats = 0
        if max_stalled_repeats and stalled_repeats >= max_stalled_repeats:
            stop_reason = "stalled_repeated_action"
            break

    return EpisodeResult(
        task=effective_task,
        observation=observation,
        steps=tuple(steps),
        total_reward=total_reward,
        success=stop_reason == "environment_done" and total_reward > 0,
        stop_reason=stop_reason,
        input_tokens=agent.usage.input_tokens - initial_input_tokens,
        output_tokens=agent.usage.output_tokens - initial_output_tokens,
        total_tokens=agent.usage.total_tokens - initial_total_tokens,
    )


def _page_fingerprint(observation: Observation) -> tuple[object, ...]:
    """Compare visible task state while ignoring transient action-error text."""
    return (
        observation.url,
        observation.title,
        observation.elements,
        observation.visible_text,
    )
