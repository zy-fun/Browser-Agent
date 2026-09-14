"""Centralized prompts and state rendering for the M2 ReAct agent."""

from __future__ import annotations

from collections.abc import Sequence

from browser.observation import Observation

REACT_SYSTEM_PROMPT = """You are a text-based browser agent operating BrowserGym.
Choose exactly one action that makes concrete progress toward the user's task.
Use only element identifiers shown in the current observation. Never invent an identifier.
Respect control states such as checked, selected, expanded, pressed, and disabled.
Return exactly one JSON object and no Markdown or surrounding prose.

Schema:
{
  "reason": "brief reason for the next action",
  "action": {
    "type": "click|type|scroll|select|navigate|go_back|finish",
    "element_id": "required for click, type, and select",
    "text": "required for type",
    "option": "required for select",
    "direction": "up|down; required for scroll",
    "url": "absolute HTTP(S) URL; required for navigate",
    "message": "required for finish"
  }
}

Include only fields used by the selected action. Use finish only when the task is complete or cannot
be completed from the available page state. Keep the reason short.
"""


def render_react_state(
    task: str,
    observation: Observation,
    history: Sequence[str],
    *,
    history_limit: int = 8,
) -> str:
    recent = list(history[-history_limit:])
    history_text = "\n".join(recent) if recent else "(none)"
    return (
        f"Task:\n{task}\n\n"
        f"Recent Action History:\n{history_text}\n\n"
        f"Current Observation:\n{observation.to_text()}"
    )
