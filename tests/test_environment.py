from typing import Any

from browser.actions import ActionType, BrowserAction
from browser.environment import BrowserEnvironment

RAW_OBSERVATION: dict[str, Any] = {
    "url": "https://example.test",
    "open_pages_urls": ("https://example.test",),
    "open_pages_titles": ("Example",),
    "active_page_index": [0],
    "axtree_object": {"nodes": []},
    "extra_element_properties": {},
    "last_action_error": "",
}


class FakeGymEnvironment:
    def __init__(self) -> None:
        self.action = ""
        self.closed = False

    def reset(self, *, seed: int | None = None):
        return RAW_OBSERVATION, {"seed": seed}

    def step(self, action: str):
        self.action = action
        return RAW_OBSERVATION, 1.0, True, False, {}

    def close(self) -> None:
        self.closed = True


def test_environment_translates_actions_and_results() -> None:
    gym_env = FakeGymEnvironment()
    env = BrowserEnvironment(gym_env)

    observation = env.reset(seed=7)
    result = env.step(BrowserAction(ActionType.CLICK, element_id="a1"))

    assert observation.url == "https://example.test"
    assert gym_env.action == "click('a1')"
    assert result.reward == 1.0
    assert result.done


def test_environment_context_manager_closes() -> None:
    gym_env = FakeGymEnvironment()
    with BrowserEnvironment(gym_env):
        pass
    assert gym_env.closed
