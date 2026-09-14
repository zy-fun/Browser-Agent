from agent.agent import ReActAgent
from agent.loop import run_episode
from browser.environment import BrowserEnvironment
from llm.client import LLMResponse


def raw_observation(*, done: bool = False):
    return {
        "goal": "Click Submit.",
        "url": "https://example.test",
        "open_pages_titles": ("Example",),
        "active_page_index": [0],
        "axtree_object": {
            "nodes": [
                {
                    "role": {"value": "button"},
                    "name": {"value": "Submit"},
                    "browsergym_id": "a1",
                }
            ]
        },
        "extra_element_properties": {"a1": {"visibility": 1.0}},
        "last_action_error": "" if done else "",
    }


class FakeLLM:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.calls = 0

    def complete(self, messages):
        self.calls += 1
        return LLMResponse(next(self.responses), input_tokens=10, output_tokens=5, total_tokens=15)


class FakeGymEnvironment:
    def __init__(self) -> None:
        self.actions: list[str] = []

    def reset(self, *, seed=None):
        return raw_observation(), {}

    def step(self, action: str):
        self.actions.append(action)
        return raw_observation(done=True), 1.0, True, False, {}

    def close(self):
        pass


def test_agent_retries_hallucinated_element_id() -> None:
    llm = FakeLLM(
        [
            '{"reason":"Click","action":{"type":"click","element_id":"missing"}}',
            '{"reason":"Click Submit","action":{"type":"click","element_id":"a1"}}',
        ]
    )
    env = BrowserEnvironment(FakeGymEnvironment())
    observation = env.reset()
    decision = ReActAgent(llm).step(observation.goal, observation, ())

    assert decision.action.element_id == "a1"
    assert llm.calls == 2


def test_react_loop_completes_environment_task() -> None:
    gym_env = FakeGymEnvironment()
    llm = FakeLLM(['{"reason":"Click Submit","action":{"type":"click","element_id":"a1"}}'])

    result = run_episode(BrowserEnvironment(gym_env), ReActAgent(llm), max_steps=3)

    assert result.success
    assert result.stop_reason == "environment_done"
    assert result.total_reward == 1.0
    assert result.total_tokens == 15
    assert gym_env.actions == ["click('a1')"]


def test_finish_is_handled_locally() -> None:
    gym_env = FakeGymEnvironment()
    llm = FakeLLM(['{"reason":"Cannot continue","action":{"type":"finish","message":"Stopped"}}'])

    result = run_episode(BrowserEnvironment(gym_env), ReActAgent(llm), max_steps=3)

    assert not result.success
    assert result.stop_reason == "agent_finish"
    assert gym_env.actions == []


def test_episode_token_usage_is_not_cumulative() -> None:
    llm = FakeLLM(
        [
            '{"reason":"Click","action":{"type":"click","element_id":"a1"}}',
            '{"reason":"Click","action":{"type":"click","element_id":"a1"}}',
        ]
    )
    agent = ReActAgent(llm)

    first = run_episode(BrowserEnvironment(FakeGymEnvironment()), agent)
    second = run_episode(BrowserEnvironment(FakeGymEnvironment()), agent)

    assert first.total_tokens == 15
    assert second.total_tokens == 15
