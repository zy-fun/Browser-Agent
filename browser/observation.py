"""Compact, LLM-readable representation of BrowserGym observations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

INTERACTIVE_ROLES = frozenset(
    {
        "button",
        "checkbox",
        "combobox",
        "link",
        "listbox",
        "menuitem",
        "option",
        "radio",
        "searchbox",
        "slider",
        "spinbutton",
        "switch",
        "tab",
        "textbox",
    }
)

INTERACTIVE_STATE_PROPERTIES = (
    "checked",
    "selected",
    "expanded",
    "pressed",
    "disabled",
)


def _value(node: Mapping[str, Any], key: str) -> str:
    raw = node.get(key, "")
    if isinstance(raw, Mapping):
        raw = raw.get("value", "")
    return str(raw or "").strip()


def _interactive_states(node: Mapping[str, Any]) -> tuple[str, ...]:
    raw_properties = node.get("properties", ())
    if not isinstance(raw_properties, (list, tuple)):
        return ()
    values: dict[str, str] = {}
    for prop in raw_properties:
        if not isinstance(prop, Mapping):
            continue
        name = str(prop.get("name", ""))
        if name not in INTERACTIVE_STATE_PROPERTIES:
            continue
        value = prop.get("value", "")
        if isinstance(value, Mapping):
            value = value.get("value", "")
        if isinstance(value, bool) or value is not None and str(value):
            values[name] = str(value).lower()
    return tuple(
        f"{name}={values[name]}" for name in INTERACTIVE_STATE_PROPERTIES if name in values
    )


@dataclass(frozen=True, slots=True)
class InteractiveElement:
    element_id: str
    role: str
    name: str = ""
    value: str = ""
    states: tuple[str, ...] = ()

    def to_text(self) -> str:
        label = self.name.replace("\n", " ").strip()
        parts = [f"value={self.value!r}"] if self.value else []
        parts.extend(self.states)
        suffix = f" {' '.join(parts)}" if parts else ""
        return f"[{self.element_id}] {self.role} {label!r}{suffix}"


@dataclass(frozen=True, slots=True)
class Observation:
    goal: str
    url: str
    title: str
    elements: tuple[InteractiveElement, ...]
    visible_text: tuple[str, ...] = ()
    last_action_error: str = ""

    def to_text(self, *, max_chars: int = 12_000) -> str:
        lines = [f"Current URL:\n{self.url}", f"Title:\n{self.title}"]
        if self.last_action_error:
            lines.append(f"Last Action Error:\n{self.last_action_error}")
        lines.append("Interactive Elements:")
        lines.extend(element.to_text() for element in self.elements)
        if self.visible_text:
            lines.append("Relevant Text:")
            lines.extend(self.visible_text)
        return "\n".join(lines)[:max_chars]


def _iter_nodes(axtree: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    nodes = axtree.get("nodes", ())
    if isinstance(nodes, (list, tuple)):
        yield from (node for node in nodes if isinstance(node, Mapping))


def build_observation(raw: Mapping[str, Any]) -> Observation:
    """Build a compact observation from BrowserGym's stable observation fields."""
    urls = tuple(str(value) for value in raw.get("open_pages_urls", ()))
    titles = tuple(str(value) for value in raw.get("open_pages_titles", ()))
    active_raw = raw.get("active_page_index", 0)
    try:
        active = int(active_raw[0])
    except (IndexError, TypeError):
        active = int(active_raw or 0)

    url = str(raw.get("url") or (urls[active] if active < len(urls) else ""))
    title = titles[active] if active < len(titles) else ""
    extras = raw.get("extra_element_properties", {})
    if not isinstance(extras, Mapping):
        extras = {}

    elements: list[InteractiveElement] = []
    visible_text: list[str] = []
    seen: set[str] = set()
    axtree = raw.get("axtree_object", {})
    if not isinstance(axtree, Mapping):
        axtree = {}

    for node in _iter_nodes(axtree):
        role = _value(node, "role").lower()
        name = _value(node, "name")
        element_id = _value(node, "browsergym_id")
        value = _value(node, "value")
        properties = extras.get(element_id, {}) if element_id else {}
        visible = not isinstance(properties, Mapping) or properties.get("visibility", 1) > 0

        if element_id and visible and element_id not in seen and role in INTERACTIVE_ROLES:
            elements.append(
                InteractiveElement(
                    element_id,
                    role,
                    name,
                    value,
                    _interactive_states(node),
                )
            )
            seen.add(element_id)
        elif role in {"statictext", "heading"} and name and len(name) <= 500:
            if name not in visible_text:
                visible_text.append(name)

    return Observation(
        goal=str(raw.get("goal", "")),
        url=url,
        title=title,
        elements=tuple(elements),
        visible_text=tuple(visible_text[:50]),
        last_action_error=str(raw.get("last_action_error", "")),
    )
