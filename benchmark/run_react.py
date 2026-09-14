"""Run the M2 LLM-driven ReAct agent on one MiniWoB task."""

from __future__ import annotations

import argparse
import time

from agent.agent import ReActAgent
from agent.loop import ExecutionStep, run_episode
from browser.environment import BrowserEnvironment
from browser.observation import Observation
from configs.environment import load_project_env
from llm.factory import LLMProvider, create_llm_client


def _show_step(delay: float):
    def callback(step: ExecutionStep, observation: Observation) -> None:
        print(f"\nStep {step.number}: {step.decision.reason}")
        print(f"Action: {step.decision.action}")
        print(f"Reward: {step.reward:g} URL: {observation.url}")
        if step.error:
            print(f"Error: {step.error}")
        if delay:
            time.sleep(delay)

    return callback


def main() -> None:
    load_project_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", default="click-test", help="MiniWoB task name")
    parser.add_argument("--instruction", help="Override the instruction supplied by MiniWoB")
    parser.add_argument(
        "--provider",
        choices=[provider.value for provider in LLMProvider],
        help="LLM provider; defaults to LLM_PROVIDER or openai",
    )
    parser.add_argument(
        "--model",
        help="Model name; defaults to the provider-specific *_MODEL or LLM_MODEL",
    )
    parser.add_argument("--max-output-tokens", type=int, default=800)
    parser.add_argument("--llm-retries", type=int, default=1)
    parser.add_argument("--llm-retry-delay", type=float, default=1.0)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--max-stalled-repeats", type=int, default=3)
    parser.add_argument("--step-delay", type=float, default=0.0)
    parser.add_argument("--pause-on-finish", action="store_true")
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

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
    with BrowserEnvironment.miniwob(args.task, headless=args.headless) as env:
        result = run_episode(
            env,
            agent,
            task=args.instruction,
            seed=args.seed,
            max_steps=args.max_steps,
            max_stalled_repeats=args.max_stalled_repeats,
            on_step=_show_step(args.step_delay),
        )
        print(
            f"\nSuccess: {result.success} | stop={result.stop_reason} | "
            f"steps={len(result.steps)} | reward={result.total_reward:g} | "
            f"tokens={result.total_tokens}"
        )
        if args.pause_on_finish:
            input("Press Enter to close the browser...")

    raise SystemExit(0 if result.success else 1)


if __name__ == "__main__":
    main()
