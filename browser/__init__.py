"""Browser environment and structured page representation."""

from browser.actions import ActionType, BrowserAction
from browser.environment import BrowserEnvironment, StepResult
from browser.observation import InteractiveElement, Observation

__all__ = [
    "ActionType",
    "BrowserAction",
    "BrowserEnvironment",
    "InteractiveElement",
    "Observation",
    "StepResult",
]
