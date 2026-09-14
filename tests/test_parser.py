import pytest

from agent.parser import ActionParseError, parse_action, parse_decision
from browser.actions import ActionType


def test_parse_action() -> None:
    action = parse_action(
        '{"reason":"Search", "action":{"type":"type","element_id":"a12","text":"Mac"}}'
    )
    assert action.type is ActionType.TYPE
    assert action.element_id == "a12"


def test_parse_action_rejects_unknown_fields() -> None:
    with pytest.raises(ActionParseError, match="Unknown action fields"):
        parse_action(
            '{"reason":"Click","action":{"type":"click","element_id":"a12","selector":"#bad"}}'
        )


def test_parse_action_rejects_invalid_json() -> None:
    with pytest.raises(ActionParseError, match="Invalid JSON"):
        parse_action("click(a12)")


def test_parse_decision_requires_reason() -> None:
    with pytest.raises(ActionParseError, match="non-empty 'reason'"):
        parse_decision('{"action":{"type":"click","element_id":"a12"}}')
