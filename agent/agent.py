"""Minimal agent interface reserved for the M2 ReAct implementation."""

from __future__ import annotations

from typing import Protocol

from browser.actions import BrowserAction
from browser.observation import Observation


class BrowserAgent(Protocol):
    """Choose exactly one browser action from the current structured state."""

    def step(
        self,
        task: str,
        observation: Observation,
        history: tuple[BrowserAction, ...],
    ) -> BrowserAction: ...
