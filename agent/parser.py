"""Strict parsing of model-produced browser actions."""

from __future__ import annotations

import json
from typing import Any

from browser.actions import ActionType, BrowserAction


class ActionParseError(ValueError):
    """Raised when a model response does not match the action schema."""


def parse_action(response: str) -> BrowserAction:
    """Parse a JSON decision without guessing or repairing malformed output."""
    try:
        payload: Any = json.loads(response)
    except json.JSONDecodeError as exc:
        raise ActionParseError(f"Invalid JSON: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise ActionParseError("Decision must be a JSON object")

    action_payload = payload.get("action")
    if not isinstance(action_payload, dict):
        raise ActionParseError("Decision must contain an 'action' object")

    allowed = {"type", "element_id", "text", "option", "direction", "url", "message"}
    unknown = set(action_payload) - allowed
    if unknown:
        raise ActionParseError(f"Unknown action fields: {sorted(unknown)}")

    try:
        return BrowserAction(
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
