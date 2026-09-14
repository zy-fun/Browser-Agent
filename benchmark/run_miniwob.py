"""M1 smoke runner: solve MiniWoB click-test through the project action API."""

from __future__ import annotations

import argparse

from browser.actions import ActionType, BrowserAction
from browser.environment import BrowserEnvironment
from browser.observation import Observation
from configs.environment import load_project_env


def choose_click_target(observation: Observation) -> str:
    """Select the only/most likely button for the fixed M1 click-test task."""
    buttons = [element for element in observation.elements if element.role == "button"]
    if not buttons:
        raise RuntimeError("No visible button with a BrowserGym element id was found")
    return buttons[0].element_id


def run(task_name: str, *, headless: bool, seed: int | None) -> float:
    with BrowserEnvironment.miniwob(task_name, headless=headless) as env:
        observation = env.reset(seed=seed)
        print(observation.to_text())
        target = choose_click_target(observation)
        result = env.step(BrowserAction(ActionType.CLICK, element_id=target))
        print(f"reward={result.reward} done={result.done}")
        return result.reward


def main() -> None:
    load_project_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", default="click-test")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    reward = run(args.task, headless=args.headless, seed=args.seed)
    raise SystemExit(0 if reward > 0 else 1)


if __name__ == "__main__":
    main()
