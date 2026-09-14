import pytest

from agent.planner import PlanError, TaskPlanner
from browser.observation import Observation
from llm.client import LLMResponse

OBSERVATION = Observation("Book a flight", "https://example.test", "Travel", ())


class FakeLLM:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)

    def complete(self, messages):
        return LLMResponse(next(self.responses), input_tokens=10, output_tokens=5, total_tokens=15)


def test_planner_creates_and_updates_typed_plan_state() -> None:
    llm = FakeLLM(
        [
            '{"goal":"Book flight","steps":['
            '{"id":1,"description":"Enter trip details"},'
            '{"id":2,"description":"Choose a flight"}]}',
            '{"completed":[1],"current":2}',
        ]
    )
    planner = TaskPlanner(llm)

    state = planner.create_plan("Book a flight", OBSERVATION)
    updated = planner.update_plan(state, OBSERVATION, ("1. entered details",))

    assert state.current_step_id == 1
    assert updated.completed_step_ids == (1,)
    assert updated.current_step_id == 2
    assert "[completed] 1. Enter trip details" in updated.to_text()
    assert planner.usage.total_tokens == 30


def test_planner_rejects_non_prefix_progress() -> None:
    llm = FakeLLM(
        [
            '{"goal":"Book flight","steps":['
            '{"id":1,"description":"Enter details"},'
            '{"id":2,"description":"Choose flight"}]}',
            '{"completed":[2],"current":1}',
        ]
    )
    planner = TaskPlanner(llm, retries=0)
    state = planner.create_plan("Book a flight", OBSERVATION)

    with pytest.raises(PlanError, match="consecutive prefix"):
        planner.update_plan(state, OBSERVATION, ())
