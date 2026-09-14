"""BrowserGym adapter implementing the project's stable environment interface."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from browser.actions import BrowserAction
from browser.observation import Observation, build_observation


class GymEnvironment(Protocol):
    def reset(self, *, seed: int | None = None) -> tuple[Mapping[str, Any], Mapping[str, Any]]: ...

    def step(
        self, action: str
    ) -> tuple[Mapping[str, Any], float, bool, bool, Mapping[str, Any]]: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class StepResult:
    observation: Observation
    reward: float
    terminated: bool
    truncated: bool
    info: Mapping[str, Any]

    @property
    def done(self) -> bool:
        return self.terminated or self.truncated


class BrowserEnvironment:
    """Own a BrowserGym environment while exposing project-native data types."""

    def __init__(self, env: GymEnvironment) -> None:
        self._env = env
        self._observation: Observation | None = None

    @classmethod
    def miniwob(
        cls,
        task_name: str,
        *,
        headless: bool = True,
        **kwargs: Any,
    ) -> BrowserEnvironment:
        import browsergym.miniwob  # noqa: F401 -- registers Gymnasium environments
        import gymnasium as gym

        env = gym.make(f"browsergym/miniwob.{task_name}", headless=headless, **kwargs)
        return cls(env)

    def reset(self, *, seed: int | None = None) -> Observation:
        raw, _info = self._env.reset(seed=seed)
        self._observation = build_observation(raw)
        return self._observation

    def step(self, action: BrowserAction) -> StepResult:
        raw, reward, terminated, truncated, info = self._env.step(action.to_browsergym())
        self._observation = build_observation(raw)
        return StepResult(
            observation=self._observation,
            reward=float(reward),
            terminated=bool(terminated),
            truncated=bool(truncated),
            info=info,
        )

    @property
    def current_url(self) -> str:
        """Return the URL from the latest observation."""
        if self._observation is None:
            raise RuntimeError("Environment must be reset before reading the current URL")
        return self._observation.url

    def close(self) -> None:
        self._env.close()

    def __enter__(self) -> BrowserEnvironment:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
