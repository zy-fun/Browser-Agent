import json

from agent.loop import EpisodeResult, ExecutionStep
from agent.parser import AgentDecision
from agent.planner import Plan, PlanState, PlanStep
from benchmark.suite import SuiteCase, build_cases, run_suite, write_outputs
from browser.actions import ActionType, BrowserAction
from browser.observation import Observation

OBSERVATION = Observation(
    goal="Click Submit",
    url="https://example.test",
    title="Example",
    elements=(),
)


def successful_result(task: str, *, with_plan: bool = False) -> EpisodeResult:
    decision = AgentDecision(
        reason="Click Submit",
        action=BrowserAction(ActionType.CLICK, element_id="a1"),
    )
    step = ExecutionStep(1, decision, OBSERVATION.url, reward=1.0)
    plan_state = None
    if with_plan:
        plan = Plan("Submit the form", (PlanStep(1, "Click Submit"),))
        plan_state = PlanState(plan, (1,), None)
    return EpisodeResult(
        task=task,
        observation=OBSERVATION,
        steps=(step,),
        total_reward=1.0,
        success=True,
        stop_reason="environment_done",
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        plan_state=plan_state,
    )


def test_build_cases_is_task_major_and_deduplicated() -> None:
    assert build_cases(["click-test", "click-test", "enter-text"], [1, 2, 1]) == (
        SuiteCase("click-test", 1),
        SuiteCase("click-test", 2),
        SuiteCase("enter-text", 1),
        SuiteCase("enter-text", 2),
    )


def test_suite_isolates_episode_errors_and_continues() -> None:
    cases = build_cases(["good", "bad", "next"], [0])

    def runner(case: SuiteCase) -> EpisodeResult:
        if case.task_name == "bad":
            raise RuntimeError("provider unavailable")
        return successful_result(case.task_name)

    records = run_suite(cases, runner, provider="deepseek", model="test-model")

    assert [record.success for record in records] == [True, False, True]
    assert records[1].stop_reason == "runner_error"
    assert records[1].error == "RuntimeError: provider unavailable"


def test_write_outputs_preserves_metrics_and_trajectory(tmp_path) -> None:
    case = SuiteCase("click-test", 7)
    records = run_suite(
        (case,),
        lambda _: successful_result("Click Submit", with_plan=True),
        provider="deepseek",
        model="test-model",
        input_cost_per_million=1.0,
        output_cost_per_million=2.0,
    )

    summary = write_outputs(tmp_path, records, run_config={"seeds": [7]})
    episode = json.loads((tmp_path / "episodes.jsonl").read_text(encoding="utf-8"))
    saved_summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))

    assert summary.success_rate == 1.0
    assert episode["trajectory"][0]["action"] == {"type": "click", "element_id": "a1"}
    assert episode["plan_state"]["steps"][0]["status"] == "completed"
    assert saved_summary["total_tokens"] == 15
    assert saved_summary["estimated_cost_usd"] == 0.00002
    assert (tmp_path / "episodes.csv").is_file()
    assert (tmp_path / "run_config.json").is_file()
