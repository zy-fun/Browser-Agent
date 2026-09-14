"""Typed actions and deterministic BrowserGym serialization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse


class ActionType(StrEnum):
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    SELECT = "select"
    NAVIGATE = "navigate"
    GO_BACK = "go_back"
    FINISH = "finish"


def _quote(value: str) -> str:
    """Render a safe Python-style string literal for BrowserGym actions."""
    return repr(value)


@dataclass(frozen=True, slots=True)
class BrowserAction:
    type: ActionType
    element_id: str | None = None
    text: str | None = None
    option: str | None = None
    direction: str | None = None
    url: str | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        fields = {
            "element_id": self.element_id,
            "text": self.text,
            "option": self.option,
            "direction": self.direction,
            "url": self.url,
            "message": self.message,
        }
        required: dict[ActionType, tuple[str, ...]] = {
            ActionType.CLICK: ("element_id",),
            ActionType.TYPE: ("element_id", "text"),
            ActionType.SELECT: ("element_id", "option"),
            ActionType.SCROLL: ("direction",),
            ActionType.NAVIGATE: ("url",),
            ActionType.FINISH: ("message",),
        }
        allowed = set(required.get(self.type, ()))
        unexpected = {name for name, value in fields.items() if value is not None} - allowed
        if unexpected:
            raise ValueError(f"{self.type.value} received unexpected fields: {sorted(unexpected)}")
        for field_name in required.get(self.type, ()):
            if getattr(self, field_name) is None:
                raise ValueError(f"{self.type.value} requires '{field_name}'")
        for field_name, value in fields.items():
            if value is not None and not isinstance(value, str):
                raise ValueError(f"'{field_name}' must be a string")
        if self.element_id == "":
            raise ValueError("'element_id' cannot be empty")

        if self.direction is not None and self.direction not in {"up", "down"}:
            raise ValueError("scroll direction must be 'up' or 'down'")
        if self.type is ActionType.NAVIGATE:
            parsed = urlparse(self.url or "")
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("navigate requires an absolute HTTP(S) URL")

    def to_browsergym(self, *, scroll_amount: int = 600) -> str:
        """Translate the project schema to BrowserGym's high-level action language."""
        match self.type:
            case ActionType.CLICK:
                return f"click({_quote(self.element_id or '')})"
            case ActionType.TYPE:
                return f"fill({_quote(self.element_id or '')}, {_quote(self.text or '')})"
            case ActionType.SELECT:
                element_id = _quote(self.element_id or "")
                option = _quote(self.option or "")
                return f"select_option({element_id}, {option})"
            case ActionType.SCROLL:
                dy = scroll_amount if self.direction == "down" else -scroll_amount
                return f"scroll(0, {dy})"
            case ActionType.NAVIGATE:
                return f"goto({_quote(self.url or '')})"
            case ActionType.GO_BACK:
                return "go_back()"
            case ActionType.FINISH:
                return f"send_msg_to_user({_quote(self.message or '')})"
