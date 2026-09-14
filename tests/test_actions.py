import pytest

from browser.actions import ActionType, BrowserAction


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        (BrowserAction(ActionType.CLICK, element_id="a12"), "click('a12')"),
        (BrowserAction(ActionType.TYPE, element_id="a1", text="hello"), "fill('a1', 'hello')"),
        (
            BrowserAction(ActionType.SELECT, element_id="a2", option="Blue"),
            "select_option('a2', 'Blue')",
        ),
        (BrowserAction(ActionType.SCROLL, direction="down"), "scroll(0, 600)"),
        (BrowserAction(ActionType.GO_BACK), "go_back()"),
    ],
)
def test_browsergym_serialization(action: BrowserAction, expected: str) -> None:
    assert action.to_browsergym() == expected


def test_text_is_escaped() -> None:
    action = BrowserAction(ActionType.TYPE, element_id="a1", text="O'Reilly")
    assert action.to_browsergym() == "fill('a1', \"O'Reilly\")"


def test_missing_required_field_is_rejected() -> None:
    with pytest.raises(ValueError, match="requires 'element_id'"):
        BrowserAction(ActionType.CLICK)


def test_invalid_navigation_url_is_rejected() -> None:
    with pytest.raises(ValueError, match="absolute HTTP"):
        BrowserAction(ActionType.NAVIGATE, url="javascript:alert(1)")


def test_unexpected_fields_are_rejected() -> None:
    with pytest.raises(ValueError, match="unexpected fields"):
        BrowserAction(ActionType.CLICK, element_id="a1", text="hidden payload")
