"""Run a reproducible M2 benchmark suite across MiniWoB tasks and seeds."""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path

from agent.agent import ReActAgent
from agent.loop import run_episode
from benchmark.suite import (
    DEFAULT_M2_TASKS,
    EpisodeRecord,
    SuiteCase,
    build_cases,
    run_suite,
    write_outputs,
)
from browser.environment import BrowserEnvironment
from configs.environment import load_project_env
from llm.factory import LLMProvider, create_llm_client


def _show_record(record: EpisodeRecord) -> None:
    status = "PASS" if record.success else "FAIL"
    print(
        f"[{status}] task={record.task_name} seed={record.seed} "
        f"stop={record.stop_reason} steps={record.steps} "
        f"reward={record.total_reward:g} tokens={record.total_tokens}"
    )
    if record.error:
        print(f"       error={record.error}")


def _default_output_dir() -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return Path("artifacts") / "miniwob" / timestamp


def main() -> None:
    load_project_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", nargs="+", default=list(DEFAULT_M2_TASKS))
    parser.add_argument("--seeds", nargs="+", type=int, default=[0])
    parser.add_argument(
        "--provider",
        choices=[provider.value for provider in LLMProvider],
        help="LLM provider; defaults to LLM_PROVIDER or openai",
    )
    parser.add_argument("--model", help="Model name; defaults to provider environment config")
    parser.add_argument("--max-output-tokens", type=int, default=800)
    parser.add_argument("--llm-retries", type=int, default=1)
    parser.add_argument("--llm-retry-delay", type=float, default=1.0)
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--max-stalled-repeats", type=int, default=3)
    parser.add_argument("--input-cost-per-million", type=float)
    parser.add_argument("--output-cost-per-million", type=float)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--fail-on-task-failure", action="store_true")
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    if (args.input_cost_per_million is None) != (args.output_cost_per_million is None):
        parser.error("Provide both --input-cost-per-million and --output-cost-per-million")
    if any(
        rate is not None and rate < 0
        for rate in (args.input_cost_per_million, args.output_cost_per_million)
    ):
        parser.error("Token prices cannot be negative")

    cases = build_cases(args.tasks, args.seeds)
    llm = create_llm_client(
        args.provider,
        model=args.model,
        max_output_tokens=args.max_output_tokens,
    )
    agent = ReActAgent(
        llm,
        llm_retries=args.llm_retries,
        llm_retry_delay=args.llm_retry_delay,
    )
    provider = args.provider or os.environ.get("LLM_PROVIDER", LLMProvider.OPENAI.value)
    model = str(getattr(llm, "model", args.model or "unknown"))

    def run_case(case: SuiteCase):
        with BrowserEnvironment.miniwob(case.task_name, headless=args.headless) as env:
            return run_episode(
                env,
                agent,
                seed=case.seed,
                max_steps=args.max_steps,
                max_stalled_repeats=args.max_stalled_repeats,
            )

    records = run_suite(
        cases,
        run_case,
        provider=provider,
        model=model,
        input_cost_per_million=args.input_cost_per_million,
        output_cost_per_million=args.output_cost_per_million,
        fail_fast=args.fail_fast,
        on_record=_show_record,
    )
    output_dir = args.output_dir or _default_output_dir()
    summary = write_outputs(
        output_dir,
        records,
        run_config={
            "tasks": list(args.tasks),
            "seeds": list(args.seeds),
            "provider": provider,
            "model": model,
            "max_output_tokens": args.max_output_tokens,
            "max_steps": args.max_steps,
            "max_stalled_repeats": args.max_stalled_repeats,
            "llm_retries": args.llm_retries,
            "llm_retry_delay": args.llm_retry_delay,
            "headless": args.headless,
            "input_cost_per_million": args.input_cost_per_million,
            "output_cost_per_million": args.output_cost_per_million,
        },
    )
    print(
        f"\nSuccess: {summary.successes}/{summary.episodes} "
        f"({summary.success_rate:.1%}) | avg_steps={summary.average_steps:.2f} | "
        f"avg_tokens={summary.average_tokens:.1f}"
    )
    if summary.estimated_cost_usd is not None:
        print(f"Estimated API cost: ${summary.estimated_cost_usd:.6f}")
    print(f"Results: {output_dir.resolve()}")
    if args.fail_on_task_failure and summary.successes != summary.episodes:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
