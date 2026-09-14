"""Strict parsing of model-produced browser decisions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from browser.actions import ActionType, BrowserAction


class ActionParseError(ValueError):
    """Raised when a model response does not match the decision schema."""


@dataclass(frozen=True, slots=True)
class AgentDecision:
    reason: str
    action: BrowserAction
    raw_response: str = ""


def _load_payload(response: str) -> dict[str, Any]:
    try:
        payload: Any = json.loads(response)
    except json.JSONDecodeError as exc:
        raise ActionParseError(f"Invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ActionParseError("Decision must be a JSON object")
    unknown = set(payload) - {"reason", "action"}
    if unknown:
        raise ActionParseError(f"Unknown decision fields: {sorted(unknown)}")
    return payload


def parse_decision(response: str) -> AgentDecision:
    """Parse one complete decision without guessing or repairing malformed output."""
    payload = _load_payload(response)
    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ActionParseError("Decision requires a non-empty 'reason'")

    action_payload = payload.get("action")
    if not isinstance(action_payload, dict):
        raise ActionParseError("Decision must contain an 'action' object")

    allowed = {"type", "element_id", "text", "option", "direction", "url", "message"}
    unknown = set(action_payload) - allowed
    if unknown:
        raise ActionParseError(f"Unknown action fields: {sorted(unknown)}")

    try:
        action = BrowserAction(
            type=ActionType(action_payload.get("type")),
            element_id=action_payload.get("element_id"),
            text=action_payload.get("text"),
            option=action_payload.get("option"),
            direction=action_payload.get("direction"),
            url=action_payload.get("url"),
            message=action_payload.get("message"),
        )
    except (TypeError, ValueError) as exc:
        raise ActionParseError(str(exc)) from exc
    return AgentDecision(reason=reason.strip(), action=action, raw_response=response)


def parse_action(response: str) -> BrowserAction:
    """Backward-compatible convenience wrapper returning only the action."""
    return parse_decision(response).action
