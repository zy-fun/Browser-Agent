"""Reusable MiniWoB suite execution and result serialization."""

from __future__ import annotations

import csv
import json
import time
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agent.loop import EpisodeResult

DEFAULT_M2_TASKS = (
    "click-test",
    "enter-text",
    "choose-list",
    "click-checkboxes",
    "click-button-sequence",
    "login-user",
)


@dataclass(frozen=True, slots=True)
class SuiteCase:
    task_name: str
    seed: int


@dataclass(frozen=True, slots=True)
class EpisodeRecord:
    task_name: str
    seed: int
    instruction: str
    provider: str
    model: str
    success: bool
    stop_reason: str
    total_reward: float
    steps: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None
    elapsed_seconds: float
    error: str = ""
    trajectory: tuple[dict[str, Any], ...] = ()

    @classmethod
    def from_result(
        cls,
        case: SuiteCase,
        result: EpisodeResult,
        *,
        provider: str,
        model: str,
        elapsed_seconds: float,
        input_cost_per_million: float | None = None,
        output_cost_per_million: float | None = None,
    ) -> EpisodeRecord:
        trajectory = []
        for step in result.steps:
            action = {
                key: value
                for key, value in asdict(step.decision.action).items()
                if value is not None
            }
            action["type"] = step.decision.action.type.value
            trajectory.append(
                {
                    "number": step.number,
                    "reason": step.decision.reason,
                    "action": action,
                    "url": step.url,
                    "reward": step.reward,
                    "error": step.error,
                }
            )
        return cls(
            task_name=case.task_name,
            seed=case.seed,
            instruction=result.task,
            provider=provider,
            model=model,
            success=result.success,
            stop_reason=result.stop_reason,
            total_reward=result.total_reward,
            steps=len(result.steps),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            estimated_cost_usd=_estimate_cost(
                result.input_tokens,
                result.output_tokens,
                input_cost_per_million,
                output_cost_per_million,
            ),
            elapsed_seconds=elapsed_seconds,
            trajectory=tuple(trajectory),
        )

    @classmethod
    def from_error(
        cls,
        case: SuiteCase,
        error: Exception,
        *,
        provider: str,
        model: str,
        elapsed_seconds: float,
    ) -> EpisodeRecord:
        return cls(
            task_name=case.task_name,
            seed=case.seed,
            instruction="",
            provider=provider,
            model=model,
            success=False,
            stop_reason="runner_error",
            total_reward=0.0,
            steps=0,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            estimated_cost_usd=None,
            elapsed_seconds=elapsed_seconds,
            error=f"{type(error).__name__}: {error}",
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["trajectory"] = list(self.trajectory)
        return payload


@dataclass(frozen=True, slots=True)
class SuiteSummary:
    episodes: int
    successes: int
    success_rate: float
    average_steps: float
    average_tokens: float
    total_tokens: int
    estimated_cost_usd: float | None
    total_elapsed_seconds: float
    stop_reasons: dict[str, int]

    @classmethod
    def from_records(cls, records: Sequence[EpisodeRecord]) -> SuiteSummary:
        count = len(records)
        successes = sum(record.success for record in records)
        costs = [record.estimated_cost_usd for record in records]
        estimated_cost = None if any(cost is None for cost in costs) else sum(costs)
        return cls(
            episodes=count,
            successes=successes,
            success_rate=successes / count if count else 0.0,
            average_steps=sum(record.steps for record in records) / count if count else 0.0,
            average_tokens=sum(record.total_tokens for record in records) / count if count else 0.0,
            total_tokens=sum(record.total_tokens for record in records),
            estimated_cost_usd=estimated_cost,
            total_elapsed_seconds=sum(record.elapsed_seconds for record in records),
            stop_reasons=dict(sorted(Counter(record.stop_reason for record in records).items())),
        )


EpisodeRunner = Callable[[SuiteCase], EpisodeResult]
RecordCallback = Callable[[EpisodeRecord], None]


def _estimate_cost(
    input_tokens: int,
    output_tokens: int,
    input_cost_per_million: float | None,
    output_cost_per_million: float | None,
) -> float | None:
    if input_cost_per_million is None or output_cost_per_million is None:
        return None
    return (
        input_tokens * input_cost_per_million + output_tokens * output_cost_per_million
    ) / 1_000_000


def build_cases(tasks: Iterable[str], seeds: Iterable[int]) -> tuple[SuiteCase, ...]:
    """Create a stable task-major benchmark matrix."""
    selected_tasks = tuple(dict.fromkeys(task.strip() for task in tasks if task.strip()))
    selected_seeds = tuple(dict.fromkeys(seeds))
    if not selected_tasks:
        raise ValueError("At least one task is required")
    if not selected_seeds:
        raise ValueError("At least one seed is required")
    return tuple(SuiteCase(task, seed) for task in selected_tasks for seed in selected_seeds)


def run_suite(
    cases: Sequence[SuiteCase],
    runner: EpisodeRunner,
    *,
    provider: str,
    model: str,
    input_cost_per_million: float | None = None,
    output_cost_per_million: float | None = None,
    fail_fast: bool = False,
    on_record: RecordCallback | None = None,
) -> tuple[EpisodeRecord, ...]:
    """Run isolated episodes so one task failure does not discard the suite."""
    records: list[EpisodeRecord] = []
    for case in cases:
        started = time.perf_counter()
        try:
            result = runner(case)
            record = EpisodeRecord.from_result(
                case,
                result,
                provider=provider,
                model=model,
                elapsed_seconds=time.perf_counter() - started,
                input_cost_per_million=input_cost_per_million,
                output_cost_per_million=output_cost_per_million,
            )
        except Exception as exc:
            record = EpisodeRecord.from_error(
                case,
                exc,
                provider=provider,
                model=model,
                elapsed_seconds=time.perf_counter() - started,
            )
        records.append(record)
        if on_record:
            on_record(record)
        if fail_fast and not record.success:
            break
    return tuple(records)


def write_outputs(
    output_dir: Path,
    records: Sequence[EpisodeRecord],
    *,
    run_config: Mapping[str, Any],
) -> SuiteSummary:
    """Write detailed JSONL, tabular CSV, run configuration, and aggregate JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = SuiteSummary.from_records(records)

    with (output_dir / "episodes.jsonl").open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    csv_fields = [
        "task_name",
        "seed",
        "provider",
        "model",
        "success",
        "stop_reason",
        "total_reward",
        "steps",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "estimated_cost_usd",
        "elapsed_seconds",
        "error",
    ]
    with (output_dir / "episodes.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=csv_fields)
        writer.writeheader()
        for record in records:
            payload = record.to_dict()
            writer.writerow({field: payload[field] for field in csv_fields})

    (output_dir / "summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "run_config.json").write_text(
        json.dumps(dict(run_config), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary
